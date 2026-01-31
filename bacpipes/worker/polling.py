"""BACnet polling and MQTT publishing worker."""

import asyncio
import json
import os
import time
import math
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import pytz
from sqlmodel import Session, select, create_engine

from ..models.device import Device
from ..models.point import Point
from ..models.mqtt_config import MqttConfig
from ..models.system_settings import SystemSettings
from .bacnet_client import BACnetClient
from .mqtt_client import MQTTClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Discovery coordination lock file
DISCOVERY_LOCK_FILE = "/tmp/bacnet_discovery_active"
RESTART_FLAG_FILE = "/tmp/bacpipes_worker_restart"

# Fixed override subscription constants
OVERRIDE_PREFIX = "override"
OVERRIDE_PATTERN = "override/#"
OVERRIDE_QOS = 1


class PollingWorker:
    """Main BACnet polling and MQTT publishing worker."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url)

        # Clients
        self.bacnet_client: Optional[BACnetClient] = None
        self.mqtt_client: Optional[MQTTClient] = None

        # Configuration
        self.bacnet_ip: Optional[str] = None
        self.bacnet_port: int = 47808
        self.bacnet_device_id: int = 3001234
        self.timezone = pytz.timezone("UTC")
        self.poll_interval: int = 60

        # State
        self.point_last_poll: Dict[int, float] = {}
        self.poll_cycle = 0

        # Subscription config
        self.subscribe_enabled: bool = False
        self.write_command_topic: str = "write/command"
        self.write_result_topic: str = "write/result"

        # Override handling - map mqtt topics to point info
        self.topic_to_point: Dict[str, Dict[str, Any]] = {}

    def load_system_settings(self) -> bool:
        """Load system settings from database."""
        with Session(self.engine) as session:
            settings = session.exec(select(SystemSettings)).first()

            if not settings:
                logger.warning("No system settings found")
                return False

            if not settings.bacnetIp:
                logger.warning("BACnet IP not configured - waiting for setup")
                return False

            self.bacnet_ip = settings.bacnetIp
            self.bacnet_port = settings.bacnetPort
            self.bacnet_device_id = settings.bacnetDeviceId
            self.timezone = pytz.timezone(settings.timezone)
            self.poll_interval = settings.defaultPollInterval

            logger.info(f"System settings loaded:")
            logger.info(f"  BACnet: {self.bacnet_ip}:{self.bacnet_port}")
            logger.info(f"  Device ID: {self.bacnet_device_id}")
            logger.info(f"  Timezone: {settings.timezone}")

            return True

    def load_mqtt_config(self) -> bool:
        """Load MQTT configuration from database."""
        with Session(self.engine) as session:
            config = session.exec(select(MqttConfig)).first()

            if not config:
                logger.warning("No MQTT config found")
                return False

            if not config.broker:
                logger.warning("MQTT broker not configured - waiting for setup")
                return False

            self.mqtt_client = MQTTClient(
                broker=config.broker,
                port=config.port,
                client_id=config.clientId,
                username=config.username,
                password=config.password,
                tls_enabled=config.tlsEnabled,
                tls_insecure=config.tlsInsecure,
                ca_cert_path=config.caCertPath,
            )

            # Load subscription settings
            self.subscribe_enabled = config.subscribeEnabled
            self.write_command_topic = config.writeCommandTopic or "write/command"
            self.write_result_topic = config.writeResultTopic or "write/result"

            logger.info(f"MQTT config loaded: {config.broker}:{config.port}")
            if self.subscribe_enabled:
                logger.info(f"Override subscription enabled: {OVERRIDE_PATTERN}")
            return True

    def update_mqtt_status(self, status: str, update_data_flow: bool = False):
        """Update MQTT connection status in database."""
        try:
            with Session(self.engine) as session:
                config = session.exec(select(MqttConfig)).first()
                if config:
                    config.connectionStatus = status
                    config.updatedAt = datetime.now()
                    if update_data_flow and self.mqtt_client:
                        config.lastDataFlow = datetime.now()
                    if status == "connected":
                        config.lastConnected = datetime.now()
                    session.add(config)
                    session.commit()
        except Exception as e:
            logger.warning(f"Failed to update MQTT status: {e}")

    def get_enabled_points(self) -> List[Dict[str, Any]]:
        """Fetch enabled points from database."""
        with Session(self.engine) as session:
            query = (
                select(Point, Device)
                .join(Device, Point.deviceId == Device.id)
                .where(Point.mqttPublish == True)
                .where(Point.enabled == True)
                .where(Device.enabled == True)
            )

            results = session.exec(query).all()

            points = []
            for point, device in results:
                points.append({
                    "id": point.id,
                    "objectType": point.objectType,
                    "objectInstance": point.objectInstance,
                    "pointName": point.pointName,
                    "dis": point.dis,
                    "units": point.units,
                    "mqttTopic": point.mqttTopic,
                    "pollInterval": point.pollInterval,
                    "qos": point.qos,
                    "haystackPointName": point.haystackPointName,
                    "isWritable": point.isWritable,
                    "deviceId": device.deviceId,
                    "deviceIp": device.ipAddress,
                    "devicePort": device.port,
                })

            logger.info(f"Loaded {len(points)} enabled points")
            return points

    def update_point_value(self, point_id: int, value: str, timestamp: datetime):
        """Update point value in database."""
        try:
            with Session(self.engine) as session:
                point = session.get(Point, point_id)
                if point:
                    point.lastValue = value
                    point.lastPollTime = timestamp
                    point.updatedAt = timestamp
                    session.add(point)
                    session.commit()
        except Exception as e:
            logger.warning(f"Failed to update point {point_id}: {e}")

    def build_topic_to_point_map(self):
        """Build mapping from override topics to point info for fast lookup."""
        self.topic_to_point = {}
        points = self.get_enabled_points()

        for point in points:
            mqtt_topic = point.get("mqttTopic")
            if mqtt_topic:
                # The override topic uses fixed prefix: override/<mqtt_topic>
                # e.g., mqtt_topic = "site/ahu/12/sensor/temp/435"
                # override_topic = "override/site/ahu/12/sensor/temp/435"
                override_topic = f"{OVERRIDE_PREFIX}/{mqtt_topic}"
                self.topic_to_point[override_topic] = point
                logger.debug(f"Mapped override topic: {override_topic}")

        logger.info(f"Built topic map with {len(self.topic_to_point)} override topics")

    def handle_mqtt_message(self, topic: str, payload: bytes):
        """Handle incoming MQTT messages for overrides and write commands."""
        try:
            # Check if this is a write command
            if topic == self.write_command_topic:
                self._handle_write_command(payload)
                return

            # Check if this is an override message (uses fixed prefix)
            if topic.startswith(f"{OVERRIDE_PREFIX}/"):
                self._handle_override_message(topic, payload)
                return

            logger.debug(f"Unhandled message on topic: {topic}")

        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}", exc_info=True)

    def _handle_write_command(self, payload: bytes):
        """Handle write command messages (legacy format)."""
        # This is handled by WriteHandler - just log for now
        logger.info(f"Received write command (handled by WriteHandler)")

    def _handle_override_message(self, topic: str, payload: bytes):
        """Handle override messages - write value to BACnet point."""
        # Find matching point
        point = self.topic_to_point.get(topic)
        if not point:
            logger.warning(f"Override topic not found in map: {topic}")
            return

        # Check if point is writable
        if not point.get("isWritable", False):
            logger.warning(
                f"Override rejected: Point '{point.get('pointName')}' is not writable"
            )
            return

        try:
            # Parse payload
            data = json.loads(payload.decode())
            value = data.get("value")

            if value is None:
                logger.warning(f"Override message missing 'value': {topic}")
                return

            logger.info(f"Override received: {topic} -> {value}")

            # Queue the write for async processing
            self._queue_override_write(point, value, data.get("priority", 8))

        except json.JSONDecodeError:
            # Try raw value (just a number or string)
            try:
                value = payload.decode().strip()
                if value:
                    logger.info(f"Override received (raw): {topic} -> {value}")
                    self._queue_override_write(point, value, 8)
            except Exception as e:
                logger.error(f"Failed to parse override payload: {e}")

    def _queue_override_write(self, point: Dict[str, Any], value: Any, priority: int):
        """Queue an override write to be processed."""
        # Store for async processing
        if not hasattr(self, 'pending_overrides'):
            self.pending_overrides: List[Dict] = []

        self.pending_overrides.append({
            "point": point,
            "value": value,
            "priority": priority,
            "timestamp": datetime.now(pytz.utc),
        })

    async def process_pending_overrides(self):
        """Process any pending override writes."""
        if not hasattr(self, 'pending_overrides') or not self.pending_overrides:
            return

        if not self.bacnet_client:
            return

        while self.pending_overrides:
            override = self.pending_overrides.pop(0)
            point = override["point"]
            value = override["value"]
            priority = override["priority"]

            try:
                success, error_msg = await self.bacnet_client.write_property(
                    device_ip=point["deviceIp"],
                    device_port=point["devicePort"],
                    object_type=point["objectType"],
                    object_instance=point["objectInstance"],
                    value=value,
                    priority=priority,
                )

                if success:
                    logger.info(f"Override write successful: {point['pointName']} = {value}")
                    # Update the point value in DB
                    self.update_point_value(point["id"], str(value), datetime.now(pytz.utc))
                else:
                    logger.error(f"Override write failed: {point['pointName']} - {error_msg}")

            except Exception as e:
                logger.error(f"Override write error: {point['pointName']} - {e}")

    async def poll_and_publish(self):
        """Main polling loop - poll points and publish to MQTT."""
        points = self.get_enabled_points()

        if not points:
            return

        current_time = time.time()
        timestamp = datetime.now(pytz.utc)

        # Calculate minute boundary for alignment
        next_minute = math.ceil(current_time / 60) * 60

        # Statistics
        total_reads = 0
        successful_reads = 0
        failed_reads = 0
        skipped_reads = 0
        publishes = 0

        # Poll each point
        for point in points:
            point_id = point["id"]
            poll_interval = point["pollInterval"]

            # Initialize new points for minute-aligned polling
            if point_id not in self.point_last_poll:
                self.point_last_poll[point_id] = next_minute - poll_interval
                skipped_reads += 1
                continue

            # Check if time to poll
            last_poll = self.point_last_poll.get(point_id, 0)
            if current_time - last_poll < poll_interval:
                skipped_reads += 1
                continue

            # Check alignment
            current_second = int(current_time) % 60
            if (current_second % poll_interval) >= 2:
                skipped_reads += 1
                continue

            total_reads += 1

            # Read from BACnet
            value = await self.bacnet_client.read_property(
                device_ip=point["deviceIp"],
                device_port=point["devicePort"],
                object_type=point["objectType"],
                object_instance=point["objectInstance"],
            )

            if value is not None:
                successful_reads += 1

                # Update poll time
                aligned_time = math.floor(current_time / poll_interval) * poll_interval
                self.point_last_poll[point_id] = aligned_time

                # Update database
                self.update_point_value(point_id, str(value), timestamp)

                # Publish to MQTT
                if point["mqttTopic"] and self.mqtt_client and self.mqtt_client.connected:
                    tz_offset = int(timestamp.astimezone(self.timezone).utcoffset().total_seconds() / 3600)

                    if self.mqtt_client.publish_point_value(
                        topic=point["mqttTopic"],
                        value=value,
                        units=point["units"],
                        dis=point["dis"],
                        haystack_name=point["haystackPointName"],
                        object_type=point["objectType"],
                        object_instance=point["objectInstance"],
                        timezone_offset=tz_offset,
                        qos=point["qos"],
                    ):
                        publishes += 1
            else:
                failed_reads += 1

        # Log summary
        if total_reads > 0:
            self.poll_cycle += 1
            logger.info(f"Poll Cycle #{self.poll_cycle}:")
            logger.info(f"  Points: {len(points)} ({total_reads} polled, {skipped_reads} skipped)")
            logger.info(f"  Reads: {successful_reads}/{total_reads} successful")
            logger.info(f"  Published: {publishes}")

            # Update MQTT status if publishing
            if publishes > 0:
                self.update_mqtt_status("connected", update_data_flow=True)

    async def run(self):
        """Main worker loop."""
        logger.info("=== BacPipes Worker Starting ===")

        # Wait for configuration
        while not self.load_system_settings():
            logger.info("Waiting for BACnet configuration...")
            await asyncio.sleep(10)

        while not self.load_mqtt_config():
            logger.info("Waiting for MQTT configuration...")
            await asyncio.sleep(10)

        # Initialize BACnet
        self.bacnet_client = BACnetClient(
            local_ip=self.bacnet_ip,
            port=self.bacnet_port,
            device_id=self.bacnet_device_id,
        )

        if not self.bacnet_client.initialize():
            logger.error("Failed to initialize BACnet client")
            return

        # Set up MQTT subscriptions
        self.mqtt_client.add_subscription(self.write_command_topic, qos=1)
        if self.subscribe_enabled:
            self.mqtt_client.add_subscription(OVERRIDE_PATTERN, qos=OVERRIDE_QOS)

        # Set message callback
        self.mqtt_client.on_message_callback = self.handle_mqtt_message

        # Connect to MQTT
        self.update_mqtt_status("connecting")
        if self.mqtt_client.connect():
            self.update_mqtt_status("connected")
        else:
            self.update_mqtt_status("disconnected")

        # Build topic-to-point map for overrides
        self.build_topic_to_point_map()

        logger.info("=== Worker Started ===")

        # Main loop
        while True:
            try:
                # Check for discovery lock
                if os.path.exists(DISCOVERY_LOCK_FILE):
                    logger.info("Discovery lock detected - pausing polling")
                    self.bacnet_client.close()
                    self.bacnet_client = None

                    while os.path.exists(DISCOVERY_LOCK_FILE):
                        await asyncio.sleep(1)

                    logger.info("Discovery complete - restarting BACnet")
                    self.bacnet_client = BACnetClient(
                        local_ip=self.bacnet_ip,
                        port=self.bacnet_port,
                        device_id=self.bacnet_device_id,
                    )
                    self.bacnet_client.initialize()
                    continue

                # Check for restart flag
                if os.path.exists(RESTART_FLAG_FILE):
                    logger.info("Restart flag detected - reloading configuration")
                    os.remove(RESTART_FLAG_FILE)

                    # Reload configs
                    self.load_system_settings()
                    self.load_mqtt_config()

                    # Update subscriptions
                    if self.subscribe_enabled:
                        self.mqtt_client.add_subscription(OVERRIDE_PATTERN, qos=OVERRIDE_QOS)
                    self.mqtt_client.on_message_callback = self.handle_mqtt_message

                    # Reconnect MQTT
                    if self.mqtt_client:
                        self.mqtt_client.disconnect()
                    self.update_mqtt_status("connecting")
                    if self.mqtt_client.connect():
                        self.update_mqtt_status("connected")
                    else:
                        self.update_mqtt_status("disconnected")

                    # Rebuild topic map
                    self.build_topic_to_point_map()

                # Reconnect MQTT if needed (don't set "connecting" for periodic retries)
                if self.mqtt_client and not self.mqtt_client.connected:
                    if self.mqtt_client.reconnect():
                        self.update_mqtt_status("connected")

                # Process any pending override writes
                await self.process_pending_overrides()

                # Poll and publish
                await self.poll_and_publish()

            except Exception as e:
                logger.error(f"Error in poll cycle: {e}", exc_info=True)

            await asyncio.sleep(1)

        # Cleanup
        logger.info("Shutting down...")

        if self.mqtt_client:
            self.mqtt_client.disconnect()

        if self.bacnet_client:
            self.bacnet_client.close()

        logger.info("Worker stopped")


async def start_worker():
    """Start the polling worker."""
    # Get database URL from rxconfig
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://bacpipes@localhost:5432/bacpipes"
    )

    worker = PollingWorker(db_url)
    await worker.run()

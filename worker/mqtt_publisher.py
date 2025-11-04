#!/usr/bin/env python3
"""
BacPipes MQTT Publisher - M4 Implementation (BACpypes3)
Publishes BACnet data to MQTT broker using hybrid strategy:
- Individual topics: {site}/{equipment}/{point}/presentValue
- Batch topics: {site}/{equipment}/batch

Based on proven working implementation from scripts/05_production_mqtt.py
"""

import os
import sys
import time
import json
import signal
import logging
import asyncio
import struct
import math
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import RealDictCursor
import pytz

# BACpypes3 imports (proven working approach)
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.local.device import DeviceObject
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.apdu import ReadPropertyRequest
from bacpypes3.basetypes import PropertyIdentifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


class MqttPublisher:
    """MQTT Publisher with BACpypes3 integration"""

    def __init__(self):
        # Configuration from environment
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = int(os.getenv('DB_PORT', '5434'))
        self.db_name = os.getenv('DB_NAME', 'bacpipes')
        self.db_user = os.getenv('DB_USER', 'anatoli')
        self.db_password = os.getenv('DB_PASSWORD', '')

        self.mqtt_broker = os.getenv('MQTT_BROKER', '10.0.60.2')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.mqtt_client_id = os.getenv('MQTT_CLIENT_ID', 'bacpipes_worker')

        self.bacnet_ip = os.getenv('BACNET_IP', '192.168.1.35')
        self.bacnet_port = int(os.getenv('BACNET_PORT', '47808'))
        self.bacnet_device_id = int(os.getenv('BACNET_DEVICE_ID', '3056496'))

        self.poll_interval = int(os.getenv('POLL_INTERVAL', '60'))
        self.timezone = pytz.timezone(os.getenv('TZ', 'Asia/Kuala_Lumpur'))

        # Retry configuration (from proven working script)
        self.max_retries = 3
        self.base_timeout = 6000  # 6 seconds
        self.exponential_backoff = True

        # State
        self.db_conn = None
        self.mqtt_client = None
        self.mqtt_connected = False
        self.poll_cycle = 0
        self.bacnet_app = None  # Will be initialized after event loop starts
        self.enable_batch_publishing = False  # Loaded from database
        self.point_last_poll = {}  # Track last poll time per point ID

        logger.info("=== BacPipes MQTT Publisher Configuration ===")
        logger.info(f"Database: {self.db_host}:{self.db_port}/{self.db_name}")
        logger.info(f"MQTT Broker: {self.mqtt_broker}:{self.mqtt_port}")
        logger.info(f"BACnet Interface: {self.bacnet_ip}:{self.bacnet_port}")
        logger.info(f"BACnet Device ID: {self.bacnet_device_id}")
        logger.info(f"Poll Interval: {self.poll_interval}s")
        logger.info(f"=" * 45)

    def initialize_bacnet(self):
        """Initialize BACpypes3 application (must be called after event loop is running)"""
        try:
            # Create BACnet device
            device = DeviceObject(
                objectIdentifier=ObjectIdentifier(f"device,{self.bacnet_device_id}"),
                objectName="BACpipes",
                vendorIdentifier=842,  # Servisys
                maxApduLengthAccepted=1024,
                segmentationSupported="segmentedBoth",
            )

            # Create address for BACnet interface
            local_address = Address(f"{self.bacnet_ip}:{self.bacnet_port}")

            # Create NormalApplication
            self.bacnet_app = NormalApplication(device, local_address)

            logger.info(f"✅ BACpypes3 NormalApplication initialized on {local_address}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize BACnet: {e}")
            return False

    def connect_database(self):
        """Connect to PostgreSQL database"""
        try:
            self.db_conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                cursor_factory=RealDictCursor
            )
            logger.info("✅ Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False

    def load_system_settings(self):
        """Load system settings from database (timezone, etc)"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT timezone FROM "SystemSettings" LIMIT 1')
            result = cursor.fetchone()
            cursor.close()

            if result and result['timezone']:
                self.timezone = pytz.timezone(result['timezone'])
                logger.info(f"🌍 Timezone: {result['timezone']}")
            else:
                logger.warning("⚠️  No system settings found in database, using default timezone")
                self.timezone = pytz.timezone(os.getenv('TZ', 'Asia/Kuala_Lumpur'))

            return True
        except Exception as e:
            logger.error(f"❌ Failed to load system settings: {e}")
            logger.warning(f"⚠️  Using default timezone: {os.getenv('TZ', 'Asia/Kuala_Lumpur')}")
            self.timezone = pytz.timezone(os.getenv('TZ', 'Asia/Kuala_Lumpur'))
            return False

    def load_mqtt_config(self):
        """Load MQTT configuration from database"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT "enableBatchPublishing" FROM "MqttConfig" LIMIT 1')
            result = cursor.fetchone()
            cursor.close()

            if result:
                self.enable_batch_publishing = result['enableBatchPublishing']
                logger.info(f"📋 Batch Publishing: {'ENABLED' if self.enable_batch_publishing else 'DISABLED'}")
            else:
                logger.warning("⚠️  No MQTT config found in database, using default (batch disabled)")
                self.enable_batch_publishing = False

            return True
        except Exception as e:
            logger.error(f"❌ Failed to load MQTT config: {e}")
            logger.warning("⚠️  Using default: batch publishing disabled")
            self.enable_batch_publishing = False
            return False

    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.mqtt_client = mqtt.Client(client_id=self.mqtt_client_id)
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect

            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()

            # Wait for connection
            time.sleep(2)
            logger.info(f"✅ Connected to MQTT broker {self.mqtt_broker}:{self.mqtt_port}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MQTT broker: {e}")
            return False

    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            logger.info("MQTT connection established successfully")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        if rc != 0:
            logger.warning(f"MQTT unexpected disconnection (code {rc}), will auto-reconnect")
            self.mqtt_connected = False

    def get_enabled_points(self) -> List[Dict]:
        """Fetch enabled points from database"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT
                    p.id, p."objectType", p."objectInstance", p."pointName",
                    p.dis, p.units, p."mqttTopic", p."pollInterval",
                    p.qos, p."haystackPointName", p."siteId", p."equipmentType",
                    p."equipmentId", p."isReadable", p."isWritable",
                    d.id as "deviceDbId", d."deviceId", d."deviceName", d."ipAddress", d.port
                FROM "Point" p
                JOIN "Device" d ON p."deviceId" = d.id
                WHERE p."mqttPublish" = true AND p.enabled = true
                ORDER BY d.id, p."objectInstance"
            """)

            points = cursor.fetchall()
            cursor.close()

            logger.info(f"Loaded {len(points)} enabled points from database")
            return [dict(point) for point in points]
        except Exception as e:
            logger.error(f"Failed to fetch enabled points: {e}")
            return []

    async def read_with_retry(self, device_ip: str, device_port: int, device_id: int,
                                object_type: str, object_instance: int) -> Optional[Any]:
        """Read BACnet point with retry logic (proven working approach)"""

        # Map object types to BACnet format
        obj_type_map = {
            'analog-input': 'analogInput',
            'analog-output': 'analogOutput',
            'analog-value': 'analogValue',
            'binary-input': 'binaryInput',
            'binary-output': 'binaryOutput',
            'binary-value': 'binaryValue',
            'multi-state-input': 'multiStateInput',
            'multi-state-output': 'multiStateOutput',
            'multi-state-value': 'multiStateValue',
            'date-value': 'dateValue',
        }

        obj_type_bacnet = obj_type_map.get(object_type, object_type)

        # Create BACnet address and object identifier
        device_address = Address(f"{device_ip}:{device_port}")
        object_id = ObjectIdentifier(f"{obj_type_bacnet},{object_instance}")

        # Retry loop with exponential backoff
        for attempt in range(self.max_retries + 1):
            try:
                # Calculate timeout
                if self.exponential_backoff and attempt > 0:
                    timeout = self.base_timeout * (2 ** (attempt - 1))
                else:
                    timeout = self.base_timeout

                logger.debug(f"  Attempt {attempt + 1}: Reading {object_type}:{object_instance} from device {device_id} at {device_ip} (timeout: {timeout}ms)")

                # Create read request
                request = ReadPropertyRequest(
                    objectIdentifier=object_id,
                    propertyIdentifier=PropertyIdentifier('presentValue'),
                    destination=device_address
                )

                # Send request with timeout
                response = await asyncio.wait_for(
                    self.bacnet_app.request(request),
                    timeout=timeout / 1000.0  # Convert to seconds
                )

                if response and hasattr(response, 'propertyValue'):
                    value = self.extract_value(response.propertyValue)
                    logger.info(f"✓ Read {object_type}:{object_instance} from device {device_id}: {value}")
                    return value

            except asyncio.TimeoutError:
                logger.debug(f"  Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5)  # Brief delay before retry
                continue
            except Exception as e:
                logger.debug(f"  Error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5)
                continue

        logger.error(f"✗ Failed to read {object_type}:{object_instance} from device {device_id} after {self.max_retries + 1} attempts")
        return None

    def extract_value(self, bacnet_value):
        """Extract readable value from BACnet Any object (proven working approach)"""
        try:
            # Convert to string first
            value_str = str(bacnet_value)

            # If it's the Any object representation, extract from tagList
            if "bacpypes3.primitivedata.Any object" in value_str:
                if hasattr(bacnet_value, 'tagList') and bacnet_value.tagList:
                    tag_list = list(bacnet_value.tagList)

                    # Find tag with data
                    data_tag = None
                    for tag in tag_list:
                        if hasattr(tag, 'tag_data') and tag.tag_data and len(tag.tag_data) > 0:
                            data_tag = tag
                            break

                    if not data_tag:
                        data_tag = tag_list[0]

                    if hasattr(data_tag, 'tag_data') and hasattr(data_tag, 'tag_number'):
                        tag_number = data_tag.tag_number
                        tag_data = data_tag.tag_data

                        if not tag_data or len(tag_data) == 0:
                            return None

                        # Decode based on tag type
                        if tag_number == 1:  # Boolean
                            return bool(tag_data[0])
                        elif tag_number == 2:  # Unsigned
                            if len(tag_data) == 1:
                                return tag_data[0]
                            elif len(tag_data) == 2:
                                return struct.unpack('>H', tag_data)[0]
                            elif len(tag_data) == 4:
                                return struct.unpack('>I', tag_data)[0]
                            else:
                                return int.from_bytes(tag_data, byteorder='big')
                        elif tag_number == 3:  # Integer
                            if len(tag_data) == 1:
                                return struct.unpack('>b', tag_data)[0]
                            elif len(tag_data) == 2:
                                return struct.unpack('>h', tag_data)[0]
                            elif len(tag_data) == 4:
                                return struct.unpack('>i', tag_data)[0]
                            else:
                                return int.from_bytes(tag_data, byteorder='big', signed=True)
                        elif tag_number == 4:  # Real
                            return struct.unpack('>f', tag_data)[0]
                        elif tag_number == 5:  # Double
                            return struct.unpack('>d', tag_data)[0]
                        elif tag_number == 7:  # CharacterString
                            return tag_data.decode('utf-8')
                        elif tag_number == 9:  # Enumerated
                            return int.from_bytes(tag_data, byteorder='big')
                        else:
                            return value_str
            else:
                # Already readable value
                return value_str

        except Exception as e:
            logger.debug(f"Value extraction error: {e}")
            return str(bacnet_value)

    def publish_individual_topic(self, point: Dict, value: Any, timestamp: str):
        """Publish individual point topic"""
        if not point['mqttTopic'] or not self.mqtt_connected:
            return False

        try:
            payload = {
                "value": float(value) if isinstance(value, (int, float)) else value,
                "timestamp": timestamp,
                "units": point['units'],
                "quality": "good",
                "dis": point['dis'],
                "haystackName": point['haystackPointName'],
                "deviceIp": point['ipAddress'],
                "deviceId": point['deviceId'],
                "objectType": point['objectType'],
                "objectInstance": point['objectInstance']
            }

            self.mqtt_client.publish(
                topic=point['mqttTopic'],
                payload=json.dumps(payload),
                qos=point['qos'],
                retain=True
            )

            return True
        except Exception as e:
            logger.error(f"Failed to publish individual topic {point['mqttTopic']}: {e}")
            return False

    def publish_equipment_batch(self, site_id: str, equipment_type: str, equipment_id: str,
                                 points_data: List[Dict], timestamp: str, poll_stats: Dict):
        """Publish equipment-level batch"""
        try:
            # Normalize to lowercase to match individual topic format
            site_normalized = site_id.lower().replace(' ', '_')
            equipment_type_normalized = equipment_type.lower()
            equipment_name = f"{equipment_type_normalized}_{equipment_id}"
            batch_topic = f"{site_normalized}/{equipment_name}/batch"

            payload = {
                "timestamp": timestamp,
                "site": site_id,
                "equipment": equipment_name,
                "equipmentType": equipment_type,
                "equipmentId": equipment_id,
                "points": points_data,
                "metadata": {
                    "pollCycle": self.poll_cycle,
                    "totalPoints": poll_stats['total'],
                    "successfulReads": poll_stats['success'],
                    "failedReads": poll_stats['failed'],
                    "pollDuration": poll_stats['duration']
                }
            }

            self.mqtt_client.publish(
                topic=batch_topic,
                payload=json.dumps(payload),
                qos=1,
                retain=False
            )

            logger.info(f"📦 Published batch: {batch_topic} ({len(points_data)} points)")
            return True
        except Exception as e:
            logger.error(f"Failed to publish equipment batch: {e}")
            return False

    async def poll_and_publish(self):
        """Main polling loop - checks each point's individual interval"""
        points = self.get_enabled_points()

        if not points:
            logger.warning("No enabled points found, skipping poll cycle")
            return

        cycle_start = time.time()
        current_time = cycle_start
        timestamp = datetime.now(self.timezone).isoformat()

        # Calculate next minute boundary for minute-aligned polling
        next_minute = math.ceil(current_time / 60) * 60
        next_minute_time = datetime.fromtimestamp(next_minute, self.timezone).strftime('%H:%M:%S')

        # Group points by equipment
        equipment_groups = defaultdict(list)

        # Statistics
        total_reads = 0
        successful_reads = 0
        failed_reads = 0
        skipped_reads = 0
        individual_publishes = 0
        batch_publishes = 0

        # Poll each point (only if interval elapsed)
        for point in points:
            point_id = point['id']
            poll_interval = point['pollInterval']

            # For new points, initialize to minute-aligned polling
            if point_id not in self.point_last_poll:
                # Set last poll time so point will poll at next minute boundary
                # Formula: last_poll = next_minute - poll_interval
                self.point_last_poll[point_id] = next_minute - poll_interval
                logger.info(f"📅 Point {point['pointName']} (ID {point_id}) initialized for minute-aligned polling (next poll at {next_minute_time})")
                # Note: We'll skip this point now and poll it at the minute boundary
                skipped_reads += 1
                continue

            # Check if enough time has passed since last poll
            last_poll = self.point_last_poll.get(point_id, 0)
            time_since_last_poll = current_time - last_poll

            if time_since_last_poll < poll_interval:
                # Not time to poll this point yet
                skipped_reads += 1
                continue

            total_reads += 1

            # Read from BACnet
            value = await self.read_with_retry(
                device_ip=point['ipAddress'],
                device_port=point['port'],
                device_id=point['deviceId'],
                object_type=point['objectType'],
                object_instance=point['objectInstance']
            )

            if value is not None:
                successful_reads += 1

                # Update last poll time for this point
                self.point_last_poll[point_id] = current_time

                # Publish individual topic
                if self.publish_individual_topic(point, value, timestamp):
                    individual_publishes += 1

                # Prepare for batch
                if point['siteId'] and point['equipmentType'] and point['equipmentId']:
                    equipment_key = (point['siteId'], point['equipmentType'], point['equipmentId'])

                    point_data = {
                        "name": f"{point['objectType']}{point['objectInstance']}",
                        "dis": point['dis'],
                        "haystackName": point['haystackPointName'],
                        "value": float(value) if isinstance(value, (int, float)) else value,
                        "units": point['units'],
                        "quality": "good",
                        "objectType": point['objectType'],
                        "objectInstance": point['objectInstance']
                    }

                    equipment_groups[equipment_key].append(point_data)

                # Update database
                try:
                    cursor = self.db_conn.cursor()
                    cursor.execute(
                        'UPDATE "Point" SET "lastValue" = %s, "lastPollTime" = %s WHERE id = %s',
                        (str(value), timestamp, point['id'])
                    )
                    self.db_conn.commit()
                    cursor.close()
                except Exception as e:
                    logger.debug(f"Failed to update last value for point {point['id']}: {e}")
            else:
                failed_reads += 1

        # Publish equipment batches (only if enabled in settings)
        cycle_duration = time.time() - cycle_start

        if self.enable_batch_publishing:
            for (site_id, equipment_type, equipment_id), points_data in equipment_groups.items():
                poll_stats = {
                    'total': len(points_data),
                    'success': len(points_data),
                    'failed': 0,
                    'duration': round(cycle_duration, 2)
                }

                if self.publish_equipment_batch(site_id, equipment_type, equipment_id, points_data, timestamp, poll_stats):
                    batch_publishes += 1

        # Log summary (only if we actually polled something)
        if total_reads > 0:
            self.poll_cycle += 1
            logger.info(f"✅ Poll Cycle #{self.poll_cycle} complete:")
            logger.info(f"   - Points checked: {len(points)} ({total_reads} polled, {skipped_reads} skipped)")
            logger.info(f"   - Reads: {successful_reads}/{total_reads} successful")
            logger.info(f"   - Individual topics: {individual_publishes} published")
            logger.info(f"   - Batch topics: {batch_publishes} published")
            logger.info(f"   - Duration: {cycle_duration:.2f}s")

    async def run(self):
        """Main worker loop"""
        # Connect to services
        if not self.connect_database():
            logger.error("Cannot start without database connection")
            return 1

        # Load system settings from database (timezone, etc)
        self.load_system_settings()

        # Load MQTT configuration from database
        self.load_mqtt_config()

        if not self.connect_mqtt():
            logger.error("Cannot start without MQTT connection")
            return 1

        # Initialize BACnet (after event loop is running)
        if not self.initialize_bacnet():
            logger.error("Cannot start without BACnet stack")
            return 1

        logger.info("🚀 BacPipes MQTT Publisher started successfully")
        logger.info("Polling points based on individual intervals (Ctrl+C to stop)")

        # Main loop - check every 5 seconds for points that need polling
        while not shutdown_requested:
            try:
                await self.poll_and_publish()
            except Exception as e:
                logger.error(f"Error in poll cycle: {e}", exc_info=True)

            # Check again in 5 seconds
            await asyncio.sleep(5)

        # Cleanup
        logger.info("Shutting down gracefully...")

        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("Disconnected from MQTT broker")

        if self.db_conn:
            self.db_conn.close()
            logger.info("Disconnected from database")

        logger.info("Shutdown complete")
        return 0


def main():
    """Entry point - manage event loop for BACpypes3"""
    # Create or get the event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    publisher = MqttPublisher()

    try:
        return loop.run_until_complete(publisher.run())
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
        return 0
    finally:
        # Cleanup
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
        finally:
            loop.close()


if __name__ == "__main__":
    sys.exit(main())

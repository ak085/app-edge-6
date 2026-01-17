"""Paho MQTT client wrapper."""

import json
import ssl
import time
import logging
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    """Paho MQTT client wrapper for BacPipes."""

    def __init__(
        self,
        broker: str,
        port: int = 1883,
        client_id: str = "bacpipes_worker",
        username: Optional[str] = None,
        password: Optional[str] = None,
        tls_enabled: bool = False,
        tls_insecure: bool = False,
        ca_cert_path: Optional[str] = None,
    ):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.tls_enabled = tls_enabled
        self.tls_insecure = tls_insecure
        self.ca_cert_path = ca_cert_path

        self.client: Optional[mqtt.Client] = None
        self.connected = False

        # Callbacks
        self.on_message_callback: Optional[Callable] = None

        # Subscription topics (added after connect)
        self.subscribe_topics: List[tuple] = []  # List of (topic, qos)

        # Tracking
        self.last_data_flow_time: Optional[float] = None
        self.messages_published = 0

    def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=self.client_id,
            )
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            # Authentication
            if self.username:
                self.client.username_pw_set(self.username, self.password or '')
                logger.info(f"MQTT authentication configured (user: {self.username})")

            # TLS
            if self.tls_enabled:
                self._configure_tls()

            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()

            # Wait for connection
            time.sleep(2)

            if self.connected:
                logger.info(f"Connected to MQTT broker {self.broker}:{self.port}")
            else:
                logger.warning(f"MQTT broker unreachable at {self.broker}:{self.port}")

            return True

        except Exception as e:
            logger.warning(f"Failed to connect to MQTT broker: {e}")
            self.connected = False
            return True  # Graceful degradation

    def _configure_tls(self):
        """Configure TLS for MQTT connection."""
        import os

        if self.tls_insecure:
            self.client.tls_set(cert_reqs=ssl.CERT_NONE)
            self.client.tls_insecure_set(True)
            logger.warning("TLS configured with INSECURE mode")
        else:
            ca_cert = self.ca_cert_path
            if ca_cert:
                if not os.path.exists(ca_cert):
                    logger.error(f"CA certificate not found: {ca_cert}")
                    ca_cert = None
                elif not os.access(ca_cert, os.R_OK):
                    logger.error(f"CA certificate not readable: {ca_cert}")
                    ca_cert = None

            if ca_cert:
                self.client.tls_set(
                    ca_certs=ca_cert,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS,
                )
                logger.info(f"TLS configured with CA: {ca_cert}")
            else:
                self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
                logger.info("TLS configured with system CA bundle")

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connection established")

            # Subscribe to all configured topics
            for topic, qos in self.subscribe_topics:
                client.subscribe(topic, qos=qos)
                logger.info(f"Subscribed to {topic} (QoS {qos})")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def add_subscription(self, topic: str, qos: int = 1):
        """Add a topic to subscribe to (call before connect or will be added on reconnect)."""
        if (topic, qos) not in self.subscribe_topics:
            self.subscribe_topics.append((topic, qos))
            logger.info(f"Added subscription: {topic} (QoS {qos})")
            # If already connected, subscribe immediately
            if self.connected and self.client:
                self.client.subscribe(topic, qos=qos)

    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback."""
        self.connected = False
        if rc != 0:
            logger.warning(f"MQTT unexpected disconnection (code {rc})")

    def _on_message(self, client, userdata, msg):
        """MQTT message callback."""
        if self.on_message_callback:
            self.on_message_callback(msg.topic, msg.payload)

    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("Disconnected from MQTT broker")

    def reconnect(self) -> bool:
        """Attempt to reconnect to MQTT broker."""
        if self.connected:
            return True

        if self.client:
            try:
                self.client.reconnect()
                time.sleep(1)
                return self.connected
            except Exception as e:
                logger.warning(f"MQTT reconnection failed: {e}")
                return False
        else:
            return self.connect()

    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        qos: int = 1,
        retain: bool = False,
    ) -> bool:
        """Publish a message to MQTT.

        Args:
            topic: MQTT topic
            payload: Dictionary to be JSON-encoded
            qos: Quality of service (0, 1, 2)
            retain: Retain flag

        Returns:
            True if published successfully
        """
        if not self.connected or not self.client:
            return False

        try:
            self.client.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=qos,
                retain=retain,
            )

            # Track data flow
            self.last_data_flow_time = time.time()
            self.messages_published += 1

            return True

        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return False

    def publish_point_value(
        self,
        topic: str,
        value: Any,
        units: Optional[str],
        dis: Optional[str],
        haystack_name: Optional[str],
        object_type: str,
        object_instance: int,
        timezone_offset: int,
        qos: int = 1,
    ) -> bool:
        """Publish a BACnet point value."""
        if value is None:
            return False

        # Validate value
        if isinstance(value, str) and ("bacpypes3" in value or "object at" in value):
            logger.error(f"Prevented publishing object string for {topic}")
            return False

        # Clean value
        if isinstance(value, (int, float)):
            clean_value = float(value)
        elif isinstance(value, bool):
            clean_value = bool(value)
        elif isinstance(value, str):
            clean_value = str(value)
        else:
            clean_value = str(value)

        timestamp = datetime.utcnow().isoformat() + "Z"

        payload = {
            "value": clean_value,
            "timestamp": timestamp,
            "tz": timezone_offset,
            "units": units,
            "quality": "good",
            "dis": dis,
            "haystackName": haystack_name,
            "objectType": object_type,
            "objectInstance": object_instance,
        }

        return self.publish(topic, payload, qos=qos, retain=False)

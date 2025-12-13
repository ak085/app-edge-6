#!/usr/bin/env python3
"""
BacPipes MQTT Publisher - M4 Implementation (BACpypes3)
Publishes BACnet data to MQTT broker:
- Individual point topics: {site}/{equipment}/{point}/presentValue

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
import hashlib
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

# Discovery coordination lock file
DISCOVERY_LOCK_FILE = "/tmp/bacnet_discovery_active"

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

        self.mqtt_broker = os.getenv('MQTT_BROKER', '10.0.60.3')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.mqtt_client_id = os.getenv('MQTT_CLIENT_ID', 'bacpipes_worker')

        self.bacnet_ip = os.getenv('BACNET_IP', '192.168.1.35')
        self.bacnet_port = int(os.getenv('BACNET_PORT', '47808'))
        self.bacnet_device_id = int(os.getenv('BACNET_DEVICE_ID', '3056496'))

        # TimescaleDB configuration (for direct historical writes)
        self.timescaledb_host = os.getenv('TIMESCALEDB_HOST', 'timescaledb')
        self.timescaledb_port = int(os.getenv('TIMESCALEDB_PORT', '5432'))
        self.timescaledb_db = os.getenv('TIMESCALEDB_DB', 'timescaledb')
        self.timescaledb_user = os.getenv('TIMESCALEDB_USER', 'anatoli')
        self.timescaledb_password = os.getenv('TIMESCALEDB_PASSWORD', '')

        self.poll_interval = int(os.getenv('POLL_INTERVAL', '60'))
        self.timezone = pytz.timezone(os.getenv('TZ', 'Asia/Kuala_Lumpur'))

        # Retry configuration (from proven working script)
        self.max_retries = 3
        self.base_timeout = 6000  # 6 seconds
        self.exponential_backoff = True

        # State
        self.db_conn = None  # PostgreSQL (configuration)
        self.timescaledb_conn = None  # TimescaleDB (historical data)
        self.timescaledb_connected = False  # Track TimescaleDB availability
        self.mqtt_client = None
        self.mqtt_connected = False
        self.poll_cycle = 0
        self.bacnet_app = None  # Will be initialized after event loop starts
        self.point_last_poll = {}  # Track last poll time per point ID
        self.pending_write_commands = []  # Queue for MQTT write commands (processed in main loop)

        logger.info("=== BacPipes MQTT Publisher Configuration ===")
        logger.info(f"Database: {self.db_host}:{self.db_port}/{self.db_name}")
        logger.info(f"TimescaleDB: {self.timescaledb_host}:{self.timescaledb_port}/{self.timescaledb_db}")
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

    def connect_timescaledb(self):
        """Connect to TimescaleDB for historical data storage (graceful degradation)"""
        try:
            self.timescaledb_conn = psycopg2.connect(
                host=self.timescaledb_host,
                port=self.timescaledb_port,
                database=self.timescaledb_db,
                user=self.timescaledb_user,
                password=self.timescaledb_password,
                connect_timeout=10
            )
            self.timescaledb_conn.autocommit = True  # Auto-commit for time-series inserts
            self.timescaledb_connected = True
            logger.info("✅ Connected to TimescaleDB for historical data storage")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Failed to connect to TimescaleDB: {e}")
            logger.warning(f"⚠️  Worker will continue without local historical storage")
            logger.warning(f"⚠️  Historical data will only be saved via MQTT → Telegraf pipeline")
            self.timescaledb_connected = False
            return True  # Return True for graceful degradation

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
        """Load MQTT configuration from database

        Returns:
            True if configuration is complete and ready
            False if waiting for first-time setup (broker is NULL)
        """
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                SELECT broker, port, "clientId", username, password,
                       "tlsEnabled", "tlsInsecure", "caCertPath", "clientCertPath", "clientKeyPath",
                       "subscribeEnabled", "subscribeTopicPattern", "subscribeQos"
                FROM "MqttConfig" LIMIT 1
            ''')
            result = cursor.fetchone()
            cursor.close()

            if result:
                db_broker = result['broker']

                # Check if first-run setup is needed (broker is NULL)
                if db_broker is None:
                    logger.warning("⏸️  MQTT broker not configured - waiting for first-time setup")
                    logger.info("   👉 Complete setup wizard at: http://your-ip:3001")
                    logger.info("   ⏳ Worker will start automatically after configuration")
                    return False

                # Use configured broker from database
                if db_broker and db_broker.strip():
                    self.mqtt_broker = db_broker
                    self.mqtt_port = result['port']
                    self.mqtt_client_id = result['clientId'] or self.mqtt_client_id

                    # Authentication
                    self.mqtt_username = result['username']
                    self.mqtt_password = result['password']

                    # TLS Configuration
                    self.mqtt_tls_enabled = result['tlsEnabled'] or False
                    self.mqtt_tls_insecure = result['tlsInsecure'] or False
                    self.mqtt_ca_cert_path = result['caCertPath']
                    self.mqtt_client_cert_path = result['clientCertPath']
                    self.mqtt_client_key_path = result['clientKeyPath']

                    # Subscription Configuration
                    self.mqtt_subscribe_enabled = result['subscribeEnabled'] or False
                    self.mqtt_subscribe_topic_pattern = result['subscribeTopicPattern'] or 'bacnet/override/#'
                    self.mqtt_subscribe_qos = result['subscribeQos'] if result['subscribeQos'] is not None else 1

                    logger.info(f"📋 MQTT Configuration:")
                    logger.info(f"   - Broker: {self.mqtt_broker}:{self.mqtt_port}")
                    logger.info(f"   - Client ID: {self.mqtt_client_id}")
                    if self.mqtt_username:
                        logger.info(f"   - Authentication: Enabled (user: {self.mqtt_username})")
                    if self.mqtt_tls_enabled:
                        logger.info(f"   - TLS: Enabled (insecure: {self.mqtt_tls_insecure})")
                        if self.mqtt_ca_cert_path:
                            logger.info(f"   - CA Cert: {self.mqtt_ca_cert_path}")
                    if self.mqtt_subscribe_enabled:
                        logger.info(f"   - Override Subscription: {self.mqtt_subscribe_topic_pattern} (QoS {self.mqtt_subscribe_qos})")

                    # Warn if using default placeholder IP
                    if self.mqtt_broker in ['10.0.60.3', '10.0.60.2', '192.168.1.35']:
                        logger.warning(f"   ⚠️  Using default placeholder IP - configure actual broker via Settings GUI")
                        logger.info(f"   💡 http://your-ip:3001/settings")
                    return True
                else:
                    logger.warning("⚠️  MQTT broker empty - waiting for configuration")
                    return False
            else:
                logger.warning("⏸️  No MQTT config found - waiting for first-time setup")
                logger.info("   👉 Complete setup wizard at: http://your-ip:3001")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to load MQTT config: {e}")
            logger.warning("⚠️  Using environment defaults")
            return False

    def _get_config_hash(self):
        """Generate hash of MQTT config for change detection"""
        broker = getattr(self, 'mqtt_broker', '') or ''
        port = getattr(self, 'mqtt_port', 1883)
        username = getattr(self, 'mqtt_username', '') or ''
        password = getattr(self, 'mqtt_password', '') or ''
        tls_enabled = getattr(self, 'mqtt_tls_enabled', False)
        ca_cert = getattr(self, 'mqtt_ca_cert_path', '') or ''
        subscribe_enabled = getattr(self, 'mqtt_subscribe_enabled', False)
        subscribe_pattern = getattr(self, 'mqtt_subscribe_topic_pattern', '') or ''

        config_str = f"{broker}:{port}:{username}:{password}:{tls_enabled}:{ca_cert}:{subscribe_enabled}:{subscribe_pattern}"
        return hashlib.md5(config_str.encode()).hexdigest()

    def _check_config_changes(self):
        """Check if MQTT config changed, trigger reconnect if needed

        Called periodically (every 10 seconds) to detect credential/TLS changes
        made via the Settings GUI and apply them without restart.
        """
        old_hash = getattr(self, '_config_hash', None)

        # Reload config from database
        self.load_mqtt_config()
        new_hash = self._get_config_hash()

        if old_hash and old_hash != new_hash:
            logger.info("🔄 MQTT configuration changed via Settings GUI - reconnecting...")
            self._force_reconnect()

        self._config_hash = new_hash

    def _force_reconnect(self):
        """Force MQTT reconnection with new configuration"""
        try:
            if self.mqtt_client:
                logger.info("🔌 Disconnecting from current MQTT broker...")
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                self.mqtt_client = None
                self.mqtt_connected = False
        except Exception as e:
            logger.warning(f"⚠️  Error during disconnect: {e}")
            self.mqtt_connected = False

        # Reconnect with new config
        logger.info("🔌 Connecting with updated MQTT configuration...")
        self.connect_mqtt()

    def _auto_detect_local_ip(self):
        """Auto-detect local IP address for BACnet interface"""
        import socket
        try:
            # Create a socket and connect to external address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            # Fallback: try to get from hostname
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip and not local_ip.startswith('127.'):
                    return local_ip
            except Exception:
                pass
            return None

    def load_bacnet_config(self):
        """Load BACnet configuration from database SystemSettings

        Returns:
            True if configuration is complete and ready
            False if waiting for first-time setup (bacnetIp is NULL)
        """
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT "bacnetIp", "bacnetPort", "bacnetDeviceId" FROM "SystemSettings" LIMIT 1')
            result = cursor.fetchone()
            cursor.close()

            if result:
                db_ip = result['bacnetIp']
                db_port = result['bacnetPort']
                db_device_id = result['bacnetDeviceId']

                # Check if first-run setup is needed (bacnetIp is NULL)
                if db_ip is None:
                    logger.warning("⏸️  BACnet IP not configured - waiting for first-time setup")
                    logger.info("   👉 Complete setup wizard at: http://your-ip:3001")
                    logger.info("   ⏳ Worker will start automatically after configuration")
                    return False

                # Use configured IP from database
                if db_ip and db_ip.strip():
                    self.bacnet_ip = db_ip
                    logger.info(f"📋 BACnet IP from database: {self.bacnet_ip}")
                else:
                    logger.warning("⚠️  BACnet IP empty - waiting for configuration")
                    return False

                self.bacnet_port = db_port if db_port else self.bacnet_port
                self.bacnet_device_id = db_device_id if db_device_id else self.bacnet_device_id

                logger.info(f"📋 BACnet Configuration:")
                logger.info(f"   - Interface: {self.bacnet_ip}:{self.bacnet_port}")
                logger.info(f"   - Device ID: {self.bacnet_device_id}")
                return True
            else:
                logger.warning("⏸️  No system settings found - waiting for first-time setup")
                logger.info("   👉 Complete setup wizard at: http://your-ip:3001")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to load BACnet config: {e}")
            return False

    def connect_mqtt(self):
        """Connect to MQTT broker (graceful degradation - doesn't fail startup)"""
        try:
            self.mqtt_client = mqtt.Client(client_id=self.mqtt_client_id)
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            self.mqtt_client.on_message = self.on_mqtt_message

            # Apply authentication if configured
            if hasattr(self, 'mqtt_username') and self.mqtt_username:
                self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password or '')
                logger.info(f"🔐 MQTT authentication configured (user: {self.mqtt_username})")

            # Apply TLS if configured
            if hasattr(self, 'mqtt_tls_enabled') and self.mqtt_tls_enabled:
                import ssl
                ca_cert = getattr(self, 'mqtt_ca_cert_path', None)
                client_cert = getattr(self, 'mqtt_client_cert_path', None)
                client_key = getattr(self, 'mqtt_client_key_path', None)
                tls_insecure = getattr(self, 'mqtt_tls_insecure', False)

                # Configure TLS
                if ca_cert or client_cert:
                    self.mqtt_client.tls_set(
                        ca_certs=ca_cert,
                        certfile=client_cert,
                        keyfile=client_key,
                        cert_reqs=ssl.CERT_NONE if tls_insecure else ssl.CERT_REQUIRED,
                        tls_version=ssl.PROTOCOL_TLS
                    )
                    if tls_insecure:
                        self.mqtt_client.tls_insecure_set(True)
                        logger.warning(f"🔓 TLS configured with INSECURE mode (certificate verification disabled)")
                    else:
                        logger.info(f"🔒 TLS configured with certificate verification")
                else:
                    # TLS enabled but no certs - use default CA bundle
                    self.mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE if tls_insecure else ssl.CERT_REQUIRED)
                    logger.info(f"🔒 TLS configured with system CA bundle")

            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()

            # Wait for connection
            time.sleep(2)

            if self.mqtt_connected:
                logger.info(f"✅ Connected to MQTT broker {self.mqtt_broker}:{self.mqtt_port}")
            else:
                logger.warning(f"⚠️  MQTT broker unreachable at {self.mqtt_broker}:{self.mqtt_port}")
                logger.warning(f"⚠️  Worker will continue without MQTT publishing. Configure broker in Settings GUI.")

            # Always return True - graceful degradation (app works without MQTT)
            return True
        except Exception as e:
            logger.warning(f"⚠️  Failed to connect to MQTT broker: {e}")
            logger.warning(f"⚠️  Worker will continue without MQTT publishing. Configure broker in Settings GUI.")
            self.mqtt_connected = False
            # Don't fail startup - return True for graceful degradation
            return True

    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            logger.info("MQTT connection established successfully")

            # Subscribe to write command topic
            client.subscribe("bacnet/write/command", qos=1)
            logger.info("📝 Subscribed to bacnet/write/command topic")

            # Subscribe to override topic if enabled
            if hasattr(self, 'mqtt_subscribe_enabled') and self.mqtt_subscribe_enabled:
                topic_pattern = getattr(self, 'mqtt_subscribe_topic_pattern', 'bacnet/override/#')
                qos = getattr(self, 'mqtt_subscribe_qos', 1)
                client.subscribe(topic_pattern, qos=qos)
                logger.info(f"📥 Subscribed to override topic: {topic_pattern} (QoS {qos})")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        if rc != 0:
            logger.warning(f"⚠️  MQTT unexpected disconnection (code {rc}), will auto-reconnect")
            self.mqtt_connected = False

    def reconnect_mqtt(self):
        """Attempt to reconnect to MQTT broker if disconnected

        Reloads configuration from database before reconnection attempt
        to pick up any broker IP changes made via Settings GUI.
        """
        if not self.mqtt_connected:
            # Reload MQTT config from database (pick up any changes from Settings GUI)
            old_broker = self.mqtt_broker
            if self.load_mqtt_config():
                # Check if broker changed - need to recreate client
                if old_broker != self.mqtt_broker:
                    logger.info(f"🔄 MQTT broker changed from {old_broker} to {self.mqtt_broker}")
                    # Stop old client if exists
                    if self.mqtt_client:
                        try:
                            self.mqtt_client.loop_stop()
                            self.mqtt_client.disconnect()
                        except Exception:
                            pass
                    # Create new connection with updated broker
                    return self.connect_mqtt()

                # Same broker - try reconnect with existing client
                if self.mqtt_client:
                    try:
                        logger.info(f"🔄 Attempting MQTT reconnection to {self.mqtt_broker}:{self.mqtt_port}...")
                        self.mqtt_client.reconnect()
                        # Brief wait to check connection
                        time.sleep(1)
                        if self.mqtt_connected:
                            logger.info(f"✅ MQTT reconnected successfully")
                            return True
                        else:
                            logger.debug(f"   MQTT reconnection in progress...")
                            return False
                    except Exception as e:
                        logger.debug(f"   MQTT reconnection failed: {e}")
                        return False
                else:
                    # No client exists - create new connection
                    return self.connect_mqtt()
            else:
                logger.debug("   MQTT config not ready, skipping reconnection")
                return False
        return self.mqtt_connected

    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages (write commands and override values) - QUEUE BASED APPROACH"""
        try:
            if msg.topic == "bacnet/write/command":
                # Parse write command
                command = json.loads(msg.payload.decode())
                logger.info(f"📥 Received write command on MQTT: {command.get('jobId')}")

                # Add to queue (don't create asyncio task from MQTT callback thread!)
                # The main polling loop will process this queue
                self.pending_write_commands.append(command)
                logger.info(f"📝 Write command queued for processing (queue size: {len(self.pending_write_commands)})")

            elif msg.topic.startswith("bacnet/override/"):
                # Handle setpoint override from ML/external system
                self._handle_override_message(msg)

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in MQTT message: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing MQTT message: {e}", exc_info=True)

    def _handle_override_message(self, msg):
        """Process setpoint override message from ML/external system

        Override topic format: bacnet/override/{site}/{equip}/{equipId}/{func}/{qty}/{substance}/{location}
        Corresponding publish topic: bacnet/{site}/{equip}/{equipId}/{func}/{qty}/{substance}/{location}
        """
        try:
            payload = json.loads(msg.payload.decode())
            value = payload.get('value')
            priority = payload.get('priority', 8)
            source = payload.get('source', 'mqtt_override')

            if value is None:
                logger.warning(f"⚠️  Override message missing 'value' field: {msg.topic}")
                return

            # Convert override topic to publish topic to find the point
            # bacnet/override/klcc/ahu/12/sp/temp/air/supply -> bacnet/klcc/ahu/12/sp/temp/air/supply
            publish_topic = msg.topic.replace('bacnet/override/', 'bacnet/', 1)

            # Find point by MQTT topic
            point = self._find_point_by_topic(publish_topic)
            if not point:
                logger.warning(f"⚠️  No point found for override topic: {msg.topic}")
                return

            # Verify it's a setpoint (position-4 in haystack name should be 'sp')
            haystack_name = point.get('haystackPointName', '')
            if haystack_name:
                parts = haystack_name.split('.')
                if len(parts) >= 4 and parts[3] != 'sp':
                    logger.warning(f"⚠️  Override rejected: Point {haystack_name} is not a setpoint (position-4 = '{parts[3]}', expected 'sp')")
                    return

            logger.info(f"📥 Received override for {point['pointName']}: value={value}, priority={priority}, source={source}")

            # Create write command and queue it
            import uuid
            write_command = {
                'jobId': str(uuid.uuid4()),
                'deviceId': point['deviceId'],
                'deviceIp': point['ipAddress'],
                'objectType': point['objectType'],
                'objectInstance': point['objectInstance'],
                'value': value,
                'priority': priority,
                'release': False,
                'source': source,
                'pointName': point['pointName'],
                'originalTopic': msg.topic
            }
            self.pending_write_commands.append(write_command)
            logger.info(f"📝 Override queued as write command (queue size: {len(self.pending_write_commands)})")

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in override message: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing override message: {e}", exc_info=True)

    def _find_point_by_topic(self, mqtt_topic: str) -> Optional[Dict]:
        """Find point in database by MQTT topic"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                SELECT p.id, p."pointName", p."objectType", p."objectInstance",
                       p."haystackPointName", p."isWritable",
                       d."deviceId", d."ipAddress", d.port
                FROM "Point" p
                JOIN "Device" d ON p."deviceId" = d.id
                WHERE p."mqttTopic" = %s
                LIMIT 1
            ''', (mqtt_topic,))
            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"❌ Error finding point by topic: {e}")
            return None

    async def execute_write_command(self, command: Dict):
        """Execute BACnet write command with comprehensive validation"""
        job_id = command.get('jobId')
        device_ip = command.get('deviceIp')
        device_id = command.get('deviceId')
        object_type = command.get('objectType')
        object_instance = command.get('objectInstance')
        value = command.get('value')
        priority = command.get('priority', 8)
        release = command.get('release', False)
        point_name = command.get('pointName', 'Unknown')
        source = command.get('source', 'edge')

        logger.info(f"📝 Executing write command {job_id} (source: {source})")
        logger.info(f"  Device: {device_id} ({device_ip})")
        logger.info(f"  Point: {point_name} ({object_type}-{object_instance})")
        logger.info(f"  Action: {'Release priority' if release else 'Write value'} {'' if release else value}")
        logger.info(f"  Priority: {priority}")

        validation_errors = []

        # VALIDATION 1: Query point from database
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT
                    p.id, p."pointName", p."haystackPointName", p."isWritable",
                    p."minPresValue", p."maxPresValue",
                    d."ipAddress", d.port
                FROM "Point" p
                JOIN "Device" d ON p."deviceId" = d.id
                WHERE d."deviceId" = %s
                  AND p."objectType" = %s
                  AND p."objectInstance" = %s
                LIMIT 1
            """, (device_id, object_type, object_instance))

            point = cursor.fetchone()
            cursor.close()

            if not point:
                validation_errors.append({
                    "field": "point",
                    "code": "POINT_NOT_FOUND",
                    "message": f"Point not found in database: device={device_id}, {object_type}:{object_instance}"
                })
                result = self._create_validation_error_result(job_id, device_id, point_name, validation_errors)
                self.mqtt_client.publish("bacnet/write/result", json.dumps(result), qos=1)
                logger.error(f"❌ Write command {job_id} failed validation: Point not found")
                return

        except Exception as e:
            logger.error(f"❌ Database query failed: {e}", exc_info=True)
            validation_errors.append({
                "field": "database",
                "code": "DATABASE_ERROR",
                "message": f"Database query failed: {str(e)}"
            })
            result = self._create_validation_error_result(job_id, device_id, point_name, validation_errors)
            self.mqtt_client.publish("bacnet/write/result", json.dumps(result), qos=1)
            return

        # Extract point data
        point_id = point['id']
        haystack_name = point['haystackPointName']
        is_writable = point['isWritable']
        min_val = point.get('minPresValue')
        max_val = point.get('maxPresValue')
        actual_device_ip = point['ipAddress']
        actual_device_port = point['port']

        # VALIDATION 2: Check Haystack name position-4 must be "sp"
        if haystack_name:
            parts = haystack_name.split('.')
            if len(parts) >= 4:
                position_4 = parts[3]
                if position_4 != 'sp':
                    validation_errors.append({
                        "field": "haystackName",
                        "code": "INVALID_POINT_FUNCTION",
                        "message": f"Write not allowed: position-4 must be 'sp' (setpoint), found '{position_4}'",
                        "haystackName": haystack_name,
                        "expected": "sp",
                        "actual": position_4
                    })
            else:
                validation_errors.append({
                    "field": "haystackName",
                    "code": "INVALID_HAYSTACK_FORMAT",
                    "message": f"Invalid haystack name format: {haystack_name}",
                    "expected": "minimum 4 parts (site.equip.id.sp...)",
                    "actual": f"{len(parts)} parts"
                })
        else:
            logger.warning(f"⚠️  Point {point_name} has no haystack name - skipping position-4 validation")

        # VALIDATION 3: Check isWritable flag
        if not is_writable:
            validation_errors.append({
                "field": "isWritable",
                "code": "POINT_NOT_WRITABLE",
                "message": f"Point '{point_name}' is not writable (isWritable=false)"
            })

        # VALIDATION 4: Validate priority range (1-16)
        if not (1 <= priority <= 16):
            validation_errors.append({
                "field": "priority",
                "code": "INVALID_PRIORITY",
                "message": f"Priority must be between 1 and 16, got {priority}",
                "expected": "1-16",
                "actual": priority
            })

        # VALIDATION 5: Validate value range (if configured and not releasing)
        if not release and value is not None:
            try:
                value_float = float(value)

                if min_val is not None and value_float < min_val:
                    validation_errors.append({
                        "field": "value",
                        "code": "VALUE_BELOW_MINIMUM",
                        "message": f"Value {value_float} is below minimum {min_val}",
                        "min": min_val,
                        "max": max_val,
                        "actual": value_float
                    })

                if max_val is not None and value_float > max_val:
                    validation_errors.append({
                        "field": "value",
                        "code": "VALUE_ABOVE_MAXIMUM",
                        "message": f"Value {value_float} is above maximum {max_val}",
                        "min": min_val,
                        "max": max_val,
                        "actual": value_float
                    })

            except (ValueError, TypeError) as e:
                validation_errors.append({
                    "field": "value",
                    "code": "INVALID_VALUE_TYPE",
                    "message": f"Value must be numeric, got: {value}",
                    "actual": str(value)
                })

        # If validation failed, return error result
        if validation_errors:
            result = self._create_validation_error_result(job_id, device_id, point_name, validation_errors)
            self.mqtt_client.publish("bacnet/write/result", json.dumps(result), qos=1)
            logger.error(f"❌ Write command {job_id} failed validation: {len(validation_errors)} error(s)")
            for error in validation_errors:
                logger.error(f"   - {error['code']}: {error['message']}")
            return

        # ALL VALIDATIONS PASSED - Execute BACnet write
        logger.info(f"✅ All validations passed for write command {job_id}")

        try:
            success, error_msg = await self.write_bacnet_value(
                device_ip=actual_device_ip,
                device_port=actual_device_port,
                object_type=object_type,
                object_instance=object_instance,
                value=value,
                priority=priority,
                release=release
            )

            # Publish result
            result = {
                "jobId": job_id,
                "success": success,
                "timestamp": datetime.now(self.timezone).isoformat(),
                "error": error_msg if not success else None,
                "deviceId": device_id,
                "pointName": point_name,
                "haystackName": haystack_name,
                "value": value,
                "priority": priority,
                "release": release,
                "validationErrors": []
            }

            self.mqtt_client.publish("bacnet/write/result", json.dumps(result), qos=1)

            if success:
                logger.info(f"✅ Write command {job_id} completed successfully")
            else:
                logger.error(f"❌ Write command {job_id} failed: {error_msg}")

        except Exception as e:
            logger.error(f"❌ Exception executing write command {job_id}: {e}", exc_info=True)

            result = {
                "jobId": job_id,
                "success": False,
                "timestamp": datetime.now(self.timezone).isoformat(),
                "error": str(e),
                "deviceId": device_id,
                "pointName": point_name,
                "validationErrors": [{
                    "field": "bacnet",
                    "code": "BACNET_WRITE_EXCEPTION",
                    "message": str(e)
                }]
            }
            self.mqtt_client.publish("bacnet/write/result", json.dumps(result), qos=1)

    def _create_validation_error_result(self, job_id: str, device_id: int, point_name: str, validation_errors: list) -> dict:
        """Create standardized validation error result"""
        return {
            "jobId": job_id,
            "success": False,
            "timestamp": datetime.now(self.timezone).isoformat(),
            "deviceId": device_id,
            "pointName": point_name,
            "error": "Validation failed",
            "validationErrors": validation_errors
        }

    async def process_write_commands(self):
        """Process any pending write commands from the queue (called from main loop)"""
        while self.pending_write_commands:
            command = self.pending_write_commands.pop(0)
            logger.info(f"🔄 Processing write command from queue: {command.get('jobId')}")
            await self.execute_write_command(command)

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
        """Extract readable value from BACnet Any object - improved version"""
        try:
            # First, try direct numeric/boolean type conversion (most common case)
            if isinstance(bacnet_value, (int, float, bool)):
                return bacnet_value

            # Try to extract from common BACpypes3 primitive types
            if hasattr(bacnet_value, 'value'):
                # Many BACpypes3 types have a .value attribute
                extracted = bacnet_value.value
                if isinstance(extracted, (int, float, bool, str)):
                    return extracted

            # Convert to string and check if it's an object representation
            value_str = str(bacnet_value)

            # If it's an object representation string, we need to extract from tagList
            if "bacpypes3" in value_str and "object at" in value_str:
                # This is an object representation, extract from tagList
                if hasattr(bacnet_value, 'tagList') and bacnet_value.tagList:
                    tag_list = list(bacnet_value.tagList)

                    # Find tag with data
                    data_tag = None
                    for tag in tag_list:
                        if hasattr(tag, 'tag_data') and tag.tag_data and len(tag.tag_data) > 0:
                            data_tag = tag
                            break

                    if not data_tag and tag_list:
                        data_tag = tag_list[0]

                    if data_tag and hasattr(data_tag, 'tag_data') and hasattr(data_tag, 'tag_number'):
                        tag_number = data_tag.tag_number
                        tag_data = data_tag.tag_data

                        if not tag_data or len(tag_data) == 0:
                            logger.warning(f"Empty tag data in BACnet value")
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
                        elif tag_number == 4:  # Real (float)
                            return struct.unpack('>f', tag_data)[0]
                        elif tag_number == 5:  # Double
                            return struct.unpack('>d', tag_data)[0]
                        elif tag_number == 7:  # CharacterString
                            return tag_data.decode('utf-8')
                        elif tag_number == 9:  # Enumerated
                            return int.from_bytes(tag_data, byteorder='big')
                        else:
                            logger.warning(f"Unknown BACnet tag type: {tag_number}")
                            return None
                else:
                    logger.warning(f"BACnet object has no tagList: {value_str}")
                    return None
            else:
                # String representation looks clean (not an object), try to parse it
                # This handles numeric strings, boolean strings, etc.
                value_clean = value_str.strip()

                # Try parsing as number
                try:
                    if '.' in value_clean:
                        return float(value_clean)
                    else:
                        return int(value_clean)
                except ValueError:
                    # Not a number, return as string if reasonable length
                    if len(value_clean) < 100:  # Reasonable string length
                        return value_clean
                    else:
                        logger.warning(f"String value too long ({len(value_clean)} chars)")
                        return None

        except Exception as e:
            logger.error(f"❌ Value extraction error: {e}")
            logger.debug(f"   Failed to extract from: {type(bacnet_value)} = {bacnet_value}")
            return None

    async def write_bacnet_value(self, device_ip: str, device_port: int, object_type: str,
                                  object_instance: int, value: Any, priority: int = 8,
                                  release: bool = False) -> tuple[bool, Optional[str]]:
        """
        Write value to BACnet point with priority
        Returns: (success: bool, error_message: Optional[str])
        """
        try:
            # Import write-specific classes from BACpypes3
            from bacpypes3.apdu import WritePropertyRequest
            from bacpypes3.primitivedata import Null, Real, Unsigned, Boolean

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
            }

            obj_type_bacnet = obj_type_map.get(object_type, object_type)

            # Create BACnet address and object identifier
            device_address = Address(f"{device_ip}:{device_port}")
            object_id = ObjectIdentifier(f"{obj_type_bacnet},{object_instance}")

            # Prepare value based on type and release flag
            if release:
                # Release priority (write null to priority array)
                write_value = Null()
            else:
                # Convert value to appropriate BACnet type
                if 'analog' in object_type or object_type in ['multi-state-input', 'multi-state-output', 'multi-state-value']:
                    # Analog points use Real, multi-state use Unsigned
                    if 'multi-state' in object_type:
                        write_value = Unsigned(int(value))
                    else:
                        write_value = Real(float(value))
                elif 'binary' in object_type:
                    # Binary points use Unsigned (0=inactive, 1=active)
                    write_value = Unsigned(1 if value else 0)
                else:
                    # Default to Real
                    write_value = Real(float(value))

            # Create write request
            request = WritePropertyRequest(
                objectIdentifier=object_id,
                propertyIdentifier=PropertyIdentifier('presentValue'),
                destination=device_address
            )

            # Set property value
            request.propertyValue = write_value

            # NOTE: We write directly to presentValue WITHOUT using priority arrays
            # This matches the original working implementation (scripts/05_production_mqtt.py)
            # Priority arrays are not used for setpoint/testing writes
            logger.info(f"Writing value {value} to {object_type}:{object_instance} (priority {priority} not used for direct write)")

            # Send request with timeout
            try:
                response = await asyncio.wait_for(
                    self.bacnet_app.request(request),
                    timeout=10.0  # 10 second timeout
                )

                # Write successful
                logger.info(f"✅ Write successful (response: {type(response).__name__})")
                return (True, None)

            except asyncio.TimeoutError:
                error_msg = "BACnet write request timeout (10s)"
                logger.error(f"❌ {error_msg}")
                return (False, error_msg)
            except Exception as write_error:
                error_msg = f"BACnet write failed: {type(write_error).__name__}: {str(write_error)}"
                logger.error(f"❌ {error_msg}")
                return (False, error_msg)

        except Exception as e:
            error_msg = f"BACnet write error: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return (False, error_msg)

    def publish_individual_topic(self, point: Dict, value: Any, timestamp: str):
        """Publish individual point topic"""
        if not point['mqttTopic'] or not self.mqtt_connected:
            return False

        # Validate value before publishing
        if value is None:
            logger.warning(f"Skipping publish for {point['mqttTopic']}: value is None")
            return False

        # Check if value is an object representation string (should never happen now)
        if isinstance(value, str) and ("bacpypes3" in value or "object at" in value):
            logger.error(f"❌ Prevented publishing object string for {point['mqttTopic']}: {value}")
            return False

        try:
            # Ensure value is JSON-serializable (int, float, str, bool, None)
            clean_value = value
            if isinstance(value, (int, float)):
                clean_value = float(value)
            elif isinstance(value, bool):
                clean_value = bool(value)
            elif isinstance(value, str):
                clean_value = str(value)
            else:
                # Unexpected type, convert to string as last resort
                logger.warning(f"Unexpected value type {type(value)} for {point['mqttTopic']}, converting to string")
                clean_value = str(value)

            payload = {
                "value": clean_value,
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
                retain=False  # No retained messages for time-series data
            )

            return True
        except Exception as e:
            logger.error(f"Failed to publish individual topic {point['mqttTopic']}: {e}")
            return False

    def write_to_timescaledb(self, point: Dict, value: Any, timestamp: str):
        """Write sensor reading directly to TimescaleDB (bypassing MQTT)"""
        if not self.timescaledb_connected or not self.timescaledb_conn:
            return False

        try:
            if value is None:
                return False

            # Prepare data matching sensor_readings schema
            data = {
                'time': timestamp,
                'site_id': point.get('siteId'),
                'equipment_type': point.get('equipmentType'),
                'equipment_id': point.get('equipmentId'),
                'device_id': point['deviceId'],
                'device_name': point.get('deviceName'),
                'device_ip': point['ipAddress'],
                'object_type': point['objectType'],
                'object_instance': point['objectInstance'],
                'point_id': point['id'],
                'point_name': point['pointName'],
                'haystack_name': point.get('haystackPointName'),
                'dis': point.get('dis'),
                'value': float(value) if isinstance(value, (int, float)) else value,
                'units': point.get('units'),
                'quality': 'good',
                'poll_duration': None,
                'poll_cycle': self.poll_cycle
            }

            cursor = self.timescaledb_conn.cursor()
            sql = """
            INSERT INTO sensor_readings (
                time, site_id, equipment_type, equipment_id,
                device_id, device_name, device_ip,
                object_type, object_instance,
                point_id, point_name, haystack_name, dis,
                value, units, quality,
                poll_duration, poll_cycle
            ) VALUES (
                %(time)s, %(site_id)s, %(equipment_type)s, %(equipment_id)s,
                %(device_id)s, %(device_name)s, %(device_ip)s,
                %(object_type)s, %(object_instance)s,
                %(point_id)s, %(point_name)s, %(haystack_name)s, %(dis)s,
                %(value)s, %(units)s, %(quality)s,
                %(poll_duration)s, %(poll_cycle)s
            )
            """
            cursor.execute(sql, data)
            cursor.close()
            return True

        except Exception as e:
            logger.warning(f"⚠️  TimescaleDB write failed for point {point['id']}: {e}")
            self.timescaledb_connected = False  # Mark as disconnected
            logger.warning(f"⚠️  TimescaleDB writes disabled (connection lost)")
            return False

    async def poll_and_publish(self):
        """Main polling loop - checks each point's individual interval"""
        points = self.get_enabled_points()

        if not points:
            logger.warning("No enabled points found, skipping poll cycle")
            return

        cycle_start = time.time()
        current_time = cycle_start
        timestamp = datetime.now(pytz.utc).isoformat()  # Use UTC for database storage (timezone-aware)

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

                # Write to THREE destinations (order matters for data consistency)

                # 1. PostgreSQL - Update last value (CRITICAL - must succeed)
                try:
                    cursor = self.db_conn.cursor()
                    cursor.execute(
                        'UPDATE "Point" SET "lastValue" = %s, "lastPollTime" = %s WHERE id = %s',
                        (str(value), timestamp, point['id'])
                    )
                    self.db_conn.commit()
                    cursor.close()
                except Exception as e:
                    logger.warning(f"⚠️  Failed to update PostgreSQL for point {point['id']}: {e}")

                # 2. TimescaleDB - Historical time-series data (OPTIONAL - graceful degradation)
                self.write_to_timescaledb(point, value, timestamp)

                # 3. MQTT - External subscribers (OPTIONAL - graceful degradation)
                if self.publish_individual_topic(point, value, timestamp):
                    individual_publishes += 1

                # Prepare for batch (existing code)
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

            else:
                failed_reads += 1

        # Calculate cycle duration
        cycle_duration = time.time() - cycle_start

        # Log summary (only if we actually polled something)
        if total_reads > 0:
            self.poll_cycle += 1
            logger.info(f"✅ Poll Cycle #{self.poll_cycle} complete:")
            logger.info(f"   - Points checked: {len(points)} ({total_reads} polled, {skipped_reads} skipped)")
            logger.info(f"   - Reads: {successful_reads}/{total_reads} successful")
            logger.info(f"   - Individual topics: {individual_publishes} published")
            logger.info(f"   - Duration: {cycle_duration:.2f}s")

    async def run(self):
        """Main worker loop"""
        # Connect to services
        if not self.connect_database():
            logger.error("Cannot start without database connection")
            return 1

        # Load system settings from database (timezone, etc)
        self.load_system_settings()

        # Wait for BACnet configuration (first-time setup)
        logger.info("🔍 Checking BACnet configuration...")
        bacnet_ready = self.load_bacnet_config()

        while not bacnet_ready and not shutdown_requested:
            logger.info("⏳ Waiting for BACnet configuration (checking again in 10 seconds)...")
            await asyncio.sleep(10)
            # Reload configuration from database
            bacnet_ready = self.load_bacnet_config()

        if shutdown_requested:
            logger.info("Shutdown requested during configuration wait")
            return 0

        # Wait for MQTT configuration (first-time setup)
        logger.info("🔍 Checking MQTT configuration...")
        mqtt_ready = self.load_mqtt_config()

        while not mqtt_ready and not shutdown_requested:
            logger.info("⏳ Waiting for MQTT configuration (checking again in 10 seconds)...")
            await asyncio.sleep(10)
            # Reload configuration from database
            mqtt_ready = self.load_mqtt_config()

        if shutdown_requested:
            logger.info("Shutdown requested during configuration wait")
            return 0

        logger.info("✅ All configuration loaded - starting worker...")

        if not self.connect_mqtt():
            logger.error("Cannot start without MQTT connection")
            return 1

        # Initialize config hash for hot-reload detection
        self._config_hash = self._get_config_hash()
        self._last_config_check = time.time()

        # Connect to TimescaleDB (optional - graceful degradation)
        self.connect_timescaledb()

        # Initialize BACnet (after event loop is running)
        if not self.initialize_bacnet():
            logger.error("Cannot start without BACnet stack")
            return 1

        logger.info("🚀 BacPipes MQTT Publisher started successfully")
        logger.info("Polling points based on individual intervals (Ctrl+C to stop)")

        # Main loop - check every 5 seconds for points that need polling
        while not shutdown_requested:
            try:
                # Check for discovery lock file (coordination with discovery.py)
                if os.path.exists(DISCOVERY_LOCK_FILE):
                    # Discovery is running - shutdown BACnet app to release port
                    if self.bacnet_app:
                        logger.info("🔒 Discovery lock detected - shutting down BACnet application...")
                        try:
                            start_close = time.time()
                            self.bacnet_app.close()
                            close_duration = time.time() - start_close
                            logger.info(f"✅ BACnet app closed in {close_duration:.3f}s - port 47808 released for discovery")
                        except Exception as e:
                            logger.warning(f"   Error closing BACnet app: {e}")
                        self.bacnet_app = None

                    # Wait for discovery to complete (check again in 1 second)
                    await asyncio.sleep(1)
                    continue  # Skip polling while discovery is active

                # If BACnet app was shutdown and lock is gone, reinitialize it
                if not self.bacnet_app:
                    logger.info("🔄 Discovery complete - reinitializing BACnet application...")
                    if not self.initialize_bacnet():
                        logger.error("❌ Failed to reinitialize BACnet application")
                        await asyncio.sleep(5)
                        continue
                    logger.info("✅ BACnet application restarted - resuming normal polling")

                # Try to reconnect to MQTT if disconnected
                if not self.mqtt_connected:
                    self.reconnect_mqtt()

                # Check for MQTT config changes every 10 seconds (hot-reload)
                if time.time() - self._last_config_check >= 10:
                    self._check_config_changes()
                    self._last_config_check = time.time()

                # Process any pending write commands from MQTT (queue-based approach)
                await self.process_write_commands()

                # Poll enabled points
                await self.poll_and_publish()
            except Exception as e:
                logger.error(f"Error in poll cycle: {e}", exc_info=True)

            # Check again in 1 second (faster lock detection for discovery coordination)
            await asyncio.sleep(1)

        # Cleanup
        logger.info("Shutting down gracefully...")

        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("Disconnected from MQTT broker")

        if self.timescaledb_conn:
            self.timescaledb_conn.close()
            logger.info("Disconnected from TimescaleDB")

        if self.db_conn:
            self.db_conn.close()
            logger.info("Disconnected from PostgreSQL database")

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

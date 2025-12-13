#!/usr/bin/env python3
"""
MQTT to TimescaleDB Bridge
Subscribes to MQTT topics and writes sensor data to TimescaleDB
"""

import os
import json
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import execute_values

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration from environment - TimescaleDB
TIMESCALEDB_HOST = os.getenv('TIMESCALEDB_HOST', 'timescaledb')
TIMESCALEDB_PORT = int(os.getenv('TIMESCALEDB_PORT', '5432'))
TIMESCALEDB_NAME = os.getenv('TIMESCALEDB_DB', 'timescaledb')
TIMESCALEDB_USER = os.getenv('TIMESCALEDB_USER', 'anatoli')

# Configuration from environment - BacPipes config database
# Note: Using service name 'postgres' with bridge networking for LXC compatibility
CONFIG_DB_HOST = os.getenv('CONFIG_DB_HOST', 'postgres')
CONFIG_DB_PORT = int(os.getenv('CONFIG_DB_PORT', '5432'))
CONFIG_DB_NAME = os.getenv('CONFIG_DB_NAME', 'bacpipes')
CONFIG_DB_USER = os.getenv('CONFIG_DB_USER', 'anatoli')

# MQTT Configuration (from environment variables, with database override)
mqtt_config = {
    'broker': os.getenv('MQTT_BROKER', '10.0.60.3'),  # Read from env, fallback to default broker
    'port': int(os.getenv('MQTT_PORT', '1883')),
    'client_id': os.getenv('MQTT_CLIENT_ID_TELEGRAF', 'bacpipes_telegraf')  # Unique per deployment
}

# Database connections
db_conn = None  # TimescaleDB connection
config_conn = None  # BacPipes config database connection

# Statistics
stats = {
    'messages_received': 0,
    'messages_written': 0,
    'errors': 0
}

# Deduplication cache: {(haystack_name, timestamp): True}
# Prevents duplicate writes when Telegraf reconnects frequently
seen_messages = {}

def connect_config_db():
    """Connect to BacPipes configuration database"""
    global config_conn
    try:
        config_conn = psycopg2.connect(
            host=CONFIG_DB_HOST,
            port=CONFIG_DB_PORT,
            database=CONFIG_DB_NAME,
            user=CONFIG_DB_USER,
            connect_timeout=10
        )
        logger.info(f"✅ Connected to config database at {CONFIG_DB_HOST}:{CONFIG_DB_PORT}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to config database: {e}")
        return False

def load_mqtt_config():
    """Load MQTT configuration from database"""
    global mqtt_config, config_conn
    try:
        cursor = config_conn.cursor()
        cursor.execute('SELECT broker, port, "clientId" FROM "MqttConfig" WHERE enabled = true LIMIT 1')
        result = cursor.fetchone()
        cursor.close()

        if result:
            mqtt_config['broker'] = result[0]
            mqtt_config['port'] = result[1]
            # Note: client_id is NOT loaded from database to avoid conflicts with worker
            logger.info(f"✅ Loaded MQTT config from database: {mqtt_config['broker']}:{mqtt_config['port']}")
            logger.info(f"   Using unique client ID: {mqtt_config['client_id']}")
        else:
            logger.warning("⚠️  No MQTT config found in database, using defaults")
    except Exception as e:
        logger.error(f"❌ Failed to load MQTT config from database: {e}")
        logger.info("Using default MQTT configuration")

def connect_db():
    """Connect to TimescaleDB"""
    global db_conn
    try:
        db_conn = psycopg2.connect(
            host=TIMESCALEDB_HOST,
            port=TIMESCALEDB_PORT,
            database=TIMESCALEDB_NAME,
            user=TIMESCALEDB_USER,
            connect_timeout=10
        )
        db_conn.autocommit = True
        logger.info(f"✅ Connected to TimescaleDB at {TIMESCALEDB_HOST}:{TIMESCALEDB_PORT}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to TimescaleDB: {e}")
        return False

def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when connected to MQTT broker (API v2)"""
    if reason_code == 0:
        logger.info(f"✅ Connected to MQTT broker {mqtt_config['broker']}:{mqtt_config['port']}")
        # Subscribe to all point data topics
        client.subscribe("+/+/+/presentValue")
        client.subscribe("+/+/+/+/presentValue")
        logger.info("📡 Subscribed to: +/+/+/presentValue and +/+/+/+/presentValue")
    else:
        logger.error(f"❌ Failed to connect to MQTT broker, code: {reason_code}")

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    """Callback when disconnected from MQTT broker (API v2.1)"""
    if reason_code != 0:
        logger.warning(f"⚠️  Unexpected disconnect from MQTT broker, code: {reason_code}")

def on_message(client, userdata, msg):
    """Callback when MQTT message received (API v2)"""
    global stats, seen_messages

    try:
        stats['messages_received'] += 1

        # Parse JSON payload
        payload = json.loads(msg.payload.decode('utf-8'))

        # Extract data from payload
        timestamp = payload.get('timestamp')
        if timestamp:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = datetime.utcnow()

        # Deduplication check - use timestamp truncated to second
        # This prevents duplicate writes when Telegraf reconnects frequently
        haystack_name = payload.get('haystackName')
        timestamp_second = timestamp[:19] if timestamp and len(timestamp) >= 19 else timestamp  # Truncate to second precision
        dedup_key = (haystack_name, timestamp_second)
        if dedup_key in seen_messages:
            # Already processed this message (within same second), skip
            logger.debug(f"Skipping duplicate: {haystack_name} @ {timestamp_second}")
            return

        # Mark as seen (limit cache size to last 1000 messages)
        seen_messages[dedup_key] = True
        if len(seen_messages) > 1000:
            # Remove oldest entries (simple FIFO)
            for _ in range(100):
                seen_messages.pop(next(iter(seen_messages)), None)

        # Prepare data for insertion
        data = {
            'time': dt,
            'site_id': payload.get('siteId'),
            'equipment_type': payload.get('equipmentType'),
            'equipment_id': payload.get('equipmentId'),
            'device_id': payload.get('deviceId'),
            'device_name': payload.get('deviceName'),
            'device_ip': payload.get('deviceIp'),
            'object_type': payload.get('objectType'),
            'object_instance': payload.get('objectInstance'),
            'point_id': payload.get('pointId'),
            'point_name': payload.get('pointName'),
            'haystack_name': payload.get('haystackName'),
            'dis': payload.get('dis'),
            'value': payload.get('value'),
            'units': payload.get('units'),
            'quality': payload.get('quality', 'good'),
            'poll_duration': payload.get('pollDuration'),
            'poll_cycle': payload.get('pollCycle')
        }

        # Debug: Log first few messages to verify "dis" extraction
        if stats['messages_written'] < 3:
            logger.info(f"DEBUG: dis value = '{data.get('dis')}' for haystack = {data.get('haystack_name')}")

        # Insert into TimescaleDB
        insert_sensor_reading(data)
        stats['messages_written'] += 1

        # Log progress every 10 messages
        if stats['messages_received'] % 10 == 0:
            logger.info(f"📊 Stats: {stats['messages_received']} received, {stats['messages_written']} written, {stats['errors']} errors")

    except json.JSONDecodeError as e:
        stats['errors'] += 1
        logger.error(f"❌ Invalid JSON in message: {e}")
    except Exception as e:
        stats['errors'] += 1
        logger.error(f"❌ Error processing message: {e}")

def insert_sensor_reading(data):
    """Insert sensor reading into TimescaleDB"""
    global db_conn

    try:
        cursor = db_conn.cursor()

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

    except Exception as e:
        logger.error(f"❌ Database insert error: {e}")
        # Try to reconnect database (but don't crash the MQTT loop)
        connect_db()
        # Don't raise - continue processing other messages

def main():
    """Main function"""
    import os
    logger.info(f"🚀 Starting MQTT to TimescaleDB bridge... (PID: {os.getpid()})")

    # Connect to config database and load MQTT configuration
    if connect_config_db():
        load_mqtt_config()
    else:
        logger.warning("⚠️  Could not load MQTT config from database, using defaults")

    # Connect to TimescaleDB
    if not connect_db():
        logger.error("❌ Cannot start without TimescaleDB connection")
        return

    # Create MQTT client (using callback API v2)
    # clean_session=True ensures no duplicate subscriptions on reconnect
    client = mqtt.Client(
        client_id=mqtt_config['client_id'],
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        clean_session=True  # Clear session state on connect
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Disable automatic reconnect to prevent rapid reconnection loop
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    # Connect to MQTT broker (with retry)
    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            logger.info(f"📡 Connecting to MQTT broker {mqtt_config['broker']}:{mqtt_config['port']} (attempt {attempt + 1}/{max_retries})...")
            client.connect(mqtt_config['broker'], mqtt_config['port'], keepalive=60)
            break  # Success!
        except Exception as e:
            logger.error(f"❌ Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                logger.error(f"❌ Failed to connect after {max_retries} attempts")
                return

    # Start MQTT loop
    logger.info("✅ MQTT to TimescaleDB bridge running!")
    client.loop_forever()

if __name__ == "__main__":
    main()

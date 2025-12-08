# BacPipes Architecture Enhancement: Bidirectional MQTT Bridge with Direct TimescaleDB Writes

## Executive Summary

This document specifies the architectural improvements to BacPipes for a bidirectional MQTT bridge deployment with:
- Local edge processing (30-day retention)
- Remote central server (unlimited retention, ML training)
- Direct TimescaleDB writes (no data loss)
- Setpoint write-back capability (ML → BACnet)

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ LOCAL SITE (Docker Compose - 192.168.1.32)                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ BACnet Worker (Python)                                       │    │
│  │                                                              │    │
│  │  1. Poll BACnet devices every 30-60s                        │    │
│  │  2. Write to 3 destinations simultaneously:                 │    │
│  │     ├─> PostgreSQL (Point.lastValue, lastPollTime)          │    │
│  │     ├─> Local TimescaleDB (historical, 30 days)             │    │
│  │     └─> MQTT Broker A (for bridge to remote)               │    │
│  │                                                              │    │
│  │  3. Subscribe to: bacnet/write/command                       │    │
│  │  4. Validate write commands:                                 │    │
│  │     ├─> "sp" in position 4 of haystack name                  │    │
│  │     ├─> Point.isWritable = true                              │    │
│  │     └─> Value within min/max range                           │    │
│  │                                                              │    │
│  │  5. Execute BACnet write (priority 8)                        │    │
│  │  6. Publish result to: bacnet/write/result                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ PostgreSQL (Port 5434)                                       │    │
│  │  - Configuration database                                    │    │
│  │  - Point definitions, Haystack tags                          │    │
│  │  - Latest values (Point.lastValue)                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Local TimescaleDB (Port 5435)                                │    │
│  │  - 30-day retention (automatic cleanup)                      │    │
│  │  - Compression after 6 hours                                 │    │
│  │  - Operational queries, local dashboards                     │    │
│  │  - CSV export via GUI                                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Frontend (Next.js - Port 3001)                               │    │
│  │  - Dashboard, Points configuration                           │    │
│  │  - Monitoring page (SSE from MQTT)                           │    │
│  │  - NEW: CSV Export API endpoint                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
                               ↕
                    MQTT Broker A (External EMQX)
                    Bridge: WAN + TLS + Username/Password
                               ↕
┌──────────────────────────────────────────────────────────────────────┐
│ REMOTE SERVER (Central)                                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ MQTT Broker B (EMQX)                                         │    │
│  │  - Receives all site data from Broker A                      │    │
│  │  - Publishes write commands to Broker A                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Telegraf                                                      │    │
│  │  - Subscribes: +/+/+/presentValue                            │    │
│  │  - Writes to Remote TimescaleDB                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Remote TimescaleDB                                            │    │
│  │  - Unlimited retention                                        │    │
│  │  - ML training dataset                                        │    │
│  │  - Energy reporting                                           │    │
│  │  - Cross-site analytics                                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ ML Server                                                     │    │
│  │  1. Read historical data from Remote TimescaleDB             │    │
│  │  2. Train optimization models                                 │    │
│  │  3. Preliminary validation:                                   │    │
│  │     ├─> Check "sp" in position 4                              │    │
│  │     └─> Verify point exists in remote database                │    │
│  │  4. Publish to: bacnet/write/command                          │    │
│  │  5. Subscribe to: bacnet/write/result (track success)         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## MQTT Topic Structure (CRITICAL - NO AMBIGUITY)

### Uplink Topics (Local → Remote) - Point-Specific

**Format:** `{site}/{equipmentType}_{equipmentId}/{objectType}{objectInstance}/presentValue`

**Generation Rules:**
1. `site` = `siteId` field (lowercase, spaces → underscores)
2. `equipment` = `equipmentType` + `_` + `equipmentId` (lowercase, spaces → underscores)
3. `object` = `objectType` (remove hyphens) + `objectInstance` (number)
4. Suffix = `/presentValue` (fixed)

**Examples:**

```
Haystack: duxton.ahu.1.sensor.temp.air.supply.actual
BACnet:   Device 12345, analog-input 101
Topic:    duxton/ahu_1/analoginput101/presentValue

Haystack: duxton.ahu.1.sp.humidity.air.return.effective
BACnet:   Device 12345, analog-value 120
Topic:    duxton/ahu_1/analogvalue120/presentValue

Haystack: klcc.chiller.2.sensor.power.elec.total.actual
BACnet:   Device 67890, analog-input 501
Topic:    klcc/chiller_2/analoginput501/presentValue
```

**Payload Structure:**
```json
{
  "value": 21.5,
  "timestamp": "2025-12-08T14:30:00.000Z",
  "units": "°C",
  "quality": "good",
  "dis": "SupplyAirTemp",
  "haystackName": "duxton.ahu.1.sensor.temp.air.supply.actual",
  "deviceIp": "192.168.1.37",
  "deviceId": 12345,
  "objectType": "analog-input",
  "objectInstance": 101
}
```

**Broker A Bridge Configuration (Uplink):**
```
# Forward all site data to Broker B
topic duxton/# out 1
topic klcc/# out 1
topic site3/# out 1
```

**Remote Telegraf Subscription:**
```
# Subscribe to all presentValue topics
+/+/+/presentValue
+/+/+/+/presentValue  # For 4-level topics
```

---

### Downlink Topics (Remote → Local) - Command Channel

**Command Topic (Fixed):** `bacnet/write/command`

**Payload Structure:**
```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "deviceId": 12345,
  "objectType": "analog-value",
  "objectInstance": 120,
  "value": 65.0,
  "priority": 8,
  "release": false,
  "timestamp": "2025-12-08T14:30:00.000Z",
  "source": "ml-optimizer",
  "reason": "energy-optimization",
  "siteId": "duxton",
  "equipmentType": "ahu",
  "equipmentId": "1",
  "haystackName": "duxton.ahu.1.sp.humidity.air.return.effective"
}
```

**Field Descriptions:**
- `jobId`: UUID for tracking (generated by ML server)
- `deviceId`: BACnet device ID (REQUIRED)
- `objectType`: BACnet object type (REQUIRED) - e.g., "analog-value", "binary-output"
- `objectInstance`: BACnet object instance number (REQUIRED)
- `value`: Value to write (REQUIRED) - float, int, or boolean
- `priority`: BACnet priority level (1-16, default 8)
- `release`: If true, release priority (revert to lower priority/default)
- `timestamp`: When command was generated
- `source`: Who generated command (e.g., "ml-optimizer", "manual-override")
- `reason`: Why command was generated (for audit trail)
- `siteId`, `equipmentType`, `equipmentId`: For validation/logging
- `haystackName`: Full haystack name (for validation)

**Result Topic (Fixed):** `bacnet/write/result`

**Payload Structure:**
```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "deviceId": 12345,
  "objectType": "analog-value",
  "objectInstance": 120,
  "value": 65.0,
  "priority": 8,
  "timestamp": "2025-12-08T14:30:05.123Z",
  "processingTime": 0.123,
  "error": null,
  "validationErrors": []
}
```

**Error Response Example:**
```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "success": false,
  "deviceId": 12345,
  "objectType": "analog-value",
  "objectInstance": 120,
  "value": 65.0,
  "priority": 8,
  "timestamp": "2025-12-08T14:30:05.123Z",
  "processingTime": 0.045,
  "error": "Validation failed",
  "validationErrors": [
    "Point is not a setpoint (no 'sp' in position 4)",
    "Point.isWritable = false in database"
  ]
}
```

**Broker A Bridge Configuration (Downlink):**
```
# Receive write commands from Broker B
topic bacnet/write/# in 1
```

---

## Data Flow Examples

### Example 1: Sensor Reading (Uplink Only)

**Scenario:** Temperature sensor on AHU-1 is polled

```
Step 1: Worker polls BACnet device
  Device: 12345
  Object: analog-input 101
  Value: 21.5°C

Step 2: Worker writes to PostgreSQL
  UPDATE Point SET lastValue='21.5', lastPollTime=NOW() WHERE id=123

Step 3: Worker writes to Local TimescaleDB
  INSERT INTO sensor_readings (time, device_id, object_type, object_instance,
    value, units, haystack_name, dis, ...)
  VALUES (NOW(), 12345, 'analog-input', 101, 21.5, '°C',
    'duxton.ahu.1.sensor.temp.air.supply.actual', 'SupplyAirTemp', ...)

Step 4: Worker publishes to MQTT Broker A
  Topic: duxton/ahu_1/analoginput101/presentValue
  Payload: {"value": 21.5, "timestamp": "...", ...}

Step 5: Bridge forwards to Broker B
  Topic: duxton/ahu_1/analoginput101/presentValue
  (Same payload)

Step 6: Telegraf subscribes from Broker B
  Receives message, inserts to Remote TimescaleDB

Result:
  ✅ Local TimescaleDB has reading (immediate)
  ✅ Remote TimescaleDB has reading (1-2 seconds later)
  ✅ ML can query historical data from Remote TimescaleDB
```

---

### Example 2: Setpoint Reading (Uplink Only)

**Scenario:** Humidity setpoint current value is polled

```
Step 1: Worker polls BACnet device
  Device: 12345
  Object: analog-value 120
  Value: 60.0%

Step 2: Worker writes to PostgreSQL
  UPDATE Point SET lastValue='60.0', lastPollTime=NOW() WHERE id=456

Step 3: Worker writes to Local TimescaleDB
  INSERT INTO sensor_readings (...)
  VALUES (..., 'duxton.ahu.1.sp.humidity.air.return.effective', ...)

Step 4: Worker publishes to MQTT Broker A
  Topic: duxton/ahu_1/analogvalue120/presentValue
  Payload: {"value": 60.0, "haystackName": "duxton.ahu.1.sp.humidity.air.return.effective", ...}

Step 5: Bridge forwards to Broker B → Remote TimescaleDB

Note: This is a READ of the current setpoint value, not a WRITE command
```

---

### Example 3: ML Writes Setpoint (Bidirectional)

**Scenario:** ML optimizes humidity setpoint from 60% to 65%

```
Step 1: ML queries Remote TimescaleDB
  SELECT * FROM sensor_readings
  WHERE haystack_name = 'duxton.ahu.1.sp.humidity.air.return.effective'
  AND time > NOW() - INTERVAL '30 days'

  Analyzes historical data...

Step 2: ML preliminary validation
  ✅ Haystack name: "duxton.ahu.1.sp.humidity.air.return.effective"
  ✅ Position 4 = "sp" (is a setpoint)
  ✅ Point exists in remote database copy

Step 3: ML publishes write command to Broker B
  Topic: bacnet/write/command
  Payload: {
    "jobId": "abc-123",
    "deviceId": 12345,
    "objectType": "analog-value",
    "objectInstance": 120,
    "value": 65.0,
    "priority": 8,
    "haystackName": "duxton.ahu.1.sp.humidity.air.return.effective",
    "source": "ml-optimizer",
    "reason": "energy-optimization"
  }

Step 4: Bridge forwards to Broker A
  (Same topic, same payload)

Step 5: Worker receives from Broker A
  Subscription: bacnet/write/command

Step 6: Worker authoritative validation
  ✅ Load point from PostgreSQL by deviceId + objectType + objectInstance
  ✅ Check haystack name: "duxton.ahu.1.sp.humidity.air.return.effective"
  ✅ Split by '.': ['duxton', 'ahu', '1', 'sp', 'humidity', 'air', 'return', 'effective']
  ✅ Position 4 (index 3) = "sp" ✓
  ✅ Point.isWritable = true ✓
  ✅ Value 65.0 within Point.minPresValue (0) and maxPresValue (100) ✓
  ✅ Priority 8 is valid (1-16) ✓

Step 7: Worker executes BACnet write
  Write to Device 12345, analog-value 120, priority 8, value 65.0
  Result: Success

Step 8: Worker publishes result to Broker A
  Topic: bacnet/write/result
  Payload: {
    "jobId": "abc-123",
    "success": true,
    "deviceId": 12345,
    "objectType": "analog-value",
    "objectInstance": 120,
    "value": 65.0,
    "timestamp": "2025-12-08T14:30:05.123Z",
    "processingTime": 0.123,
    "error": null,
    "validationErrors": []
  }

Step 9: Bridge forwards result to Broker B

Step 10: ML subscribes to bacnet/write/result
  Receives confirmation, logs success

Step 11: Next poll cycle (30-60 seconds later)
  Worker polls BACnet → reads new value 65.0%
  Publishes to: duxton/ahu_1/analogvalue120/presentValue
  Payload: {"value": 65.0, ...}

  → Bridge forwards to Broker B
  → Telegraf writes to Remote TimescaleDB
  → ML sees updated value in next query

Result:
  ✅ Setpoint changed from 60% → 65%
  ✅ ML received confirmation
  ✅ Updated value flows back through system
  ✅ Both local and remote TimescaleDB updated
```

---

### Example 4: ML Tries to Write Sensor (Validation Fails)

**Scenario:** ML mistakenly tries to write to a sensor (read-only)

```
Step 1: ML publishes write command to Broker B
  Topic: bacnet/write/command
  Payload: {
    "jobId": "xyz-789",
    "deviceId": 12345,
    "objectType": "analog-input",
    "objectInstance": 101,
    "value": 25.0,
    "haystackName": "duxton.ahu.1.sensor.temp.air.supply.actual"
  }

Step 2: Bridge forwards to Broker A

Step 3: Worker receives, validates
  ❌ Load point from PostgreSQL
  ❌ Haystack: "duxton.ahu.1.sensor.temp.air.supply.actual"
  ❌ Split: ['duxton', 'ahu', '1', 'sensor', 'temp', 'air', 'supply', 'actual']
  ❌ Position 4 (index 3) = "sensor" (NOT "sp") → REJECT

Step 4: Worker publishes error result
  Topic: bacnet/write/result
  Payload: {
    "jobId": "xyz-789",
    "success": false,
    "deviceId": 12345,
    "objectType": "analog-input",
    "objectInstance": 101,
    "value": 25.0,
    "timestamp": "2025-12-08T14:30:05.045Z",
    "processingTime": 0.012,
    "error": "Validation failed",
    "validationErrors": [
      "Point is not a setpoint (position 4 is 'sensor', not 'sp')",
      "Only setpoints with 'sp' in position 4 can be written"
    ]
  }

Step 5: ML receives error, logs failure

Result:
  ✅ Sensor NOT written (protected)
  ✅ Clear error message for debugging
  ✅ System integrity maintained
```

---

## Worker Implementation Details

### New Code Additions

**File:** `worker/mqtt_publisher.py`

#### 1. Add TimescaleDB Connection (After line 76)

```python
# TimescaleDB connection for direct writes
self.timescaledb_host = os.getenv('TIMESCALEDB_HOST', 'localhost')
self.timescaledb_port = int(os.getenv('TIMESCALEDB_PORT', '5435'))
self.timescaledb_name = os.getenv('TIMESCALEDB_DB', 'timescaledb')
self.timescaledb_user = os.getenv('TIMESCALEDB_USER', 'anatoli')
self.timescaledb_password = os.getenv('TIMESCALEDB_PASSWORD', '')
self.timescaledb_conn = None
```

#### 2. Add TimescaleDB Connect Method

```python
def connect_timescaledb(self):
    """Connect to TimescaleDB for direct writes"""
    try:
        self.timescaledb_conn = psycopg2.connect(
            host=self.timescaledb_host,
            port=self.timescaledb_port,
            database=self.timescaledb_name,
            user=self.timescaledb_user,
            password=self.timescaledb_password,
            cursor_factory=RealDictCursor
        )
        self.timescaledb_conn.autocommit = True
        logger.info(f"✅ Connected to TimescaleDB: {self.timescaledb_host}:{self.timescaledb_port}")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Failed to connect to TimescaleDB: {e}")
        logger.warning(f"⚠️  Worker will continue without local historical storage")
        self.timescaledb_conn = None
        return False
```

#### 3. Add Direct Write to TimescaleDB (After line 949)

```python
# Write to local TimescaleDB if connected
if self.timescaledb_conn:
    try:
        cursor = self.timescaledb_conn.cursor()
        cursor.execute("""
            INSERT INTO sensor_readings (
                time, site_id, equipment_type, equipment_id,
                device_id, device_name, device_ip,
                object_type, object_instance,
                point_id, point_name, haystack_name, dis,
                value, units, quality,
                poll_duration, poll_cycle
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
        """, (
            timestamp,
            point.get('siteId'),
            point.get('equipmentType'),
            point.get('equipmentId'),
            point['deviceId'],
            point['deviceName'],
            point['ipAddress'],
            point['objectType'],
            point['objectInstance'],
            point['id'],
            point['pointName'],
            point['haystackPointName'],
            point['dis'],
            float(value) if isinstance(value, (int, float)) else value,
            point['units'],
            'good',
            None,  # poll_duration (optional)
            self.poll_cycle
        ))
        cursor.close()
        logger.debug(f"✅ Wrote to local TimescaleDB: {point['haystackPointName']}")
    except Exception as e:
        logger.debug(f"Failed to write to TimescaleDB: {e}")
```

#### 4. Subscribe to Write Commands (In startup sequence)

```python
def setup_write_command_subscription(self):
    """Subscribe to write commands from MQTT broker"""
    if not self.mqtt_connected:
        return

    try:
        # Subscribe to write command topic
        self.mqtt_client.subscribe("bacnet/write/command", qos=1)
        logger.info("📡 Subscribed to: bacnet/write/command")

        # Set message callback
        self.mqtt_client.on_message = self.on_write_command_received

    except Exception as e:
        logger.error(f"❌ Failed to subscribe to write commands: {e}")
```

#### 5. Write Command Handler

```python
def on_write_command_received(self, client, userdata, message):
    """Handle incoming write command from MQTT"""
    try:
        payload = json.loads(message.payload.decode('utf-8'))

        job_id = payload.get('jobId')
        device_id = payload.get('deviceId')
        object_type = payload.get('objectType')
        object_instance = payload.get('objectInstance')
        value = payload.get('value')
        priority = payload.get('priority', 8)
        release = payload.get('release', False)

        logger.info(f"📝 Write command received: jobId={job_id}, device={device_id}, "
                   f"object={object_type}:{object_instance}, value={value}, priority={priority}")

        # Validate and execute
        result = self.execute_write_command(
            job_id=job_id,
            device_id=device_id,
            object_type=object_type,
            object_instance=object_instance,
            value=value,
            priority=priority,
            release=release,
            payload=payload
        )

        # Publish result
        self.publish_write_result(result)

    except Exception as e:
        logger.error(f"❌ Error processing write command: {e}")
        # Publish error result if possible
        try:
            error_result = {
                "jobId": payload.get('jobId') if 'payload' in locals() else None,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.publish_write_result(error_result)
        except:
            pass
```

#### 6. Write Command Validation and Execution

```python
def execute_write_command(self, job_id, device_id, object_type, object_instance,
                          value, priority, release, payload):
    """Validate and execute BACnet write command"""

    start_time = time.time()
    validation_errors = []

    try:
        # Load point from database
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT p.*, d.ipAddress, d.deviceName
            FROM "Point" p
            JOIN "Device" d ON p."deviceId" = d.id
            WHERE d."deviceId" = %s
            AND p."objectType" = %s
            AND p."objectInstance" = %s
        """, (device_id, object_type, object_instance))

        point = cursor.fetchone()
        cursor.close()

        if not point:
            validation_errors.append(f"Point not found: device={device_id}, {object_type}:{object_instance}")
            return self._create_result(job_id, False, device_id, object_type, object_instance,
                                       value, priority, start_time, "Point not found", validation_errors)

        # CRITICAL: Validate "sp" in position 4 of haystack name
        haystack_name = point['haystackPointName']
        if haystack_name:
            parts = haystack_name.split('.')
            if len(parts) < 4 or parts[3] != 'sp':
                validation_errors.append(
                    f"Point is not a setpoint (position 4 is '{parts[3] if len(parts) > 3 else 'missing'}', not 'sp')"
                )
                validation_errors.append("Only setpoints with 'sp' in position 4 can be written")
        else:
            validation_errors.append("Point has no haystack name, cannot validate")

        # Validate isWritable flag
        if not point.get('isWritable', False):
            validation_errors.append(f"Point.isWritable = false in database")

        # Validate priority (1-16)
        if not (1 <= priority <= 16):
            validation_errors.append(f"Priority {priority} is invalid (must be 1-16)")

        # Validate value range (if not releasing)
        if not release:
            min_val = point.get('minPresValue')
            max_val = point.get('maxPresValue')
            if min_val is not None and max_val is not None:
                try:
                    num_value = float(value)
                    if not (float(min_val) <= num_value <= float(max_val)):
                        validation_errors.append(
                            f"Value {value} out of range [{min_val}, {max_val}]"
                        )
                except (ValueError, TypeError):
                    pass  # Non-numeric value, skip range check

        # If validation failed, return error
        if validation_errors:
            return self._create_result(job_id, False, device_id, object_type, object_instance,
                                       value, priority, start_time, "Validation failed", validation_errors)

        # Execute BACnet write
        success, error_msg = self._execute_bacnet_write(
            device_ip=point['ipAddress'],
            device_id=device_id,
            object_type=object_type,
            object_instance=object_instance,
            value=value,
            priority=priority,
            release=release
        )

        processing_time = time.time() - start_time

        return self._create_result(job_id, success, device_id, object_type, object_instance,
                                   value, priority, start_time, error_msg, validation_errors)

    except Exception as e:
        logger.error(f"❌ Error executing write command: {e}")
        return self._create_result(job_id, False, device_id, object_type, object_instance,
                                   value, priority, start_time, str(e), validation_errors)

def _create_result(self, job_id, success, device_id, object_type, object_instance,
                   value, priority, start_time, error, validation_errors):
    """Create write result object"""
    return {
        "jobId": job_id,
        "success": success,
        "deviceId": device_id,
        "objectType": object_type,
        "objectInstance": object_instance,
        "value": value,
        "priority": priority,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processingTime": round(time.time() - start_time, 3),
        "error": error,
        "validationErrors": validation_errors
    }

def _execute_bacnet_write(self, device_ip, device_id, object_type, object_instance,
                         value, priority, release):
    """Execute actual BACnet write operation"""
    try:
        # Use existing BACnet application instance
        address = Address(f"{device_ip}")
        obj_id = ObjectIdentifier(f"{object_type},{object_instance}")

        if release:
            # Release priority (write NULL)
            write_value = Null()
        else:
            # Write actual value (convert to appropriate BACnet type)
            write_value = value  # Simplified - actual implementation needs type conversion

        # Execute write (using BACpypes3 async write)
        result = asyncio.run(self.write_property(
            address=address,
            obj_id=obj_id,
            prop_id=PropertyIdentifier("presentValue"),
            value=write_value,
            priority=priority
        ))

        logger.info(f"✅ BACnet write successful: device={device_id}, {object_type}:{object_instance}, "
                   f"value={value}, priority={priority}")
        return True, None

    except Exception as e:
        logger.error(f"❌ BACnet write failed: {e}")
        return False, str(e)

def publish_write_result(self, result):
    """Publish write command result to MQTT"""
    try:
        if not self.mqtt_connected:
            logger.warning("⚠️  Cannot publish write result: MQTT not connected")
            return

        self.mqtt_client.publish(
            topic="bacnet/write/result",
            payload=json.dumps(result),
            qos=1,
            retain=False
        )

        logger.info(f"📤 Published write result: jobId={result['jobId']}, success={result['success']}")

    except Exception as e:
        logger.error(f"❌ Failed to publish write result: {e}")
```

---

## Configuration Changes

### Docker Compose (`docker-compose.yml`)

Add TimescaleDB environment variables to worker service:

```yaml
  bacnet-worker:
    # ... existing config ...
    environment:
      # ... existing vars ...

      # TimescaleDB connection for direct writes
      TIMESCALEDB_HOST: ${TIMESCALEDB_HOST:-localhost}
      TIMESCALEDB_PORT: ${TIMESCALEDB_PORT:-5435}
      TIMESCALEDB_DB: ${TIMESCALEDB_DB:-timescaledb}
      TIMESCALEDB_USER: ${TIMESCALEDB_USER:-anatoli}
      TIMESCALEDB_PASSWORD: ${TIMESCALEDB_PASSWORD:-}

    depends_on:
      postgres:
        condition: service_healthy
      timescaledb:
        condition: service_healthy  # Add dependency
      frontend:
        condition: service_started
```

### Environment Variables (`.env`)

```bash
# TimescaleDB (for direct writes from worker)
TIMESCALEDB_HOST=localhost
TIMESCALEDB_PORT=5435
TIMESCALEDB_DB=timescaledb
TIMESCALEDB_USER=anatoli
TIMESCALEDB_PASSWORD=

# MQTT Broker A (external)
MQTT_BROKER=10.0.60.3  # Your external EMQX broker
MQTT_PORT=1883
```

---

## Data Export Feature

### CSV Export API Endpoint

**File:** `frontend/src/app/api/timeseries/export/route.ts` (NEW)

```typescript
import { NextRequest, NextResponse } from 'next/server';
import postgres from 'postgres';

export const dynamic = 'force-dynamic';

// TimescaleDB connection
const timescaledb = postgres({
  host: process.env.TIMESCALEDB_HOST || 'localhost',
  port: parseInt(process.env.TIMESCALEDB_PORT || '5435'),
  database: process.env.TIMESCALEDB_DB || 'timescaledb',
  username: process.env.TIMESCALEDB_USER || 'anatoli',
  password: process.env.TIMESCALEDB_PASSWORD || '',
});

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Parse query parameters
    const start = searchParams.get('start') || new Date(Date.now() - 86400000).toISOString(); // Default: 24h ago
    const end = searchParams.get('end') || new Date().toISOString();
    const haystackName = searchParams.get('haystackName'); // Optional filter
    const format = searchParams.get('format') || 'csv'; // csv or json

    // Build query
    let query = `
      SELECT
        time,
        haystack_name,
        dis,
        value,
        units,
        quality,
        device_name,
        device_ip,
        object_type,
        object_instance
      FROM sensor_readings
      WHERE time >= $1 AND time <= $2
    `;

    const params = [start, end];

    if (haystackName) {
      query += ` AND haystack_name = $3`;
      params.push(haystackName);
    }

    query += ` ORDER BY time DESC`;

    // Execute query
    const results = await timescaledb.unsafe(query, params);

    if (format === 'json') {
      // Return JSON
      return NextResponse.json(results);
    } else {
      // Return CSV
      const csv = convertToCSV(results);
      return new NextResponse(csv, {
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': `attachment; filename="export_${Date.now()}.csv"`,
        },
      });
    }

  } catch (error) {
    console.error('Export error:', error);
    return NextResponse.json(
      { error: 'Export failed', details: error.message },
      { status: 500 }
    );
  }
}

function convertToCSV(data: any[]): string {
  if (data.length === 0) return '';

  // Get headers
  const headers = Object.keys(data[0]);
  const csvHeaders = headers.join(',');

  // Convert rows
  const csvRows = data.map(row =>
    headers.map(header => {
      const value = row[header];
      // Escape quotes and wrap in quotes if contains comma
      if (value === null || value === undefined) return '';
      const str = String(value);
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    }).join(',')
  );

  return [csvHeaders, ...csvRows].join('\n');
}
```

### Frontend Export UI

Add export button to monitoring page or new exports page:

**Example usage:**
```
GET http://192.168.1.32:3001/api/timeseries/export?start=2025-12-01T00:00:00Z&end=2025-12-08T23:59:59Z&format=csv

Downloads CSV file with all data in range
```

---

## Testing Scenarios

### Test 1: Uplink Data Flow

1. Enable a point with "sp" in position 4
2. Wait for poll cycle (30-60s)
3. Verify:
   - ✅ PostgreSQL Point.lastValue updated
   - ✅ Local TimescaleDB has row in sensor_readings
   - ✅ MQTT message published to Broker A (check EMQX console)
   - ✅ Remote Broker B receives message (check remote EMQX console)
   - ✅ Remote TimescaleDB has row

### Test 2: Downlink Write Command (Valid Setpoint)

1. Publish to Broker B:
   ```
   Topic: bacnet/write/command
   Payload: {
     "jobId": "test-123",
     "deviceId": 12345,
     "objectType": "analog-value",
     "objectInstance": 120,
     "value": 70.0,
     "priority": 8,
     "haystackName": "duxton.ahu.1.sp.humidity.air.return.effective"
   }
   ```

2. Verify:
   - ✅ Worker receives command (check logs)
   - ✅ Validation passes (check logs)
   - ✅ BACnet write executed (check logs)
   - ✅ Result published to bacnet/write/result with success=true
   - ✅ Next poll cycle shows new value

### Test 3: Downlink Write Command (Invalid - Sensor)

1. Publish to Broker B:
   ```
   Topic: bacnet/write/command
   Payload: {
     "jobId": "test-456",
     "deviceId": 12345,
     "objectType": "analog-input",
     "objectInstance": 101,
     "value": 25.0,
     "haystackName": "duxton.ahu.1.sensor.temp.air.supply.actual"
   }
   ```

2. Verify:
   - ✅ Worker receives command
   - ❌ Validation fails (position 4 is "sensor", not "sp")
   - ✅ Result published with success=false and validationErrors
   - ✅ BACnet write NOT executed

### Test 4: CSV Export

1. Navigate to: `http://192.168.1.32:3001/api/timeseries/export?start=2025-12-07T00:00:00Z&end=2025-12-08T23:59:59Z`
2. Verify:
   - ✅ CSV file downloads
   - ✅ Contains expected rows
   - ✅ Headers match schema

---

## Validation Rules Summary

| Rule | Check | Reject If |
|------|-------|-----------|
| **Haystack Position 4** | Split haystack name by '.', check index 3 | != "sp" |
| **Database isWritable** | Point.isWritable flag | = false |
| **Priority Range** | Priority value | < 1 or > 16 |
| **Value Range** | Compare to min/maxPresValue | < min or > max |
| **Point Exists** | Query database by deviceId + objectType + objectInstance | Not found |

**Defense in Depth:**
- ML Server: Preliminary validation (prevents obvious errors)
- Worker: Authoritative validation (enforces security)

---

## Critical Files to Modify

1. **`worker/mqtt_publisher.py`**
   - Add TimescaleDB connection
   - Add direct write after PostgreSQL update
   - Add write command subscription
   - Add validation and execution logic

2. **`docker-compose.yml`**
   - Add TimescaleDB environment variables to worker
   - Add timescaledb dependency to worker

3. **`.env`**
   - Add TimescaleDB connection variables

4. **`frontend/src/app/api/timeseries/export/route.ts`** (NEW)
   - Create CSV export endpoint

5. **`worker/requirements.txt`**
   - Verify psycopg2-binary is present (already there)

---

## Non-Implementation Items (User Responsibility)

1. **MQTT Broker A Configuration**
   - Install/configure EMQX
   - Setup bridge to Broker B
   - Configure TLS certificates
   - Configure username/password auth

2. **MQTT Broker B Configuration**
   - Install/configure EMQX on remote server
   - Configure bridge from Broker A
   - Configure TLS/auth

3. **Remote Server Setup**
   - Install TimescaleDB
   - Configure Telegraf
   - Setup ML server

---

## Success Criteria

✅ Worker writes to PostgreSQL, local TimescaleDB, and MQTT simultaneously
✅ Local TimescaleDB has 30-day retention working
✅ MQTT topics follow documented structure
✅ Worker subscribes to bacnet/write/command
✅ Write command validation enforces "sp" rule
✅ Write results published to bacnet/write/result
✅ CSV export API endpoint works
✅ No data loss if MQTT bridge fails (local TimescaleDB has data)
✅ Monitoring page continues to work (subscribes from MQTT)

---

---

## Feature Removal: Equipment Batch Publishing & Remote Control

### Features to Remove

These two settings features are redundant in the new architecture and should be removed:

1. **Equipment Batch Publishing** - No longer needed (single point-specific topics are sufficient)
2. **Remote Control Toggle** - No longer needed (write commands validated by "sp" rule instead)

---

### 1. Remove Equipment Batch Publishing

**What it does:** Publishes both individual point topics AND aggregated batch topics per equipment

**Why remove:**
- ❌ Creates data redundancy (same reading sent twice)
- ❌ Complicates MQTT topic structure
- ❌ Not needed - ML can subscribe to individual topics
- ❌ Batch topics are not part of new architecture

**Current behavior:**
```
Individual: duxton/ahu_1/analoginput101/presentValue (kept)
Batch:      duxton/ahu_1/batch (removed)
            Payload: [point1, point2, point3, ...]
```

**New behavior:** Only individual point-specific topics published

#### Files to Modify:

**A. Settings Page UI** (`frontend/src/app/settings/page.tsx`)

**Find and remove:** Equipment Batch Publishing section (lines ~150-200)

```typescript
// REMOVE THIS SECTION:
<div className="space-y-2">
  <Label htmlFor="enableBatchPublishing">Enable Equipment Batch Publishing</Label>
  <div className="flex items-center space-x-2">
    <Switch
      id="enableBatchPublishing"
      checked={settings.enableBatchPublishing}
      onCheckedChange={(checked) =>
        setSettings({ ...settings, enableBatchPublishing: checked })
      }
    />
    <span className="text-sm text-muted-foreground">
      Publish aggregated equipment-level batch topics
    </span>
  </div>
  <p className="text-sm text-muted-foreground">
    When enabled, each equipment publishes both individual point topics
    AND one batch topic containing all points with synchronized timestamps.
  </p>
  <Alert>
    <AlertDescription>
      ⚠️ Note: Data Redundancy - With batch publishing enabled,
      the same sensor reading is sent twice...
    </AlertDescription>
  </Alert>
</div>
```

**B. Database Schema** (`frontend/prisma/schema.prisma`)

**Find and remove:** `enableBatchPublishing` field from MqttConfig model

```prisma
model MqttConfig {
  id                    String   @id @default(cuid())
  broker                String   @default("10.0.60.3")
  port                  Int      @default(1883)
  clientId              String   @default("bacpipes_worker")
  enabled               Boolean  @default(true)
  // REMOVE THIS LINE:
  enableBatchPublishing Boolean  @default(false)

  writeCommandTopic     String   @default("bacnet/write/command")
  writeResultTopic      String   @default("bacnet/write/result")
  createdAt             DateTime @default(now())
  updatedAt             DateTime @updatedAt
}
```

**After removing, run migration:**
```bash
cd frontend
npx prisma migrate dev --name remove_batch_publishing
```

**C. Worker Code** (`worker/mqtt_publisher.py`)

**Find and remove:** Batch publishing code (search for "batch")

Likely locations:
- Load `enableBatchPublishing` from database (remove)
- Batch topic generation logic (remove)
- Batch payload aggregation (remove)
- Batch publish method (remove)

**Example code to remove:**
```python
# REMOVE THIS METHOD:
def publish_batch_topic(self, equipment_points):
    """Publish aggregated batch topic for equipment"""
    # ... batch publishing logic ...
```

**Keep only:** Individual point publishing logic

---

### 2. Remove Remote Control Toggle

**What it does:** Allows/blocks remote write commands via MQTT based on settings

**Why remove:**
- ❌ Security is now enforced by "sp" position 4 validation (better)
- ❌ ML write commands are core feature, not optional
- ❌ Validation rules are more granular than on/off toggle
- ❌ User has control at point level (Point.isWritable flag)

**Old security model:**
```
if not remote_control_enabled:
    reject all remote writes
```

**New security model (better):**
```
if haystack position 4 != "sp":
    reject write (not a setpoint)
if not Point.isWritable:
    reject write (point not writable)
```

#### Files to Modify:

**A. Settings Page UI** (`frontend/src/app/settings/page.tsx`)

**Find and remove:** Remote Control section (lines ~250-300)

```typescript
// REMOVE THIS SECTION:
<div className="space-y-2">
  <Label htmlFor="allowRemoteControl">Allow Remote Platform Control</Label>
  <div className="flex items-center space-x-2">
    <Switch
      id="allowRemoteControl"
      checked={settings.allowRemoteControl}
      onCheckedChange={(checked) =>
        setSettings({ ...settings, allowRemoteControl: checked })
      }
    />
    <span className="text-sm text-muted-foreground">
      Allow remote platform to send write commands
    </span>
  </div>
  <Alert variant="destructive">
    <AlertDescription>
      ⚠️ Security Notice: Only enable this if you have a trusted remote platform...
    </AlertDescription>
  </Alert>
</div>
```

**B. Database Schema** (`frontend/prisma/schema.prisma`)

**Find and remove:** `allowRemoteControl` field from SystemSettings or MqttConfig

Search for:
```prisma
allowRemoteControl Boolean @default(false)
```

**Remove this line** from whichever model contains it.

**After removing, run migration:**
```bash
cd frontend
npx prisma migrate dev --name remove_remote_control_toggle
```

**C. Worker Code** (`worker/mqtt_publisher.py`)

**Find and remove:** Remote control validation check

**Search for:**
```python
# REMOVE LOGIC LIKE THIS:
if payload.get('source') == 'remote' and not self.allow_remote_control:
    reject("Remote control is disabled")
```

**Replace with:** New validation (from main implementation plan)
- Check "sp" in position 4
- Check Point.isWritable
- Check value range
- No blanket "remote control" toggle

**All write commands are now validated the same way**, regardless of source.

---

### Migration Strategy

#### Step 1: Database Schema Changes

```bash
cd frontend

# Generate migration to remove both fields
npx prisma migrate dev --name remove_redundant_settings

# This will:
# 1. Drop enableBatchPublishing column from MqttConfig
# 2. Drop allowRemoteControl column from SystemSettings/MqttConfig
# 3. Update Prisma client
```

#### Step 2: Frontend Changes

**Remove from Settings page:**
1. Remove Equipment Batch Publishing UI section
2. Remove Remote Control UI section
3. Remove related state variables
4. Remove from settings save/load logic

**Test:** Settings page loads without errors

#### Step 3: Worker Changes

**Remove batch publishing:**
1. Remove batch topic generation
2. Remove batch payload aggregation
3. Remove batch publish method
4. Keep only individual point publishing

**Remove remote control check:**
1. Remove allowRemoteControl config loading
2. Remove source-based validation
3. Keep only "sp" + isWritable validation (from main plan)

**Test:** Worker publishes individual topics correctly

#### Step 4: Verification

**Check 1: No database errors**
```bash
docker compose logs -f frontend
# Should not show any Prisma errors about missing fields
```

**Check 2: Settings page works**
- Navigate to http://192.168.1.32:3001/settings
- Should load without errors
- Save settings should work

**Check 3: Worker publishes correctly**
```bash
docker compose logs -f bacnet-worker
# Should show individual topic publishes only
# No batch topics
# No remote control warnings
```

**Check 4: MQTT topics correct**
```bash
# Subscribe to all topics
mosquitto_sub -h 10.0.60.3 -t "#" -v

# Should see:
duxton/ahu_1/analoginput101/presentValue  ✓
duxton/ahu_1/analogvalue120/presentValue  ✓

# Should NOT see:
duxton/ahu_1/batch  ✗ (removed)
```

---

### Code Location Summary

| Component | File | Action |
|-----------|------|--------|
| **Settings UI** | `frontend/src/app/settings/page.tsx` | Remove 2 UI sections |
| **Database Schema** | `frontend/prisma/schema.prisma` | Remove 2 fields |
| **Settings API** | `frontend/src/app/api/settings/route.ts` | May need cleanup |
| **Worker Config** | `worker/mqtt_publisher.py` | Remove batch + remote checks |
| **Seed Data** | `frontend/prisma/seed.ts` | Remove default values |

---

### Benefits of Removal

1. ✅ **Simpler architecture** - One topic per point (clear, unambiguous)
2. ✅ **No data redundancy** - Each reading published once
3. ✅ **Better security** - Validation by point type, not blanket toggle
4. ✅ **Less configuration** - Fewer settings to manage
5. ✅ **Easier to understand** - MQTT topic structure is straightforward
6. ✅ **Aligns with new architecture** - ML subscribes to individual topics

---

### Backward Compatibility

**Breaking changes:** None if properly removed

**Existing deployments:**
- Database migration will drop unused columns (safe)
- Worker will stop publishing batch topics (ML doesn't use them)
- Write commands will work the same (validated by "sp" rule)

**No rollback needed:** New architecture is cleaner and more secure

---

---

## MQTT Authentication & TLS Configuration

### Current Limitation

**Problem:** MQTT broker connection is currently **unauthenticated and unencrypted**

Current configuration (basic):
```yaml
broker: 10.0.60.3
port: 1883
clientId: bacpipes_worker
```

**Security risks:**
- ❌ No username/password authentication
- ❌ No TLS encryption (plain text MQTT)
- ❌ Vulnerable to man-in-the-middle attacks
- ❌ Exposed credentials on WAN connections

**Required for production:** MQTT bridge over WAN requires TLS + authentication

---

### Required Settings

Add to Settings page MQTT configuration section:

#### 1. Authentication Credentials

**Fields:**
- Username (text input)
- Password (password input, masked)

**Storage:** Database (MqttConfig table)

**Usage:**
```python
mqtt_client.username_pw_set(username, password)
```

#### 2. TLS/SSL Configuration

**Fields:**
- Enable TLS (toggle switch)
- TLS Port (default: 8883 for MQTTS)
- CA Certificate (file upload)
- Client Certificate (file upload, optional)
- Client Key (file upload, optional)

**Similar to EMQX GUI:**
```
┌─────────────────────────────────────────┐
│ TLS/SSL Settings                        │
├─────────────────────────────────────────┤
│ ☑ Enable TLS/SSL                        │
│                                         │
│ TLS Port: [8883]                        │
│                                         │
│ CA Certificate (Required):              │
│ ┌─────────────────────────────────┐    │
│ │ ca.crt                          │ 📤 │
│ └─────────────────────────────────┘    │
│ [Upload CA Certificate]                 │
│                                         │
│ Client Certificate (Optional):          │
│ ┌─────────────────────────────────┐    │
│ │ client.crt                      │ 📤 │
│ └─────────────────────────────────┘    │
│ [Upload Client Certificate]             │
│                                         │
│ Client Key (Optional):                  │
│ ┌─────────────────────────────────┐    │
│ │ client.key                      │ 📤 │
│ └─────────────────────────────────┘    │
│ [Upload Client Key]                     │
│                                         │
│ ⚠️  Note: Certificates are stored      │
│     securely in database. Client cert  │
│     and key are optional (for mutual   │
│     TLS authentication).                │
└─────────────────────────────────────────┘
```

---

### Database Schema Changes

**File:** `frontend/prisma/schema.prisma`

Add to `MqttConfig` model:

```prisma
model MqttConfig {
  id                    String   @id @default(cuid())
  broker                String   @default("10.0.60.3")
  port                  Int      @default(1883)
  clientId              String   @default("bacpipes_worker")
  enabled               Boolean  @default(true)

  // Authentication (NEW)
  username              String?  // MQTT username
  password              String?  // MQTT password (consider encryption)

  // TLS/SSL Configuration (NEW)
  tlsEnabled            Boolean  @default(false)
  tlsPort               Int      @default(8883)
  caCertificate         String?  @db.Text  // CA cert content (PEM format)
  clientCertificate     String?  @db.Text  // Client cert (optional, for mutual TLS)
  clientKey             String?  @db.Text  // Client key (optional, for mutual TLS)

  writeCommandTopic     String   @default("bacnet/write/command")
  writeResultTopic      String   @default("bacnet/write/result")
  createdAt             DateTime @default(now())
  updatedAt             DateTime @updatedAt
}
```

**Migration:**
```bash
cd frontend
npx prisma migrate dev --name add_mqtt_auth_tls
```

---

### Frontend Implementation

#### A. Settings Page UI (`frontend/src/app/settings/page.tsx`)

**Add after broker/port fields:**

```typescript
{/* Authentication Section */}
<div className="space-y-4 border-t pt-4 mt-4">
  <h3 className="text-lg font-semibold">Authentication</h3>

  <div className="space-y-2">
    <Label htmlFor="mqttUsername">Username</Label>
    <Input
      id="mqttUsername"
      type="text"
      value={settings.mqttUsername || ''}
      onChange={(e) => setSettings({ ...settings, mqttUsername: e.target.value })}
      placeholder="MQTT username (optional)"
    />
    <p className="text-sm text-muted-foreground">
      Leave empty for unauthenticated connection
    </p>
  </div>

  <div className="space-y-2">
    <Label htmlFor="mqttPassword">Password</Label>
    <Input
      id="mqttPassword"
      type="password"
      value={settings.mqttPassword || ''}
      onChange={(e) => setSettings({ ...settings, mqttPassword: e.target.value })}
      placeholder="MQTT password (optional)"
    />
  </div>
</div>

{/* TLS/SSL Section */}
<div className="space-y-4 border-t pt-4 mt-4">
  <div className="flex items-center justify-between">
    <h3 className="text-lg font-semibold">TLS/SSL Encryption</h3>
    <Switch
      checked={settings.tlsEnabled || false}
      onCheckedChange={(checked) =>
        setSettings({ ...settings, tlsEnabled: checked })
      }
    />
  </div>

  {settings.tlsEnabled && (
    <>
      <div className="space-y-2">
        <Label htmlFor="tlsPort">TLS Port</Label>
        <Input
          id="tlsPort"
          type="number"
          value={settings.tlsPort || 8883}
          onChange={(e) => setSettings({ ...settings, tlsPort: parseInt(e.target.value) })}
        />
        <p className="text-sm text-muted-foreground">
          Default: 8883 (MQTTS), 1883 (plain MQTT)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="caCertificate">CA Certificate (Required)</Label>
        <div className="flex items-center space-x-2">
          <Input
            type="file"
            accept=".crt,.pem,.cer"
            onChange={handleCaCertUpload}
          />
          {settings.caCertificate && (
            <Badge variant="outline">✓ Uploaded</Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          Upload the Certificate Authority certificate (ca.crt or ca.pem)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="clientCertificate">Client Certificate (Optional)</Label>
        <div className="flex items-center space-x-2">
          <Input
            type="file"
            accept=".crt,.pem,.cer"
            onChange={handleClientCertUpload}
          />
          {settings.clientCertificate && (
            <Badge variant="outline">✓ Uploaded</Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          For mutual TLS authentication (client.crt)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="clientKey">Client Private Key (Optional)</Label>
        <div className="flex items-center space-x-2">
          <Input
            type="file"
            accept=".key,.pem"
            onChange={handleClientKeyUpload}
          />
          {settings.clientKey && (
            <Badge variant="outline">✓ Uploaded</Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          Private key for client certificate (client.key)
        </p>
      </div>

      <Alert>
        <AlertDescription>
          🔒 <strong>Security Note:</strong> Certificates are stored securely in the database.
          For production deployments, consider using environment variables or a secrets manager.
        </AlertDescription>
      </Alert>
    </>
  )}
</div>
```

**Add file upload handlers:**

```typescript
const handleCaCertUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (event) => {
    const content = event.target?.result as string;
    setSettings({ ...settings, caCertificate: content });
  };
  reader.readAsText(file);
};

const handleClientCertUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (event) => {
    const content = event.target?.result as string;
    setSettings({ ...settings, clientCertificate: content });
  };
  reader.readAsText(file);
};

const handleClientKeyUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (event) => {
    const content = event.target?.result as string;
    setSettings({ ...settings, clientKey: content });
  };
  reader.readAsText(file);
};
```

---

#### B. Settings API (`frontend/src/app/api/settings/route.ts`)

**Update save logic to include new fields:**

```typescript
await prisma.mqttConfig.update({
  where: { id: mqttConfig.id },
  data: {
    broker: body.mqttBroker,
    port: body.mqttPort,
    username: body.mqttUsername || null,
    password: body.mqttPassword || null,  // TODO: Consider encryption
    tlsEnabled: body.tlsEnabled || false,
    tlsPort: body.tlsPort || 8883,
    caCertificate: body.caCertificate || null,
    clientCertificate: body.clientCertificate || null,
    clientKey: body.clientKey || null,
  },
});
```

---

### Worker Implementation

**File:** `worker/mqtt_publisher.py`

#### A. Load TLS Configuration from Database

**Add to `load_mqtt_config()` method:**

```python
def load_mqtt_config(self):
    """Load MQTT configuration from database"""
    try:
        cursor = self.db_conn.cursor()
        cursor.execute('''
            SELECT broker, port, "clientId", username, password,
                   "tlsEnabled", "tlsPort", "caCertificate",
                   "clientCertificate", "clientKey"
            FROM "MqttConfig"
            WHERE enabled = true
            LIMIT 1
        ''')
        result = cursor.fetchone()
        cursor.close()

        if result:
            self.mqtt_broker = result['broker']
            self.mqtt_port = result['tlsPort'] if result['tlsEnabled'] else result['port']
            self.mqtt_client_id = result['clientId']
            self.mqtt_username = result['username']
            self.mqtt_password = result['password']
            self.mqtt_tls_enabled = result['tlsEnabled']
            self.mqtt_ca_cert = result['caCertificate']
            self.mqtt_client_cert = result['clientCertificate']
            self.mqtt_client_key = result['clientKey']

            logger.info(f"✅ MQTT config loaded:")
            logger.info(f"   - Broker: {self.mqtt_broker}:{self.mqtt_port}")
            logger.info(f"   - TLS: {'Enabled' if self.mqtt_tls_enabled else 'Disabled'}")
            logger.info(f"   - Auth: {'Yes' if self.mqtt_username else 'No'}")
        else:
            logger.warning("⚠️  No MQTT config in database")
    except Exception as e:
        logger.error(f"❌ Failed to load MQTT config: {e}")
```

#### B. Configure MQTT Client with TLS

**Update `connect_mqtt()` method:**

```python
def connect_mqtt(self):
    """Connect to MQTT broker with TLS and authentication"""
    try:
        # Create client
        self.mqtt_client = mqtt.Client(client_id=self.mqtt_client_id)

        # Set authentication if configured
        if self.mqtt_username and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
            logger.info(f"🔐 MQTT authentication enabled (user: {self.mqtt_username})")

        # Set TLS if configured
        if self.mqtt_tls_enabled and self.mqtt_ca_cert:
            # Write certificates to temporary files
            import tempfile
            import os

            # Create temp directory for certs
            cert_dir = tempfile.mkdtemp()

            # Write CA certificate
            ca_cert_path = os.path.join(cert_dir, 'ca.crt')
            with open(ca_cert_path, 'w') as f:
                f.write(self.mqtt_ca_cert)

            # Write client cert and key if provided (mutual TLS)
            client_cert_path = None
            client_key_path = None

            if self.mqtt_client_cert and self.mqtt_client_key:
                client_cert_path = os.path.join(cert_dir, 'client.crt')
                with open(client_cert_path, 'w') as f:
                    f.write(self.mqtt_client_cert)

                client_key_path = os.path.join(cert_dir, 'client.key')
                with open(client_key_path, 'w') as f:
                    f.write(self.mqtt_client_key)

                logger.info("🔐 Mutual TLS enabled (client cert + key)")

            # Configure TLS
            self.mqtt_client.tls_set(
                ca_certs=ca_cert_path,
                certfile=client_cert_path,
                keyfile=client_key_path,
                tls_version=ssl.PROTOCOL_TLSv1_2
            )

            # Optional: Disable hostname verification (use with caution)
            # self.mqtt_client.tls_insecure_set(True)

            logger.info(f"🔒 TLS enabled (port {self.mqtt_port})")

        # Connect
        self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
        self.mqtt_client.loop_start()
        self.mqtt_connected = True

        logger.info(f"✅ Connected to MQTT broker: {self.mqtt_broker}:{self.mqtt_port}")
        return True

    except Exception as e:
        logger.error(f"❌ MQTT connection failed: {e}")
        self.mqtt_connected = False
        return False
```

**Add import at top:**
```python
import ssl
import tempfile
```

---

### Configuration Examples

#### 1. Unauthenticated, Unencrypted (Current - Not Recommended)

```
Broker: 10.0.60.3
Port: 1883
Username: (empty)
Password: (empty)
TLS Enabled: No
```

**Use case:** Local development, trusted network

---

#### 2. Authenticated, Unencrypted (Better)

```
Broker: 10.0.60.3
Port: 1883
Username: bacpipes_worker
Password: your_password_here
TLS Enabled: No
```

**Use case:** Trusted network with authentication

---

#### 3. Authenticated + TLS (Recommended for Production)

```
Broker: mqtt.example.com
Port: 8883
Username: bacpipes_worker
Password: your_password_here
TLS Enabled: Yes
CA Certificate: (upload ca.crt)
Client Certificate: (optional)
Client Key: (optional)
```

**Use case:** Production deployment over WAN

---

#### 4. Mutual TLS (Highest Security)

```
Broker: mqtt.example.com
Port: 8883
Username: bacpipes_worker
Password: your_password_here
TLS Enabled: Yes
CA Certificate: (upload ca.crt)
Client Certificate: (upload client.crt)
Client Key: (upload client.key)
```

**Use case:** Enterprise deployment with mutual authentication

---

### Security Considerations

#### 1. Password Storage

**Current approach:** Plain text in database

**Recommended improvements:**
```typescript
// Option A: Hash password before storing
import bcrypt from 'bcrypt';
const hashedPassword = await bcrypt.hash(password, 10);

// Option B: Use environment variables for sensitive data
MQTT_PASSWORD=your_password_here

// Option C: Use secrets manager (AWS Secrets Manager, HashiCorp Vault)
```

#### 2. Certificate Storage

**Current approach:** Store full PEM content in database

**Considerations:**
- ✅ Easy to manage via GUI
- ⚠️ Database becomes security-critical
- ⚠️ Backup database securely

**Alternative:** Store certificates as files, reference paths in database

```
/etc/bacpipes/certs/
  ├── ca.crt
  ├── client.crt
  └── client.key
```

#### 3. Certificate Validation

**Default:** Verify hostname matches certificate

**Disable only if using self-signed certs:**
```python
self.mqtt_client.tls_insecure_set(True)  # Use with caution!
```

---

### EMQX Broker Configuration

For the MQTT bridge to work with TLS, configure EMQX Broker A:

```
# emqx.conf

# Enable TLS listener
listeners.ssl.default {
  bind = "0.0.0.0:8883"
  max_connections = 1024000
  ssl_options {
    cacertfile = "/etc/emqx/certs/ca.crt"
    certfile = "/etc/emqx/certs/server.crt"
    keyfile = "/etc/emqx/certs/server.key"
    verify = verify_peer
  }
}

# Enable authentication
authentication {
  enable = true
  backend = built_in_database
}

# Add user via EMQX dashboard or CLI:
# emqx_ctl users add bacpipes_worker your_password_here
```

---

### Testing

#### 1. Test Unauthenticated Connection

```bash
# In Settings GUI:
- Broker: 10.0.60.3
- Port: 1883
- Username: (empty)
- Password: (empty)
- TLS: disabled

# Restart worker
docker compose restart bacnet-worker

# Check logs
docker compose logs -f bacnet-worker
# Should see: "✅ Connected to MQTT broker: 10.0.60.3:1883"
```

#### 2. Test Authenticated Connection

```bash
# In Settings GUI:
- Broker: 10.0.60.3
- Port: 1883
- Username: bacpipes_worker
- Password: test123
- TLS: disabled

# Add user to EMQX:
# emqx_ctl users add bacpipes_worker test123

# Restart worker
docker compose restart bacnet-worker

# Check logs
# Should see: "🔐 MQTT authentication enabled (user: bacpipes_worker)"
# Should see: "✅ Connected to MQTT broker: 10.0.60.3:1883"
```

#### 3. Test TLS Connection

```bash
# Generate test certificates:
openssl req -new -x509 -days 365 -extensions v3_ca \
  -keyout ca.key -out ca.crt -subj "/CN=Test CA"

openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=mqtt.local"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365

# In Settings GUI:
- Broker: mqtt.local
- Port: 8883
- Username: bacpipes_worker
- Password: test123
- TLS: enabled
- CA Certificate: (upload ca.crt)

# Restart worker
docker compose restart bacnet-worker

# Check logs
# Should see: "🔒 TLS enabled (port 8883)"
# Should see: "✅ Connected to MQTT broker: mqtt.local:8883"
```

---

### Migration Path

#### Phase 1: Add Fields (No Breaking Changes)

1. Add database fields (username, password, TLS fields)
2. Add UI controls
3. Deploy - existing connections still work (no auth/TLS)

#### Phase 2: Enable Authentication

1. Create EMQX user accounts
2. Update Settings GUI with credentials
3. Test connection
4. Restart worker

#### Phase 3: Enable TLS

1. Generate/obtain TLS certificates
2. Configure EMQX TLS listener
3. Upload certificates via Settings GUI
4. Update port to 8883
5. Restart worker

#### Phase 4: Enforce Security (Optional)

1. Disable plain MQTT (port 1883) on EMQX
2. Require authentication on all connections
3. Reject unauthenticated clients

---

### Files to Modify Summary

| Component | File | Changes |
|-----------|------|---------|
| **Database Schema** | `frontend/prisma/schema.prisma` | Add 8 new fields to MqttConfig |
| **Settings UI** | `frontend/src/app/settings/page.tsx` | Add auth + TLS sections |
| **Settings API** | `frontend/src/app/api/settings/route.ts` | Save new fields |
| **Worker Config** | `worker/mqtt_publisher.py` | Load TLS config from DB |
| **Worker MQTT** | `worker/mqtt_publisher.py` | Configure TLS + auth |
| **Worker Requirements** | `worker/requirements.txt` | Add `paho-mqtt` (already present) |

---

### Success Criteria

✅ Settings page has username/password fields
✅ Settings page has TLS toggle and certificate uploads
✅ Database stores credentials and certificates
✅ Worker loads TLS config from database
✅ Worker connects with authentication if configured
✅ Worker connects with TLS if enabled
✅ Connection works without auth/TLS (backward compatible)
✅ Certificates stored securely in database
✅ UI shows connection status (authenticated/encrypted)

---

## End of Specification

This document provides complete, unambiguous specifications for implementing the enhanced BacPipes architecture with:
- Bidirectional MQTT bridge
- Direct TimescaleDB writes
- Removal of redundant settings features
- **MQTT authentication and TLS/SSL encryption**

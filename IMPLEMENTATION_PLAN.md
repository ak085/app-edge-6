# BacPipes Next Phase: Enhanced Security and Data Export

## Status Update (2025-12-09)

### ✅ Completed Features

**Phase 1: Direct TimescaleDB Writes** - ✅ **COMPLETE**
- Worker now writes sensor readings directly to TimescaleDB
- Graceful degradation if TimescaleDB unavailable
- Triple-destination writes: PostgreSQL → TimescaleDB → MQTT
- Production tested and verified
- Implementation date: 2025-12-09

**Phase 2: Comprehensive Write Command Validation** - ✅ **COMPLETE**
- Implemented 5-check validation system for write commands
- Database schema updated with minPresValue and maxPresValue fields
- Worker validation logic with detailed error codes (POINT_NOT_FOUND, INVALID_POINT_FUNCTION, etc.)
- Enhanced UI with context-aware guidance and smart placeholders
- Professional UX with visual feedback and validation preview
- Production tested and verified
- Implementation date: 2025-12-09

**Key Security Features Implemented:**
- ✅ Point existence validation in database
- ✅ Haystack position-4 must be "sp" (prevents sensor writes)
- ✅ isWritable flag enforcement
- ✅ Priority range validation (1-16)
- ✅ Value range validation (min/max enforcement)
- ✅ Detailed validation error reporting via MQTT

---

## Remaining Implementation Tasks

### Phase 3: MQTT Authentication & TLS Support

**Status:** 🔴 Not Started
**Priority:** MEDIUM (Required for WAN deployments)

#### Current State
- Worker connects to MQTT without authentication
- No TLS encryption
- OK for local LAN deployments
- Not suitable for WAN/internet deployments

#### Required Changes

**1. Database Schema Updates** (`frontend/prisma/schema.prisma`)

Add to Point model:
```prisma
model Point {
  // ... existing fields ...

  // Validation fields for write commands
  isWritable       Boolean  @default(false)
  minPresValue     Float?
  maxPresValue     Float?
}
```

Run migration:
```bash
cd frontend
npx prisma migrate dev --name add_write_validation_fields
```

**2. Worker Validation Logic** (`worker/mqtt_publisher.py`)

Modify `execute_write_command()` method (currently at lines 346-412):

```python
def execute_write_command(self, job_id, device_id, object_type, object_instance,
                         value, priority, release, payload):
    """Execute BACnet write with comprehensive validation"""

    validation_errors = []

    # 1. Query point from database
    try:
        cursor = self.db_conn.cursor()
        cursor.execute('''
            SELECT
                id, "pointName", "haystackPointName", "isWritable",
                "minPresValue", "maxPresValue", "deviceId", "objectType", "objectInstance"
            FROM "Point"
            WHERE "deviceId" = %s
              AND "objectType" = %s
              AND "objectInstance" = %s
            LIMIT 1
        ''', (device_id, object_type, object_instance))

        point = cursor.fetchone()
        cursor.close()

        if not point:
            validation_errors.append({
                "field": "point",
                "message": f"Point not found: device={device_id}, {object_type}:{object_instance}"
            })
            return self._create_error_result(job_id, validation_errors)

    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return self._create_error_result(job_id, [{"field": "database", "message": str(e)}])

    # 2. Validate haystack name has "sp" in position 4
    haystack_name = point['haystackPointName']
    if haystack_name:
        parts = haystack_name.split('.')
        if len(parts) >= 4:
            if parts[3] != 'sp':
                validation_errors.append({
                    "field": "haystackName",
                    "message": f"Write not allowed: position 4 must be 'sp', found '{parts[3]}' in {haystack_name}",
                    "expected": "sp",
                    "actual": parts[3]
                })
        else:
            validation_errors.append({
                "field": "haystackName",
                "message": f"Invalid haystack name format: {haystack_name}",
                "expected": "minimum 4 parts (site.equip.id.sp...)"
            })

    # 3. Check isWritable flag
    if not point['isWritable']:
        validation_errors.append({
            "field": "isWritable",
            "message": f"Point {point['pointName']} is not writable (isWritable=false)"
        })

    # 4. Validate priority range (1-16)
    if not (1 <= priority <= 16):
        validation_errors.append({
            "field": "priority",
            "message": f"Priority must be 1-16, got {priority}"
        })

    # 5. Validate value range (if configured)
    if not release and value is not None:
        min_val = point.get('minPresValue')
        max_val = point.get('maxPresValue')

        if min_val is not None and value < min_val:
            validation_errors.append({
                "field": "value",
                "message": f"Value {value} below minimum {min_val}",
                "min": min_val,
                "actual": value
            })

        if max_val is not None and value > max_val:
            validation_errors.append({
                "field": "value",
                "message": f"Value {value} above maximum {max_val}",
                "max": max_val,
                "actual": value
            })

    # If validation failed, return error result
    if validation_errors:
        return self._create_error_result(job_id, validation_errors)

    # Validation passed - execute BACnet write
    try:
        success = await self.write_bacnet_value(
            device_ip=payload.get('deviceIp'),  # Need to add this to query
            device_id=device_id,
            object_type=object_type,
            object_instance=object_instance,
            value=value,
            priority=priority,
            release=release
        )

        result = {
            "jobId": job_id,
            "success": success,
            "timestamp": datetime.now(self.timezone).isoformat(),
            "deviceId": device_id,
            "objectType": object_type,
            "objectInstance": object_instance,
            "pointName": point['pointName'],
            "haystackName": haystack_name,
            "value": value,
            "priority": priority,
            "validationErrors": []
        }

        if not success:
            result["error"] = "BACnet write failed"

        return result

    except Exception as e:
        logger.error(f"BACnet write exception: {e}")
        return self._create_error_result(job_id, [{"field": "bacnet", "message": str(e)}])

def _create_error_result(self, job_id, validation_errors):
    """Create standardized error result"""
    return {
        "jobId": job_id,
        "success": False,
        "timestamp": datetime.now(self.timezone).isoformat(),
        "validationErrors": validation_errors
    }
```

**3. Frontend Updates**

Add validation fields to Points configuration page:
- Checkbox: "Allow Writes (isWritable)"
- Number inputs: "Min Value" and "Max Value"
- Visual indicator showing if point is writable

**4. Testing Checklist**

- [ ] Test "sp" validation: Try to write to sensor (position 4 = "sensor") → should fail
- [ ] Test "sp" validation: Write to setpoint (position 4 = "sp") → should succeed
- [ ] Test isWritable: Try to write when isWritable=false → should fail
- [ ] Test value range: Write value below min → should fail
- [ ] Test value range: Write value above max → should fail
- [ ] Test value range: Write valid value → should succeed
- [ ] Test priority: Try priority 0 or 17 → should fail
- [ ] Test result topic: Verify validationErrors array published correctly

---

### Phase 3: MQTT Authentication & TLS Support

**Status:** 🔴 Not Started
**Priority:** MEDIUM (Required for WAN deployments)

#### Current State
- Worker connects to MQTT without authentication
- No TLS encryption
- OK for local LAN deployments
- Not suitable for WAN/internet deployments

#### Required Changes

**1. Database Schema** (`frontend/prisma/schema.prisma`)

Add to MqttConfig model:
```prisma
model MqttConfig {
  // ... existing fields ...

  // Authentication
  username          String?
  password          String?

  // TLS/SSL
  tlsEnabled        Boolean  @default(false)
  tlsPort           Int      @default(8883)
  caCertificate     String?  // CA cert (PEM format)
  clientCertificate String?  // Client cert for mutual TLS
  clientKey         String?  // Client private key
}
```

**2. Worker Changes** (`worker/mqtt_publisher.py`)

Update `load_mqtt_config()` method:
```python
def load_mqtt_config(self):
    """Load MQTT config including auth and TLS"""
    try:
        cursor = self.db_conn.cursor()
        cursor.execute('''
            SELECT
                broker, port, "clientId",
                username, password,
                "tlsEnabled", "tlsPort",
                "caCertificate", "clientCertificate", "clientKey"
            FROM "MqttConfig"
            WHERE enabled = true
            LIMIT 1
        ''')
        config = cursor.fetchone()
        cursor.close()

        if config:
            self.mqtt_broker = config['broker']
            self.mqtt_port = config['tlsPort'] if config['tlsEnabled'] else config['port']
            self.mqtt_client_id = config['clientId']
            self.mqtt_username = config.get('username')
            self.mqtt_password = config.get('password')
            self.mqtt_tls_enabled = config.get('tlsEnabled', False)
            self.mqtt_ca_cert = config.get('caCertificate')
            self.mqtt_client_cert = config.get('clientCertificate')
            self.mqtt_client_key = config.get('clientKey')

            logger.info(f"📋 MQTT Config loaded: {self.mqtt_broker}:{self.mqtt_port}")
            if self.mqtt_username:
                logger.info(f"   Auth: Username = {self.mqtt_username}")
            if self.mqtt_tls_enabled:
                logger.info(f"   TLS: Enabled (port {self.mqtt_port})")

    except Exception as e:
        logger.error(f"Failed to load MQTT config: {e}")
```

Update `connect_mqtt()` method:
```python
def connect_mqtt(self):
    """Connect to MQTT broker with auth and TLS"""
    try:
        self.mqtt_client = mqtt.Client(client_id=self.mqtt_client_id)

        # Set username/password if configured
        if self.mqtt_username and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
            logger.info(f"🔐 MQTT authentication configured")

        # Configure TLS if enabled
        if self.mqtt_tls_enabled:
            import ssl
            import tempfile

            # Write certificates to temp files
            ca_cert_file = None
            client_cert_file = None
            client_key_file = None

            if self.mqtt_ca_cert:
                ca_cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
                ca_cert_file.write(self.mqtt_ca_cert)
                ca_cert_file.close()

            if self.mqtt_client_cert and self.mqtt_client_key:
                client_cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
                client_cert_file.write(self.mqtt_client_cert)
                client_cert_file.close()

                client_key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
                client_key_file.write(self.mqtt_client_key)
                client_key_file.close()

            # Configure TLS
            self.mqtt_client.tls_set(
                ca_certs=ca_cert_file.name if ca_cert_file else None,
                certfile=client_cert_file.name if client_cert_file else None,
                keyfile=client_key_file.name if client_key_file else None,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2
            )
            logger.info(f"🔒 MQTT TLS configured")

        # ... rest of connection logic ...

    except Exception as e:
        logger.error(f"MQTT connection failed: {e}")
        return False
```

**3. Frontend Settings Page**

Add MQTT authentication section:
- Username field
- Password field (masked input)
- TLS toggle
- TLS port field (default 8883)
- Certificate upload fields:
  - CA Certificate (textarea or file upload)
  - Client Certificate (optional, for mutual TLS)
  - Client Key (optional, for mutual TLS)

**4. Testing**

- [ ] Test username/password auth with EMQX/Mosquitto
- [ ] Test TLS connection (port 8883)
- [ ] Test TLS with CA verification
- [ ] Test mutual TLS (client cert + key)
- [ ] Test connection failure with wrong credentials
- [ ] Test graceful degradation if TLS fails

---

### Phase 4: CSV Export API for TimescaleDB

**Status:** 🔴 Not Started
**Priority:** LOW (Nice to have)

#### Goal
Provide REST API endpoint to export historical sensor data from TimescaleDB as CSV or JSON.

#### Implementation

**1. Create API Endpoint** (`frontend/src/app/api/timeseries/export/route.ts`)

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { Client } from 'pg';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;

  // Parse query parameters
  const start = searchParams.get('start'); // ISO 8601 timestamp
  const end = searchParams.get('end');
  const haystackName = searchParams.get('haystackName'); // Optional filter
  const format = searchParams.get('format') || 'csv'; // csv or json

  if (!start || !end) {
    return NextResponse.json(
      { error: 'Missing required parameters: start, end' },
      { status: 400 }
    );
  }

  try {
    // Connect to TimescaleDB
    const client = new Client({
      host: process.env.TIMESCALEDB_HOST || 'localhost',
      port: parseInt(process.env.TIMESCALEDB_PORT || '5435'),
      database: process.env.TIMESCALEDB_DB || 'timescaledb',
      user: process.env.TIMESCALEDB_USER || 'anatoli',
      password: process.env.TIMESCALEDB_PASSWORD || '',
    });

    await client.connect();

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

    const params: any[] = [start, end];

    if (haystackName) {
      query += ` AND haystack_name = $3`;
      params.push(haystackName);
    }

    query += ` ORDER BY time DESC LIMIT 10000`; // Safety limit

    // Execute query
    const result = await client.query(query, params);
    await client.end();

    if (format === 'json') {
      return NextResponse.json(result.rows);
    }

    // Convert to CSV
    if (result.rows.length === 0) {
      return new NextResponse('No data found', {
        headers: { 'Content-Type': 'text/csv' },
      });
    }

    const headers = Object.keys(result.rows[0]);
    const csvLines = [
      headers.join(','), // Header row
      ...result.rows.map(row =>
        headers.map(h => {
          const value = row[h];
          // Escape commas and quotes
          if (value === null) return '';
          const strValue = String(value);
          if (strValue.includes(',') || strValue.includes('"') || strValue.includes('\n')) {
            return `"${strValue.replace(/"/g, '""')}"`;
          }
          return strValue;
        }).join(',')
      )
    ];

    const csv = csvLines.join('\n');

    return new NextResponse(csv, {
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': `attachment; filename="sensor_data_${start}_${end}.csv"`,
      },
    });

  } catch (error) {
    console.error('Export error:', error);
    return NextResponse.json(
      { error: 'Export failed', details: String(error) },
      { status: 500 }
    );
  }
}
```

**2. Add Package Dependency**

```bash
cd frontend
npm install pg
```

**3. Update Environment Variables**

Add to `frontend/.env`:
```bash
TIMESCALEDB_HOST=localhost
TIMESCALEDB_PORT=5435
TIMESCALEDB_DB=timescaledb
TIMESCALEDB_USER=anatoli
TIMESCALEDB_PASSWORD=
```

**4. Frontend UI (Optional)**

Add export button to Monitoring page:
```typescript
// Example usage
const exportData = async () => {
  const start = '2025-12-09T00:00:00Z';
  const end = '2025-12-09T23:59:59Z';
  const url = `/api/timeseries/export?start=${start}&end=${end}&format=csv`;

  window.open(url, '_blank'); // Download CSV
};
```

**5. Testing**

- [ ] Export CSV for 1 hour time range
- [ ] Export JSON for 1 day time range
- [ ] Filter by specific haystack name
- [ ] Test with no data (empty result)
- [ ] Test CSV escaping (commas, quotes, newlines)
- [ ] Test 10,000 row limit
- [ ] Verify file download works in browser

---

## Implementation Priority

1. **Phase 2** (Write Validation) - **Start Next** - Security critical
2. **Phase 3** (MQTT Auth/TLS) - Required for production WAN deployment
3. **Phase 4** (CSV Export) - Nice to have, low priority

---

## Testing Strategy

### Phase 2 Testing
- Unit tests for validation logic
- Integration tests with actual MQTT broker
- Test matrix: all validation failure scenarios
- Verify validationErrors published correctly

### Phase 3 Testing
- Test with Mosquitto (username/password + TLS)
- Test with EMQX (cloud broker)
- Test certificate expiration handling
- Test connection failure scenarios

### Phase 4 Testing
- Test various time ranges (1h, 1d, 7d, 30d)
- Test large datasets (10k+ rows)
- Test CSV formatting edge cases
- Test API performance under load

---

## Documentation Updates Needed

After each phase:
1. Update README.md with new features
2. Update CLAUDE.md status
3. Update API documentation (if new endpoints)
4. Add troubleshooting section for new features

---

**Last Updated:** 2025-12-09
**Next Milestone:** Phase 2 - Write Command Validation

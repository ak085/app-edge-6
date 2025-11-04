# BacPipes - BACnet-to-MQTT Data Pipeline

## Project Overview
Production BACnet network integration system that discovers real BACnet devices, analyzes points, and streams data to MQTT/InfluxDB. Currently runs as Python scripts in LXC container on Proxmox.

**DEVELOPMENT GOAL**: Transform into full-stack Docker Compose application with web UI for BACnet point publishing to MQTT broker.

## Technology Stack
- **Python**: 3.10/3.11 (virtual env: `bac0_env`)
- **BACnet Libraries**: BACpypes3 v0.0.102, BAC0 v2025.6.10
- **Data Integration**: Paho MQTT v2.1.0, InfluxDB Client v1.49.0
- **Data Processing**: Pandas v2.3.1, NumPy v2.3.1
- **Configuration**: PyYAML v6.0.2, python-dotenv v1.0.0

## Current Architecture (LXC Container)

### 5-Stage Pipeline
```
Stage 1: Discovery (01_discovery_production.py)
  └─> Scans BACnet network, reads all device properties
  └─> Output: config/discovered_points.csv

Stage 2: Analysis (02_point_analysis.py)
  └─> Determines read/write capabilities, priority arrays
  └─> Output: Enhanced CSV with access type analysis

Stage 3: Equipment Mapping (03_device_equipment_lookup.py)
  └─> Adds configuration columns for manual mapping
  └─> Output: CSV ready for site/equipment tagging

Stage 4: JSON Generation (04_equipment_to_polling_json.py)
  └─> Converts CSV to runtime JSON
  └─> Output: config/production_json/polling_config.json

Stage 5: MQTT Publishing (05_production_mqtt.py)
  └─> Polls BACnet points, publishes to MQTT broker
  └─> Listens for write commands, executes BACnet writes
```

### Key Directories
```
BacPipes/
├── bac0_env/              # Python virtual environment (378 MB)
├── scripts/               # 7 Python scripts (3,688 lines total)
│   ├── 00_discovery_and_analysis.py      # Master: Stage 1-3
│   ├── 00_production_deployment.py       # Master: Stage 4-5
│   ├── 01_discovery_production.py        # BACnet network scan
│   ├── 02_point_analysis.py              # Access analysis
│   ├── 03_device_equipment_lookup.py     # Config columns
│   ├── 04_equipment_to_polling_json.py   # CSV to JSON
│   └── 05_production_mqtt.py             # MQTT publisher
├── config/
│   ├── bacnet_config.yaml                # Main configuration
│   ├── discovered_points.csv             # Discovery output
│   └── production_json/
│       └── polling_config.json           # Runtime config
├── setup.py               # Package: "Bac1" v2025.7.11
└── requirements.txt       # 9 dependencies
```

## Configuration (config/bacnet_config.yaml)

### Network
- Local IP: 192.168.1.35 (discovery machine)
- Broadcast: 192.168.1.255/24
- BACnet Port: 47808
- Device ID: 3001234 (discovery tool)

### External Services
- **MQTT Broker**: 10.0.60.2:1883
- **InfluxDB**: 10.0.60.5:8086 (bucket: bacnet_data, retention: 30d)
- **Timezone**: Asia/Kuala_Lumpur

### MQTT Topics
- Write commands: `bacnet/write/command`
- Write results: `bacnet/write/result`
- Polling data: `bacnet/polling/points`
- Point topics: `{site}/{equipment}/{object_type}/{property}` (e.g., `klcc/ahu_12/ao104/present_value`)

### Discovery Settings
- Timeout: 15 seconds
- Batch size: 3 objects/cycle
- Priority override: 8 (standard safe level)
- Include all properties: true

## Discovered Devices (Current Status)

### Device 221 - "Excelsior" (192.168.1.37)
- Type: AHU controller
- Objects: 25+ points
- Sensors: Temps, humidity, pressure, airflow
- Controls: Fan speed, valves, dampers

### Device 2020521 - "POS466.65/100" (192.168.1.42)
- Type: Siemens TechFree controller
- Objects: 25+ points
- Many writable points with 16-level priority arrays
- Firmware: 11.64

**Total**: 50+ points discovered, ~40% writable

## Current Usage

### Run Discovery & Analysis (Stages 1-3)
```bash
cd /home/ak101/BacPipes
source bac0_env/bin/activate
python3 scripts/00_discovery_and_analysis.py

# Manual step: Edit config/discovered_points.csv
# - Fill in site_id, equipment_type, equipment_id
# - Set mqtt_publish = true for points to publish
```

### Run Production Deployment (Stages 4-5)
```bash
python3 scripts/00_production_deployment.py
# Automatically runs Stage 4 & 5
# Ctrl+C for graceful shutdown
```

## Target Architecture (Full-Stack Docker Compose)

### Planned Services
```yaml
services:
  postgres:           # PostgreSQL 15 for discovered points
  frontend:           # Next.js 15 web UI (port 3001)
  bacnet-worker:      # Python polling/publishing service
  # Optional: mqtt-broker, influxdb (or use external)
```

### Frontend Features (Planned)
- **Dashboard**: System status, discovery control, MQTT connection status
- **Discovery Page**: Start/stop BACnet scan, view devices, browse points
- **Configuration Page**: Tag equipment, set polling intervals, enable/disable points
- **Monitoring Page**: Real-time MQTT data, send write commands, view historical data
- **Admin Page**: MQTT/InfluxDB settings, network configuration

### Database Schema (Planned - Prisma)
```prisma
model Device {
  id              Int      @id @default(autoincrement())
  deviceId        Int      @unique
  deviceName      String
  ipAddress       String
  port            Int      @default(47808)
  vendorId        Int?
  enabled         Boolean  @default(true)
  points          Point[]
  discoveredAt    DateTime @default(now())
  lastSeenAt      DateTime @updatedAt
}

model Point {
  id                    Int      @id @default(autoincrement())
  deviceId              Int
  device                Device   @relation(fields: [deviceId], references: [id])
  objectType            String   // analog-input, analog-output, etc.
  objectInstance        Int
  pointName             String
  description           String?
  units                 String?

  // Equipment mapping
  siteId                String?
  equipmentType         String?
  equipmentId           String?
  pointFunction         String?
  haystackPointName     String?

  // Configuration
  enabled               Boolean  @default(true)
  mqttPublish           Boolean  @default(false)
  pollInterval          Int      @default(60)
  qos                   Int      @default(1)

  // Access control
  isReadable            Boolean  @default(true)
  isWritable            Boolean  @default(false)
  priorityArray         Boolean  @default(false)
  priorityLevel         Int?

  // MQTT
  mqttTopic             String?

  createdAt             DateTime @default(now())
  updatedAt             DateTime @updatedAt

  @@unique([deviceId, objectType, objectInstance])
}

model MqttConfig {
  id                Int      @id @default(autoincrement())
  broker            String
  port              Int
  clientId          String
  username          String?
  password          String?
  keepAlive         Int      @default(30)
  enabled           Boolean  @default(true)
}

model InfluxConfig {
  id                Int      @id @default(autoincrement())
  host              String
  port              Int
  database          String
  organization      String?
  bucket            String?
  token             String?
  retentionDays     Int      @default(30)
  enabled           Boolean  @default(true)
}
```

### API Routes (Planned)
```
/api/discovery/start           # Start BACnet network scan
/api/discovery/stop            # Cancel discovery
/api/discovery/status          # Check progress
/api/devices                   # CRUD for devices
/api/points                    # CRUD for points
/api/points/bulk-update        # Update multiple points
/api/mqtt/status               # MQTT connection status
/api/mqtt/connect              # Connect to MQTT broker
/api/mqtt/disconnect           # Disconnect
/api/mqtt/write                # Send BACnet write command
/api/influx/status             # InfluxDB connection status
/api/config/mqtt               # MQTT configuration
/api/config/influx             # InfluxDB configuration
/api/config/network            # BACnet network settings
```

## Migration Plan

### Phase 1: Foundation
- [ ] Create Prisma schema for devices, points, MQTT/InfluxDB config
- [ ] Set up Docker Compose (postgres, frontend, worker services)
- [ ] Create Next.js frontend skeleton
- [ ] Set up environment variables (.env)

### Phase 2: Discovery Module
- [ ] Migrate Stage 1 discovery to API endpoint
- [ ] Create discovery UI (start/stop, progress, device list)
- [ ] Save discovered devices/points to PostgreSQL
- [ ] Replace CSV with database storage

### Phase 3: Configuration Module
- [ ] Create equipment mapping UI (replace manual CSV editing)
- [ ] Implement bulk point enable/disable
- [ ] Add MQTT topic generation logic
- [ ] Polling interval configuration per point

### Phase 4: MQTT Publishing Module
- [ ] Containerize Python polling worker
- [ ] Implement database-driven polling (read from PostgreSQL)
- [ ] MQTT connection management UI
- [ ] Real-time monitoring dashboard

### Phase 5: Advanced Features
- [ ] Historical data visualization (InfluxDB queries)
- [ ] Write command UI with priority control
- [ ] Alert/notification configuration
- [ ] Export/import configurations
- [ ] Multi-site management

## File References

### Key Files (with line numbers)
- Main config: `config/bacnet_config.yaml:1`
- Discovery CSV: `config/discovered_points.csv:1`
- Polling JSON: `config/production_json/polling_config.json:1`
- Discovery script: `scripts/01_discovery_production.py:1`
- MQTT publisher: `scripts/05_production_mqtt.py:1`
- Requirements: `requirements.txt:1`

## Current Status (Nov 1, 2025)
- ✅ Discovery completed: 50+ points from 2 devices
- ✅ Analysis completed: Access types determined
- ⚠️ Equipment mapping: In progress (CSV needs manual tagging)
- ⏳ Production deployment: Ready after CSV completion
- 🎯 **Target**: Transform into full-stack Docker Compose app with web UI

## Reference Architecture
Use `/home/ak101/dev-bacnet-similator-docker/` as template:
- Prisma ORM patterns
- Docker Compose structure
- Next.js API routes
- Frontend components (Shadcn/ui)
- Singleton patterns (Prisma client)
- Docker entrypoint scripts

## Development Objective
**Build a robust full-stack application for BACnet point publishing to MQTT broker** with:
- Web-based discovery and configuration (no manual CSV editing)
- PostgreSQL persistence (replace YAML/CSV files)
- Real-time monitoring dashboard
- Docker Compose deployment (portable, scalable)
- Similar UX to BACnet Simulator project

---

# DEVELOPMENT PLAN (Approved 2025-11-01)

## Architecture Decisions

### Database Strategy
**Decision**: PostgreSQL for configuration + External InfluxDB for time-series

**Rationale**:
- **PostgreSQL**: Ideal for relational configuration data
  - Stores discovered devices and points
  - Stores Haystack tags and MQTT settings
  - Stores operational metadata (last value, last poll time)
  - Lightweight (MB, not GB)
  - Proven in simulator project

- **InfluxDB (External)**: Optimized for time-series data
  - Already deployed at 10.0.60.5:8086
  - Stores historical point values with timestamps
  - Handles millions of data points efficiently
  - 30-day retention policy
  - Separate concern from configuration

**Data Flow**:
```
Discovery → PostgreSQL (configuration)
     ↓
Worker polls → MQTT Broker → InfluxDB (time-series)
     ↓
Dashboard reads PostgreSQL (last value) + InfluxDB (history)
```

**Why NOT TimescaleDB**: Already have InfluxDB for time-series, no need to duplicate storage.

### Development Approach
**Decision**: Docker Compose from day 1

**Rationale**:
- Proven reference architecture (dev-bacnet-simulator-docker)
- Hot-reload works in containers
- What you build = what you deploy
- No "works on my machine" issues
- Production-ready from start

**Why NOT Linux-first then containerize**: Double work, environment drift, delayed integration testing

### MQTT Broker Placement
**Decision**: External MQTT broker (10.0.60.2:1883) with optional internal for development

**Configuration**:
```yaml
services:
  mqtt-broker:  # Optional development broker
    image: eclipse-mosquitto:2
    profiles:
      - development  # Only starts with --profile development
```

**Rationale**:
- Production: Multiple BacPipes instances → single shared broker
- Development: Built-in broker for testing without external dependencies
- Separation of concerns: BacPipes is publisher, not message infrastructure

### Technology Stack (Approved)
- **Frontend**: Next.js 15 + TypeScript + Shadcn/ui (same as simulator)
- **Database**: PostgreSQL 15 + Prisma ORM
- **Worker**: Python 3.10 + BAC0 + paho-mqtt
- **Deployment**: Docker Compose
- **Ports**: 3001 (web), 5434 (postgres)

---

## Milestone Execution Plan

### Execution Rules
1. **Sequential Execution**: M1 → M2 → M3 → M4 → M5 → M6 → M7
2. **Blocking Rule**: Cannot proceed to next milestone until current is **100% complete and tested**
3. **Testing Requirement**: Each milestone must be verified working before advancing
4. **No Skipping**: Complete each milestone fully, even if it seems simple

---

### **MILESTONE 1: Foundation & Hello World** 🎯

**Goal**: Docker Compose running, web UI accessible, database connected

**Deliverables**:
- ✅ `docker-compose.yml` (postgres, frontend services)
- ✅ Next.js 15 app running on `http://localhost:3001`
- ✅ PostgreSQL on port 5434 (container internal: 5432)
- ✅ Prisma schema with core models:
  - Device (id, deviceId, deviceName, ipAddress, port, vendorId, enabled)
  - Point (all fields from planned schema)
  - MqttConfig (broker, port, clientId, credentials)
  - InfluxConfig (host, port, bucket, token)
- ✅ Database migrations applied
- ✅ Prisma client generated
- ✅ "Hello BacPipes" landing page with navigation

**Success Criteria**:
```bash
cd /home/ak101/BacPipes
docker-compose up
# Browser: http://localhost:3001 shows UI
# No errors in logs
# Can connect to PostgreSQL: docker exec -it bacpipes-postgres psql -U anatoli -d bacpipes
# Prisma Studio works: cd frontend && npx prisma studio
```

**Project Structure**:
```
BacPipes/
├── docker-compose.yml
├── .env
├── .gitignore
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── .env
│   ├── prisma/
│   │   ├── schema.prisma
│   │   ├── migrations/
│   │   └── seed.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── discovery/
│   │   │   ├── points/
│   │   │   ├── monitoring/
│   │   │   ├── settings/
│   │   │   └── api/
│   │   ├── components/
│   │   │   ├── ui/          # Shadcn components
│   │   │   └── layout/      # Navigation, header
│   │   └── lib/
│   │       ├── prisma.ts    # Singleton client
│   │       └── utils.ts
│   └── public/
└── worker/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    └── config.py
```

**Blocker**: Cannot proceed to M2 until Docker Compose runs cleanly and database is accessible.

---

### **MILESTONE 2: BACnet Discovery Configuration & Execution** 🎯

**Goal**: Configure and run BACnet discovery from web UI, save results to PostgreSQL

**Deliverables**:

**Frontend - Discovery Page** (`/discovery`):
- ✅ Configuration form:
  - Local IP address (dropdown from network interfaces)
  - BACnet port (default: 47808)
  - Discovery timeout (default: 15 seconds)
  - Device ID for scanner (default: 3001234)
  - Broadcast address (auto-calculated from IP/CIDR)
- ✅ "Start Discovery" button
- ✅ Progress indicator:
  - "Scanning network..." (animated)
  - "Found X devices, Y points"
  - Success/error messages
- ✅ Results display:
  - Device list with expandable point details
  - Point count per device
  - Last discovered timestamp

**Backend - API Routes**:
- ✅ `POST /api/discovery/start`
  - Body: `{ ipAddress, port, timeout, deviceId }`
  - Spawns Python discovery process
  - Returns: `{ success, jobId }`

- ✅ `GET /api/discovery/status?jobId=X`
  - Returns: `{ status: 'running' | 'complete' | 'error', progress, devices, points }`

- ✅ `POST /api/discovery/stop`
  - Cancels running discovery

- ✅ `GET /api/network/interfaces`
  - Returns available network interfaces for IP dropdown

**Worker - Discovery Service**:
- ✅ Migrate logic from `scripts/01_discovery_production.py`
- ✅ Use BAC0/BACpypes3 for BACnet scanning
- ✅ Save discovered devices to `Device` table
- ✅ Save discovered points to `Point` table
- ✅ Handle errors gracefully (timeout, network issues)
- ✅ Progress reporting (via database or API polling)

**Database Changes**:
- ✅ Add discovery job tracking table (optional):
  ```prisma
  model DiscoveryJob {
    id           String   @id @default(uuid())
    status       String   // running, complete, error
    ipAddress    String
    startedAt    DateTime @default(now())
    completedAt  DateTime?
    devicesFound Int      @default(0)
    pointsFound  Int      @default(0)
    errorMessage String?
  }
  ```

**Success Criteria**:
- Click "Start Discovery" on web UI
- Discovery runs in background
- Devices 221 ("Excelsior") and 2020521 ("POS466.65/100") appear in database
- 50+ points saved with correct properties:
  - objectType (analog-input, analog-output, etc.)
  - objectInstance
  - pointName
  - units
  - isReadable, isWritable (from stage 2 analysis logic)
- No manual CSV editing required
- Can run discovery multiple times (updates existing devices)

**Testing**:
```bash
# Verify discovery worked
docker exec -it bacpipes-postgres psql -U anatoli -d bacpipes
SELECT COUNT(*) FROM "Device";  -- Should show 2
SELECT COUNT(*) FROM "Point";   -- Should show 50+
SELECT "deviceName", COUNT(*) FROM "Point" p
  JOIN "Device" d ON p."deviceId" = d.id
  GROUP BY "deviceName";
```

**Blocker**: Cannot proceed to M3 until discovery saves data correctly to PostgreSQL.

---

### **MILESTONE 3: Point Display & Haystack Tagging UI** 🎯

**Goal**: Display discovered points in professional table, enable MQTT publishing, configure Haystack tags

**Deliverables**:

**Frontend - Points Page** (`/points`):

**Table View** (Shadcn Data Table):
- ✅ Columns displayed:
  | Device | Point Name | Type | Instance | Units | Value | MQTT | Actions |
  |--------|-----------|------|----------|-------|-------|------|---------|
  | Excelsior | Supply Temp | AI | 1 | °C | 22.5 | ☑️ | Edit ✏️ |

- ✅ Filter/Search:
  - Filter by device (dropdown)
  - Filter by object type (AI, AO, BI, BO, AV, BV)
  - Search by point name (live search)
  - Filter by MQTT publish status (enabled/disabled)

- ✅ Bulk Operations:
  - "Select All" / "Deselect All"
  - "Enable MQTT for Selected"
  - "Disable MQTT for Selected"
  - "Bulk Tag" (apply same Haystack tags to multiple points)

**Point Editor Modal**:
- ✅ Opens when clicking "Edit" or point row
- ✅ **6 Haystack Tag Fields** (dropdowns + text inputs):

  1. **Site ID** (dropdown + custom):
     - Options: `klcc`, `menara`, `plant_a`, `custom...`
     - Custom input if "custom..." selected

  2. **Equipment Type** (dropdown):
     - Options: `AHU`, `VAV`, `FCU`, `Chiller`, `CHWP`, `CWP`, `CT`, `Boiler`, `Spare`

  3. **Equipment ID** (text input):
     - Examples: `12`, `north_wing_01`, `roof_ahu_3`

  4. **Point Function** (dropdown):
     - Options: `sensor`, `setpoint`, `command`, `status`, `alarm`, `enable`

  5. **Point Type** (dropdown):
     - Options: `temp`, `pressure`, `flow`, `humidity`, `speed`, `power`, `current`, `voltage`, `position`, `percent`

  6. **Custom Tag** (optional text):
     - User-defined additional tag

- ✅ **MQTT Configuration**:
  - Checkbox: "Publish to MQTT"
  - Polling interval (seconds): `60` (default)
  - QoS level: `0`, `1`, `2` (default: 1)

- ✅ **MQTT Topic Preview** (auto-generated, read-only):
  - Format: `{site}/{equipment_type}_{equipment_id}/{object_type}{instance}/presentValue`
  - Example: `klcc/ahu_12/analogInput1/presentValue`
  - Updates live as tags are edited

- ✅ Save button (updates database)
- ✅ Cancel button

**Backend - API Routes**:
- ✅ `GET /api/points`
  - Query params: `deviceId`, `objectType`, `mqttPublish`, `search`
  - Returns paginated points with device info

- ✅ `GET /api/points/:id`
  - Returns single point with all details

- ✅ `PUT /api/points/:id`
  - Updates point (Haystack tags, MQTT config)
  - Regenerates MQTT topic based on tags

- ✅ `POST /api/points/bulk-update`
  - Body: `{ pointIds: [], updates: {} }`
  - Updates multiple points at once

**Database Schema** (from Prisma):
- Point table already has these fields (from M1):
  ```prisma
  siteId                String?
  equipmentType         String?
  equipmentId           String?
  pointFunction         String?
  haystackPointName     String?   // Custom tag
  mqttPublish           Boolean   @default(false)
  pollInterval          Int       @default(60)
  qos                   Int       @default(1)
  mqttTopic             String?   // Auto-generated
  ```

**MQTT Topic Generation Logic**:
```typescript
// lib/mqtt-topic.ts
export function generateMqttTopic(point: Point): string {
  const { siteId, equipmentType, equipmentId, objectType, objectInstance } = point

  if (!siteId || !equipmentType || !equipmentId) {
    return '' // Invalid, can't publish without tags
  }

  const equipment = `${equipmentType.toLowerCase()}_${equipmentId}`
  const object = `${objectType}${objectInstance}`

  return `${siteId}/${equipment}/${object}/presentValue`
}
```

**Success Criteria**:
- All 50+ points visible in table
- Can filter/search effectively
- Can check/uncheck "Publish to MQTT"
- Dropdowns populate with correct options
- Can edit point and save Haystack tags
- MQTT topic preview updates in real-time
- Topic format matches: `site/equipment/object/presentValue`
- Changes persist after page refresh
- Bulk operations work (select 10 points, enable MQTT for all)

**Testing**:
```sql
-- Verify tags saved
SELECT "pointName", "siteId", "equipmentType", "equipmentId", "mqttTopic"
FROM "Point"
WHERE "mqttPublish" = true
LIMIT 10;

-- Should see properly formatted topics:
-- klcc/ahu_12/analogInput1/presentValue
```

**UI Reference**: Use Shadcn Data Table component (same as simulator project)

**Blocker**: Cannot proceed to M4 until all points are properly tagged and MQTT topics generated.

---

### **MILESTONE 4: MQTT Publishing Worker** 🎯

**Goal**: Python worker polls enabled BACnet points and publishes to MQTT broker

**Deliverables**:

**Docker Service** (`bacnet-worker`):
- ✅ Python 3.10 container
- ✅ Dependencies: BAC0, paho-mqtt, psycopg2
- ✅ Dockerfile in `worker/` directory
- ✅ Depends on postgres and frontend services
- ✅ Network access to BACnet devices (192.168.1.0/24)
- ✅ Restarts automatically on failure

**Worker Application** (`worker/main.py`):

**Core Functions**:
1. **Database Connection**:
   - Connect to PostgreSQL
   - Read enabled points: `SELECT * FROM "Point" WHERE "mqttPublish" = true`
   - Cache point list, refresh every 60 seconds

2. **BACnet Polling**:
   - Initialize BAC0 application with configured IP
   - For each enabled point:
     - Read presentValue from BACnet device
     - Respect polling interval (don't poll faster than configured)
     - Handle read errors (log, don't crash)
   - Update database: `lastValue`, `lastPollTime`

3. **MQTT Publishing**:
   - Connect to MQTT broker (from MqttConfig table or env vars)
   - For each successful read:
     - Publish to point's MQTT topic
     - Include timestamp (ISO 8601 format)
     - Use configured QoS level
     - Payload format (JSON):
       ```json
       {
         "value": 22.5,
         "timestamp": "2025-11-01T10:30:00+08:00",
         "units": "degreesCelsius",
         "quality": "good",
         "deviceIp": "192.168.1.37",
         "deviceId": 221,
         "haystackName": "klcc.ahu.12.sensor.temp.air.supply.actual"
       }
       ```

4. **Error Handling**:
   - Graceful degradation (skip failed points, continue polling)
   - Exponential backoff on repeated failures
   - Log all errors with context
   - Reconnect to MQTT on disconnect

5. **Graceful Shutdown**:
   - Listen for SIGTERM/SIGINT
   - Stop polling loop
   - Disconnect from MQTT cleanly
   - Close database connection

**Configuration** (`worker/config.py`):
```python
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Database
    DB_HOST = os.getenv('DB_HOST', 'postgres')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'bacpipes')
    DB_USER = os.getenv('DB_USER', 'anatoli')

    # BACnet
    BACNET_IP = os.getenv('BACNET_IP', '192.168.1.35')
    BACNET_PORT = int(os.getenv('BACNET_PORT', '47808'))

    # MQTT
    MQTT_BROKER = os.getenv('MQTT_BROKER', '10.0.60.2')
    MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
    MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'bacpipes_worker')

    # Polling
    DEFAULT_POLL_INTERVAL = int(os.getenv('DEFAULT_POLL_INTERVAL', '60'))
    CONFIG_REFRESH_INTERVAL = int(os.getenv('CONFIG_REFRESH_INTERVAL', '60'))
```

**Logging**:
- ✅ Structured logging (timestamp, level, message)
- ✅ Log startup configuration
- ✅ Log each poll cycle summary
- ✅ Log MQTT connection status
- ✅ Log errors with full context
- ✅ Visible via `docker-compose logs bacnet-worker`

**Success Criteria**:
```bash
# Start services
docker-compose up

# Worker starts automatically
docker-compose logs bacnet-worker
# Should see:
# [INFO] Worker started, polling 15 points
# [INFO] Connected to MQTT broker 10.0.60.2:1883
# [INFO] Polling cycle 1: 15 points read, 15 published
# [INFO] Polling cycle 2: 15 points read, 15 published

# Verify MQTT messages
mosquitto_sub -h 10.0.60.2 -t "klcc/#" -v
# Should see:
# klcc/ahu_12/analogInput1/presentValue {"value": 22.5, "timestamp": "..."}
```

**Database Verification**:
```sql
SELECT "pointName", "lastValue", "lastPollTime"
FROM "Point"
WHERE "mqttPublish" = true
ORDER BY "lastPollTime" DESC
LIMIT 10;

-- Should show recent timestamps and current values
```

**Requirements File** (`worker/requirements.txt`):
```
BAC0==2025.6.10
paho-mqtt==2.1.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
```

**Dockerfile** (`worker/Dockerfile`):
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

**Blocker**: Cannot proceed to M5 until worker publishes reliably to MQTT.

---

### **MILESTONE 5: Monitoring Dashboard** 🎯

**Goal**: Real-time visibility into publishing status and point values

**Deliverables**:

**Frontend - Dashboard Page** (`/` or `/dashboard`):

**Status Cards** (top of page):
- ✅ MQTT Connection Status:
  - 🟢 Connected to 10.0.60.2:1883
  - 🔴 Disconnected (with last error)
  - Last message published: "2 seconds ago"

- ✅ Publishing Statistics:
  - Total points: 52
  - Enabled for MQTT: 15
  - Publishing: 15
  - Errors: 0

- ✅ Worker Status:
  - Worker state: Running / Stopped / Error
  - Uptime: "2 hours 15 minutes"
  - Last poll cycle: "10 seconds ago"

**Real-Time Point Values Table**:
- ✅ Columns:
  | Device | Point Name | Current Value | Units | Last Update | Status | Trend |
  |--------|-----------|---------------|-------|-------------|--------|-------|
  | Excelsior | Supply Temp | 22.5 | °C | 5s ago | 🟢 | ↑ |

- ✅ Auto-refresh every 10 seconds (configurable)
- ✅ Color coding:
  - 🟢 Green: Updated < 2 minutes ago
  - 🟡 Yellow: Updated 2-5 minutes ago
  - 🔴 Red: Updated > 5 minutes ago (stale)

- ✅ Trend indicator:
  - ↑ Increasing
  - ↓ Decreasing
  - → Stable
  - ? Unknown (first reading)

**Control Panel**:
- ✅ "Pause Publishing" button
  - Stops worker polling (via API call)
  - Shows "Resume Publishing" when paused

- ✅ "Reconnect MQTT" button
  - Forces worker to reconnect to broker

- ✅ "Refresh Config" button
  - Forces worker to reload point list from database

**Error Log Panel** (collapsible):
- ✅ Recent errors (last 50)
- ✅ Columns: Timestamp | Point | Error Message
- ✅ Auto-scroll to latest
- ✅ Clear button

**Backend - API Routes**:
- ✅ `GET /api/monitoring/status`
  - Returns worker status, MQTT connection, statistics

- ✅ `GET /api/monitoring/points`
  - Returns enabled points with latest values and timestamps
  - Includes trend calculation

- ✅ `GET /api/monitoring/errors`
  - Returns recent error log entries

- ✅ `POST /api/monitoring/pause`
  - Pauses worker polling

- ✅ `POST /api/monitoring/resume`
  - Resumes worker polling

- ✅ `POST /api/monitoring/reconnect`
  - Forces MQTT reconnection

**Worker Updates**:
- ✅ Add control mechanism (pause/resume via database flag or signal)
- ✅ Store errors in database:
  ```prisma
  model ErrorLog {
    id        Int      @id @default(autoincrement())
    pointId   Int?
    message   String
    timestamp DateTime @default(now())
  }
  ```

**Frontend State Management**:
- ✅ Use React hooks for auto-refresh
- ✅ WebSocket or polling for real-time updates
- ✅ Optimistic UI updates

**Success Criteria**:
- Dashboard shows accurate real-time data
- Point values update without page refresh (every 10 seconds)
- Can see MQTT connection status
- Can pause/resume publishing
- Pause/resume works without restarting Docker containers
- Errors display with clear context
- Trend indicators work correctly
- Color coding helps identify stale data

**Testing**:
```bash
# Verify dashboard updates
# 1. Open http://localhost:3001
# 2. Watch point values update every 10 seconds
# 3. Click "Pause Publishing"
# 4. Verify updates stop
# 5. Click "Resume Publishing"
# 6. Verify updates resume
```

**Blocker**: Cannot proceed to M6 until monitoring dashboard is functional.

---

### **MILESTONE 6: BACnet Write Commands** 🎯

**Goal**: Send write commands to BACnet devices from web UI

**Deliverables**:

**Frontend - Write Command UI** (in Points page or Monitoring page):

**Point Row Actions**:
- ✅ "Write" button (only visible for writable points: `isWritable = true`)
- ✅ Click "Write" opens modal:

**Write Command Modal**:
- ✅ Point info display:
  - Device: Excelsior
  - Point: Cooling Valve Position
  - Type: analogOutput
  - Current Value: 45.0%

- ✅ Write form:
  - **Value input** (text/number):
    - Validates based on point type (number for AO/AV, boolean for BO/BV)
    - Shows units hint

  - **Priority Level** (dropdown):
    - Options: 1-16
    - Default: 8 (Manual Operator)
    - Shows priority names:
      - 1: Manual Life Safety
      - 2: Automatic Life Safety
      - 8: Manual Operator (default)
      - 16: Scheduled (lowest)

  - **Release Priority** (checkbox):
    - If checked, releases priority instead of writing value
    - Disables value input when checked

- ✅ "Send Write Command" button
- ✅ Result display:
  - ✅ Success: "Value written successfully"
  - ❌ Error: "Write failed: [reason]"

**Backend - API Routes**:
- ✅ `POST /api/bacnet/write`
  - Body:
    ```json
    {
      "pointId": 123,
      "value": 50.0,
      "priority": 8,
      "release": false
    }
    ```
  - Validates point is writable
  - Publishes write command to MQTT topic: `bacnet/write/command`
  - Returns write job ID

- ✅ `GET /api/bacnet/write-status/:jobId`
  - Returns write result from database

**Worker - Write Command Handler**:

**MQTT Subscription**:
- ✅ Subscribe to topic: `bacnet/write/command`
- ✅ Command message format:
  ```json
  {
    "jobId": "uuid-1234",
    "deviceId": 221,
    "objectType": "analog-output",
    "objectInstance": 104,
    "value": 50.0,
    "priority": 8,
    "release": false
  }
  ```

**Write Execution**:
- ✅ Validate device exists and is reachable
- ✅ Validate point is writable
- ✅ Execute BACnet write via BAC0:
  ```python
  from BAC0 import connect

  bacnet = connect(ip=BACNET_IP)

  # Write value
  bacnet.write(
      address=f"{device_ip}",
      obj_type="analogOutput",
      obj_inst=104,
      prop="presentValue",
      value=50.0,
      priority=8
  )

  # Or release priority
  bacnet.write(..., value=None, priority=8)  # None = release
  ```

- ✅ Publish result to topic: `bacnet/write/result`
  ```json
  {
    "jobId": "uuid-1234",
    "success": true,
    "timestamp": "2025-11-01T10:30:00+08:00",
    "error": null
  }
  ```

**Write Result Logging**:
- ✅ Store write history in database:
  ```prisma
  model WriteHistory {
    id            Int      @id @default(autoincrement())
    jobId         String   @unique
    pointId       Int
    point         Point    @relation(fields: [pointId], references: [id])
    value         String?
    priority      Int
    release       Boolean
    success       Boolean
    errorMessage  String?
    timestamp     DateTime @default(now())
  }
  ```

**Success Criteria**:
- Can identify writable points in UI
- Write modal opens and validates input
- Can write value to analog output (e.g., valve position)
- Can write boolean to binary output (e.g., fan command)
- Priority levels work correctly
- Can release priority (write null)
- Write result appears in UI (success/error)
- BACnet device reflects change (verify with YABE or device display)
- Priority array shows write at correct priority level
- Error handling works (invalid value, unreachable device, read-only point)

**Testing**:
```bash
# Test write command
# 1. Open points page
# 2. Find writable point (isWritable = true)
# 3. Click "Write" button
# 4. Enter value: 50
# 5. Select priority: 8
# 6. Click "Send Write Command"
# 7. Verify success message
# 8. Check YABE: priority 8 shows value 50
# 9. Test release: check "Release Priority", submit
# 10. Check YABE: priority 8 now null
```

**Blocker**: Cannot proceed to M7 until write commands work reliably.

---

### **MILESTONE 7: Configuration Management & Polish** 🎯

**Goal**: Production-ready features, settings management, professional UI

**Deliverables**:

**Frontend - Settings Page** (`/settings`):

**Tabs/Sections**:

1. **BACnet Network Settings**:
   - Local IP address (dropdown)
   - BACnet port (default: 47808)
   - Device ID (default: 3001234)
   - Discovery timeout (seconds)
   - Save button

2. **MQTT Broker Settings**:
   - Broker host (default: 10.0.60.2)
   - Port (default: 1883)
   - Client ID (default: bacpipes_worker)
   - Username (optional)
   - Password (optional, masked)
   - Keep-alive interval (seconds)
   - Test Connection button
   - Save button

3. **InfluxDB Settings** (optional for future):
   - Host (default: 10.0.60.5)
   - Port (default: 8086)
   - Bucket (default: bacnet_data)
   - Organization
   - Token (masked)
   - Retention days (default: 30)
   - Enabled checkbox
   - Test Connection button
   - Save button

4. **System Settings**:
   - Timezone (default: Asia/Kuala_Lumpur)
   - Default polling interval (seconds)
   - Auto-refresh interval for dashboard (seconds)
   - Log retention days
   - Save button

**Export/Import Configuration**:
- ✅ "Export Configuration" button:
  - Downloads JSON file with:
    - All points with Haystack tags
    - MQTT configuration
    - Network settings
  - Filename: `bacpipes_config_2025-11-01.json`

- ✅ "Import Configuration" button:
  - Upload JSON file
  - Preview changes (show diff)
  - Confirm import
  - Updates database

**Backend - API Routes**:
- ✅ `GET /api/config/bacnet`
- ✅ `PUT /api/config/bacnet`
- ✅ `GET /api/config/mqtt`
- ✅ `PUT /api/config/mqtt`
- ✅ `POST /api/config/mqtt/test`
- ✅ `GET /api/config/influx`
- ✅ `PUT /api/config/influx`
- ✅ `POST /api/config/influx/test`
- ✅ `GET /api/config/export`
- ✅ `POST /api/config/import`

**UI Polish**:
- ✅ Responsive design (works on tablet/mobile)
- ✅ Loading states for all async operations
- ✅ Toast notifications (success/error feedback)
- ✅ Confirmation dialogs for destructive actions
- ✅ Keyboard shortcuts (Ctrl+S to save, etc.)
- ✅ Professional color scheme (consistent with simulator)
- ✅ Proper error handling throughout app
- ✅ Form validation with helpful error messages

**Documentation**:
- ✅ Update README.md:
  - Project overview
  - Quick start guide
  - Architecture diagram
  - API documentation
  - Troubleshooting guide

- ✅ Create DEPLOYMENT.md:
  - Docker Compose installation
  - Environment variables reference
  - Network configuration
  - MQTT broker setup
  - InfluxDB setup (optional)
  - Backup/restore procedures

- ✅ Create API_REFERENCE.md:
  - All API endpoints documented
  - Request/response examples
  - Authentication (if added)

**Testing & Quality**:
- ✅ Test all features end-to-end
- ✅ Test on fresh Docker environment
- ✅ Test import/export functionality
- ✅ Verify all settings persist after restart
- ✅ Check for console errors
- ✅ Verify responsive design on different screen sizes
- ✅ Test error scenarios (network down, invalid inputs)

**Success Criteria**:
- All settings can be configured from UI
- MQTT connection test works
- Can export complete configuration
- Can import configuration on fresh system
- UI is professional and polished
- No console errors
- Works on tablet and mobile
- Documentation is complete and accurate
- Fresh deployment works following README
- All features from M1-M6 still work

**Production Readiness Checklist**:
- [ ] Docker Compose starts cleanly on fresh system
- [ ] All environment variables documented
- [ ] Database migrations work correctly
- [ ] Worker restarts automatically on failure
- [ ] Logs are structured and helpful
- [ ] Error handling is comprehensive
- [ ] Settings persist across restarts
- [ ] Export/import tested and working
- [ ] Documentation complete
- [ ] No hardcoded credentials

---

## Current Development Status

**Active Milestone**: 🎯 **M1: Foundation & Hello World** (Not Started)

### Milestone Progress Tracker

- [ ] **M1: Foundation & Hello World**
  - Status: Not Started
  - Blocker: None
  - Next Steps: Create project structure, Docker Compose, Prisma schema

- [ ] **M2: BACnet Discovery**
  - Status: Waiting for M1
  - Blocker: M1 incomplete

- [ ] **M3: Point Display & Haystack Tagging**
  - Status: Waiting for M2
  - Blocker: M2 incomplete

- [ ] **M4: MQTT Publishing Worker**
  - Status: Waiting for M3
  - Blocker: M3 incomplete

- [ ] **M5: Monitoring Dashboard**
  - Status: Waiting for M4
  - Blocker: M4 incomplete

- [ ] **M6: BACnet Write Commands**
  - Status: Waiting for M5
  - Blocker: M5 incomplete

- [ ] **M7: Configuration Management & Polish**
  - Status: Waiting for M6
  - Blocker: M6 incomplete

---

## Decision Log

**2025-11-01: Database Selection**
- **Decision**: PostgreSQL for configuration + InfluxDB for time-series
- **Alternatives Considered**: TimescaleDB (PostgreSQL extension), InfluxDB only
- **Rationale**: InfluxDB already deployed externally, PostgreSQL perfect for relational config data, no need to duplicate time-series storage

**2025-11-01: Development Approach**
- **Decision**: Docker Compose from day 1
- **Alternatives Considered**: Linux-first then containerize
- **Rationale**: Reference architecture proven, hot-reload works, production parity, avoid double work

**2025-11-01: MQTT Broker Placement**
- **Decision**: External broker (10.0.60.2) with optional internal for development
- **Alternatives Considered**: Always internal, always external
- **Rationale**: Production needs shared broker, development benefits from self-contained setup

**2025-11-01: Execution Strategy**
- **Decision**: 7 sequential blocking milestones
- **Alternatives Considered**: Parallel development, agile sprints
- **Rationale**: Clear progress tracking, testable checkpoints, avoid incomplete features

---

## Technical Reference

### Port Allocation
- **3001**: Frontend web UI
- **5434**: PostgreSQL (host) → 5432 (container)
- **47808**: BACnet protocol (standard, worker container)

### Network Configuration
- **Frontend**: Bridge network (communicates with postgres)
- **Worker**: Bridge network (needs access to BACnet subnet 192.168.1.0/24)
- **PostgreSQL**: Internal bridge network

### Environment Variables (`.env`)
```bash
# Database
DATABASE_URL="postgresql://anatoli@postgres:5432/bacpipes"
POSTGRES_USER=anatoli
POSTGRES_DB=bacpipes

# BACnet
BACNET_IP=192.168.1.35
BACNET_PORT=47808

# MQTT
MQTT_BROKER=10.0.60.2
MQTT_PORT=1883
MQTT_CLIENT_ID=bacpipes_worker

# InfluxDB (optional)
INFLUX_HOST=10.0.60.5
INFLUX_PORT=8086
INFLUX_BUCKET=bacnet_data
INFLUX_ORG=bacnet
INFLUX_TOKEN=

# System
TZ=Asia/Kuala_Lumpur
NODE_ENV=production
```

### Docker Compose Services
```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: anatoli
      POSTGRES_DB: bacpipes
    ports:
      - "5434:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U anatoli"]
      interval: 10s

  frontend:
    build: ./frontend
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "3001:3000"
    environment:
      DATABASE_URL: postgresql://anatoli@postgres:5432/bacpipes
    volumes:
      - ./frontend:/app
      - /app/node_modules

  bacnet-worker:
    build: ./worker
    depends_on:
      - postgres
      - frontend
    environment:
      DB_HOST: postgres
      MQTT_BROKER: 10.0.60.2
      BACNET_IP: 192.168.1.35
    network_mode: bridge  # Needs access to external BACnet network

volumes:
  postgres_data:
```

---

## ARCHITECTURAL DECISIONS (Nov 2, 2025)

### Critical Design Choices for ML/AI Data Pipeline

**Status**: M3 (Point Display & Haystack Tagging) completed. Moving to M4 implementation.

#### 1. Navigation & UI Framework ✅

**Decision**: Unified navigation using Next.js App Router `layout.tsx`

**Implementation**:
- Shared navigation bar across all pages
- Pages: Dashboard, Discovery, Points, Monitoring, Settings
- Client-side routing via Next.js `<Link>` components
- Active route highlighting
- Mobile-responsive design

**Graphics Design**:
- ✅ Tailwind CSS v4 (continue current approach)
- ✅ Shadcn/ui components
- 🎨 **Enhanced visuals**:
  - Increased contrast for better readability
  - Mild, professional color palette
  - Icons/logos for visual navigation cues
  - Avatars for user actions
  - Better visual hierarchy

**Why**: Next.js App Router provides server-side layouts, no need for React Router (client-side only).

---

#### 2. MQTT Broker Hosting Strategy ⭐

**Decision**: Separate LXC Container (NOT in Docker Compose)

**Configuration**:
```
LXC Container: mqtt-broker
IP: 10.0.60.2
Port: 1883
Software: Eclipse Mosquitto 2.x
Storage: /var/lib/mosquitto (persistent)
Backup: Daily snapshots
```

**Rationale**:
- ✅ **High Availability**: Broker stays up during BacPipes restarts
- ✅ **Multi-instance**: Shared by multiple BacPipes deployments
- ✅ **Data Persistence**: Messages/subscriptions survive restarts
- ✅ **Resource Isolation**: Dedicated CPU/RAM allocation
- ✅ **Independent Scaling**: Can upgrade broker without touching BacPipes

**Why NOT in Docker Compose**:
- ❌ Single point of failure
- ❌ Lost data on container restart
- ❌ Cannot share between multiple BacPipes instances
- ❌ Limited scalability

---

#### 3. MQTT Publishing Strategy (ML/AI Optimized) ⭐⭐⭐

**Decision**: Hybrid Publishing - Individual AND Batched Topics

**Critical for ML/AI workloads**: Synchronized timestamps, complete feature vectors, efficient parsing.

##### **Strategy A: Individual Point Topics**

**Format**: `{site}/{equipment}/{point}/presentValue`

**Example**:
```
Topic: klcc/ahu_12/ai1/presentValue
Payload: {
  "value": 22.5,
  "timestamp": "2025-11-02T15:30:00+08:00",
  "units": "degreesCelsius",
  "quality": "good",
  "haystackName": "klcc.ahu.12.sensor.temp.air.supply.actual",
  "deviceIp": "192.168.1.37",
  "deviceId": 221,
  "objectType": "analog-input",
  "objectInstance": 1
}

QoS: 1 (at least once)
Retain: true (last value always available)
Frequency: Per point poll interval (e.g., 60s)
```

**Use Case**: Real-time dashboards, single-point monitoring, alerts

---

##### **Strategy B: Equipment-Level Batch** ⭐ PRIMARY FOR ML/AI

**Format**: `{site}/{equipment}/batch`

**Example**:
```
Topic: klcc/ahu_12/batch
Payload: {
  "timestamp": "2025-11-02T15:30:00+08:00",
  "equipment": "ahu_12",
  "site": "klcc",
  "points": [
    {
      "name": "ai1",
      "haystackName": "klcc.ahu.12.sensor.temp.air.supply.actual",
      "value": 22.5,
      "units": "degreesCelsius",
      "quality": "good"
    },
    {
      "name": "ai2",
      "haystackName": "klcc.ahu.12.sensor.temp.air.return.actual",
      "value": 24.0,
      "units": "degreesCelsius",
      "quality": "good"
    },
    {
      "name": "ao1",
      "haystackName": "klcc.ahu.12.cmd.pos.chilled-water.coil.effective",
      "value": 45.0,
      "units": "percent",
      "quality": "good"
    }
  ],
  "metadata": {
    "pollCycle": 123,
    "totalPoints": 25,
    "successfulReads": 25,
    "failedReads": 0
  }
}

QoS: 1
Retain: false (historical → InfluxDB)
Frequency: Once per poll cycle (all points together)
```

**Benefits for ML/AI**:
- ✅ **Synchronized Timestamps**: All points polled together
- ✅ **Complete Feature Vector**: All inputs in one message
- ✅ **Missing Data Detection**: Know exactly which points failed
- ✅ **Efficient Parsing**: 1 subscription, 1 JSON parse → complete dataset
- ✅ **Reduced Overhead**: 1 topic instead of 50 individual subscriptions

**Why Critical**: ML training requires all features (inputs) with the same timestamp. Individual topics create timestamp misalignment issues.

---

##### **Strategy C: Site-Level Bulk** (Optional)

**Format**: `{site}/data/bulk`

**Example**:
```
Topic: klcc/data/bulk
Payload: {
  "timestamp": "2025-11-02T15:30:00+08:00",
  "site": "klcc",
  "pollCycle": 123,
  "equipment": [
    { "equipmentId": "ahu_12", "type": "ahu", "points": [...] },
    { "equipmentId": "chiller_01", "type": "chiller", "points": [...] }
  ]
}
```

**Use Case**: Cross-equipment ML models, data warehouse ingestion, backup

---

#### 4. MQTT Topic Documentation & Export ✅

**Decision**: Both in-app display AND downloadable exports

**Implementation**:

**A. In-App Display** (Points Page):
- Add "MQTT Topic" column to points table
- Copy-to-clipboard button per topic
- Visual indication of publishing status

**B. Downloadable Exports**:

**1. Topic List** (`mqtt_topics.txt`):
```
# BacPipes MQTT Topics Reference
# Site: klcc
# Generated: 2025-11-02 15:30:00

klcc/ahu_12/ai1/presentValue    # Supply Air Temperature (°C)
klcc/ahu_12/ai2/presentValue    # Return Air Temperature (°C)
klcc/ahu_12/batch               # Equipment batch (all points)
```

**2. Subscriber Guide** (`mqtt_subscription_guide.json`):
```json
{
  "broker": "10.0.60.2:1883",
  "generatedAt": "2025-11-02T15:30:00+08:00",
  "site": "klcc",
  "topics": [
    {
      "topic": "klcc/ahu_12/ai1/presentValue",
      "description": "Supply Air Temperature",
      "units": "degreesCelsius",
      "haystackName": "klcc.ahu.12.sensor.temp.air.supply.actual",
      "updateInterval": 60,
      "qos": 1,
      "retain": true
    },
    {
      "topic": "klcc/ahu_12/batch",
      "description": "AHU-12 Equipment Batch (25 points)",
      "format": "equipment_batch",
      "updateInterval": 60,
      "qos": 1,
      "retain": false,
      "pointCount": 25
    }
  ]
}
```

**3. AsyncAPI Specification** (Future):
- Auto-generated from database
- Industry-standard MQTT API documentation

---

#### 5. MQTT Payload Standards for ML/AI

**Required Fields** (ALWAYS include):
```json
{
  "timestamp": "2025-11-02T15:30:00+08:00",  // ISO 8601 with timezone
  "value": 22.5,                              // Numeric (never string!)
  "units": "degreesCelsius",                  // For unit conversion
  "quality": "good",                          // good | uncertain | bad
  "haystackName": "klcc.ahu.12.sensor..."    // Semantic meaning
}
```

**Optional but Helpful**:
```json
{
  "deviceTime": "2025-11-02T15:29:58+08:00", // DDC controller timestamp
  "pollDuration": 1.2,                        // Read time (seconds)
  "confidence": 0.95,                         // ML validation score
  "outlier": false,                           // Outlier detection flag
  "interpolated": false                       // Interpolation flag
}
```

**Data Quality Flags**:
- `good`: Valid, reliable measurement
- `uncertain`: Value read successfully but questionable (e.g., sensor drift)
- `bad`: Communication error, null value, or failed read

---

### Implementation Priority (Next Steps)

**Current Status**: M3 completed (Haystack tagging UI with meta-data support)

**Immediate Tasks** (Nov 2, 2025):

**Task A**: Add Navigation Layout ✅ NEXT
- Create shared `layout.tsx` with navigation bar
- Add icons/logos for visual hierarchy
- Implement active route highlighting
- Mobile-responsive design
- Estimated: 30 minutes

**Task B**: MQTT Topic Export Functionality ⏳
- Add "MQTT Topic" column to points table
- Copy-to-clipboard functionality
- Export topics list (TXT)
- Export subscriber guide (JSON)
- Estimated: 30 minutes

**Task C**: Design Batched Publishing Strategy ⏳
- Update worker to publish both individual AND batch topics
- Implement equipment-level batching
- Add metadata (poll cycle, success/failure counts)
- Requires M4 (MQTT Publishing Worker)
- Estimated: M4 implementation

---

## Haystack Tagging Enhancements (Nov 2, 2025)

### Meta-Data Point Support ✅

**Added Quantities** for BACnet Schedule/Calendar/DateTime objects:
- `schedule` - BACnet Schedule objects (weekly, exception schedules)
- `calendar` - BACnet Calendar objects (holidays, special dates)
- `datetime` - BACnet DateTime value objects
- `date` - BACnet Date value objects

**Smart Validation**:
- Meta-data points allow blank `subject` and `location` fields
- Example: `klcc.ahu.12.sp.schedule..auto` (double dots = blank fields)
- Regular points still require all 8 Haystack fields

**UI Enhancements**:
- Grouped in "Meta-Data / Scheduling" optgroup
- Visual indicator when meta-data quantity selected
- Dynamic field labels (optional vs required)
- Common patterns reference includes scheduling examples

**Use Cases**:
- Occupancy schedules
- Temperature setpoint schedules
- Equipment start/stop schedules
- Holiday calendars
- Time synchronization points

---

## Next Steps

**Immediate Action**: Implement navigation layout (Task A)

1. Create project directory structure
2. Write `docker-compose.yml`
3. Create frontend Dockerfile and Next.js app
4. Create Prisma schema
5. Set up environment variables
6. Test: `docker-compose up` should show "Hello BacPipes"

**Ready to proceed?** Confirm to start M1 implementation.

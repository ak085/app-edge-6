# BacPipes - BACnet Discovery & MQTT Publishing Platform

**Production-ready BACnet-to-MQTT bridge with web-based configuration and remote monitoring**

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](docker-compose.yml)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.10-yellow?logo=python)](https://www.python.org/)

---

## Overview

BacPipes is a distributed BACnet-to-MQTT data pipeline designed for enterprise building management systems (BMS). It enables real-time monitoring, data collection, and remote control of BACnet devices with MQTT bridge support for multi-site deployments.

### Key Features

- 🔍 **BACnet Discovery** - Automatic network scanning and device detection
- 🏷️ **Haystack Tagging** - Industry-standard semantic naming (8-field structure)
- 📡 **MQTT Publishing** - Real-time data streaming to local and remote brokers
- 🌉 **MQTT Bridge** - Automatic data replication from local to remote sites
- 📊 **Monitoring Dashboard** - Real-time visualization on port 3003
- ✏️ **BACnet Write** - Web-based control with priority array support
- ⏱️ **TimescaleDB** - Time-series data storage and historical analytics
- 🐳 **Docker Compose** - Single-command deployment

### Current Status

- ✅ **Foundation** - Docker Compose, PostgreSQL, Prisma ORM
- ✅ **BACnet Discovery** - Web UI for network scanning
- ✅ **Point Configuration** - Haystack tagging, MQTT topic generation
- ✅ **MQTT Publishing** - Per-point intervals, external broker architecture
- ✅ **Monitoring Dashboard** - Real-time SSE streaming (port 3003)
- ✅ **BACnet Write Commands** - Priority array control
- ✅ **Time-Series Storage** - TimescaleDB with custom Python bridge
- ✅ **MQTT Bridge** - Local-to-remote broker forwarding (configured and working)
- ✅ **Production Deployment** - Optimized build with minimal memory footprint

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB RAM minimum (8GB recommended)
- Linux (Ubuntu/Debian recommended)
- Network access to BACnet devices

### Installation

```bash
# Clone repository
git clone http://10.0.10.2:30008/ak101/dev-bacnet-discovery-docker.git
cd BacPipes

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env

# Start core services
docker compose up -d

# Start monitoring stack (TimescaleDB + Dashboard)
docker compose -f docker-compose-monitoring.yml up -d

# View logs
docker compose logs -f bacnet-worker

# Access web UI
open http://192.168.1.35:3001

# Access monitoring dashboard
open http://192.168.1.35:3003
```

### First-Time Setup

1. **Configure Network Settings**
   - Navigate to http://192.168.1.35:3001/settings
   - Enter your local BACnet IP address (default: 192.168.1.35)
   - Configure MQTT broker (default: 10.0.60.3:1883)
   - Set timezone for your site (default: Asia/Kuala_Lumpur)

2. **Discover BACnet Devices**
   - Go to http://192.168.1.35:3001/discovery
   - Click "Start Discovery"
   - Wait for scan to complete (~15-30 seconds)
   - Review discovered devices and points

3. **Configure Points with Haystack Tags**
   - Go to http://192.168.1.35:3001/points
   - Select points to configure
   - Add Haystack tags: site, equipment type, equipment ID, point function
   - MQTT topics auto-generate from tags
   - Enable "Publish to MQTT" checkbox

4. **Verify Data Flow**
   ```bash
   # Subscribe to local MQTT broker
   mosquitto_sub -h 10.0.60.3 -t "bacnet/#" -v

   # Check worker logs
   docker compose logs -f bacnet-worker

   # Monitor dashboard
   open http://192.168.1.35:3003
   ```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────┐
│ LXC: bacpipes-discovery (192.168.1.35)     │
│ Docker Compose Stack                        │
├─────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────────┐            │
│  │PostgreSQL├─→│ Next.js UI   │            │
│  │(Config)  │  │(Web GUI)     │            │
│  │Port 5434 │  │Port 3001     │            │
│  └──────────┘  └──────────────┘            │
│                                             │
│  ┌────────────────┐                        │
│  │ BACnet Worker  │                        │
│  │ (Python+BAC0)  │                        │
│  │ (Host network) │                        │
│  └───────┬────────┘                        │
│          │                                  │
│  ┌───────┴────────┐                        │
│  │  TimescaleDB   │                        │
│  │  (Time-series) │                        │
│  │  Port 5435     │                        │
│  └───────┬────────┘                        │
│          │                                  │
│  ┌───────┴────────┐                        │
│  │   Telegraf     │                        │
│  │  (MQTT→DB)     │                        │
│  └───────┬────────┘                        │
│          │                                  │
│  ┌───────┴────────┐                        │
│  │   Monitoring   │                        │
│  │   Dashboard    │                        │
│  │   Port 3003    │                        │
│  └────────────────┘                        │
│                                             │
│  BACnet Network ←──┐                       │
│                    │                       │
│  MQTT Publish ─────┼────→                  │
└────────────────────┼───────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────┐
│ LXC: mqtt-broker (10.0.60.3)                │
├─────────────────────────────────────────────┤
│  Mosquitto MQTT Broker                      │
│  Port: 1883 (local network)                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  ⚙️  MQTT BRIDGE CONFIGURED HERE            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
└─────────────────┬───────────────────────────┘
                  │ Bridge forwards
                  ↓
┌─────────────────────────────────────────────┐
│ LXC: remote-mqtt-broker (10.0.80.3)         │
├─────────────────────────────────────────────┤
│  Mosquitto MQTT Broker                      │
│  Port: 1883 (simulates remote HQ)           │
│  Aggregates data from all sites             │
└─────────────────┬───────────────────────────┘
                  │ MQTT subscribe
                  ↓
┌─────────────────────────────────────────────┐
│ Remote Monitoring Dashboard                 │
│ IP: 10.0.80.2                               │
│ Consumes aggregated multi-site data         │
└─────────────────────────────────────────────┘
```

### Data Flow

1. **BACnet Discovery**: Worker discovers devices on 192.168.1.0/24 network
2. **Point Configuration**: Web UI tags points with Haystack metadata
3. **Polling**: Worker reads BACnet points at configured intervals (e.g., 60s)
4. **Local Storage**: Telegraf writes data to TimescaleDB for local monitoring
5. **MQTT Publishing**: Worker publishes to local broker (10.0.60.3:1883)
6. **Bridge Forward**: MQTT bridge automatically forwards topics to remote broker (10.0.80.3:1883)
7. **Remote Monitoring**: Remote dashboard consumes aggregated data from all sites

### Key Characteristics

- **Modular LXC Deployment**: Each component runs in separate container for high availability
- **External MQTT Broker**: Shared infrastructure, survives BacPipes restarts
- **Multi-Instance Support**: Single MQTT broker serves multiple BacPipes deployments
- **Database-Driven**: PostgreSQL for configuration, TimescaleDB for time-series
- **Web-Based**: No manual CSV editing, all configuration via GUI

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Next.js 15 + TypeScript | Web UI for configuration and monitoring |
| **Database** | PostgreSQL 15 + Prisma ORM | Device/point configuration storage |
| **Time-Series** | TimescaleDB (PostgreSQL extension) | Historical data storage |
| **Worker** | Python 3.10 + BAC0 | BACnet polling and MQTT publishing |
| **Ingestion** | Telegraf | MQTT → TimescaleDB data pipeline |
| **MQTT Broker** | Eclipse Mosquitto 2.x | Local message broker (external LXC) |
| **MQTT Bridge** | Mosquitto Bridge | Local → Remote data replication |
| **Deployment** | Docker Compose | Container orchestration |

---

## Port Allocation

| Port | Service | Description |
|------|---------|-------------|
| **3001** | Frontend Web UI | Discovery, configuration, settings |
| **3003** | Monitoring Dashboard | Real-time data visualization |
| **5434** | PostgreSQL | Configuration database (host port) |
| **5435** | TimescaleDB | Time-series database (host port) |
| **47808** | BACnet Worker | BACnet/IP protocol (UDP) |
| **1883** | MQTT Broker (10.0.60.3) | Local MQTT broker (external LXC) |
| **1883** | MQTT Broker (10.0.80.3) | Remote MQTT broker (external LXC) |

---

## Configuration

### Environment Variables

Key settings in `.env`:

```bash
# Database
POSTGRES_USER=anatoli
POSTGRES_DB=bacpipes
DATABASE_URL="postgresql://anatoli@postgres:5432/bacpipes"

# BACnet Network
BACNET_IP=192.168.1.35
BACNET_PORT=47808
BACNET_DEVICE_ID=3001234

# MQTT Broker (external)
MQTT_BROKER=10.0.60.3
MQTT_PORT=1883

# TimescaleDB
TIMESCALEDB_URL="postgresql://anatoli@timescaledb:5432/timescaledb"

# System
TZ=Asia/Kuala_Lumpur
NODE_ENV=production
```

### Web UI Settings

Access http://192.168.1.35:3001/settings to configure:

- **BACnet Network**: IP address, port, device ID
- **MQTT Broker**: Host (10.0.60.3), port (1883), batch publishing toggle
- **System**: Timezone (50+ timezones supported)

All settings stored in database - no `.env` editing required after initial setup!

---

## MQTT Bridge Setup

The MQTT bridge is already **configured and working** between local (10.0.60.3) and remote (10.0.80.3) brokers.

### Current Configuration

- **Local Broker**: 10.0.60.3:1883 (LXC: mqtt-broker)
- **Remote Broker**: 10.0.80.3:1883 (LXC: remote-mqtt-broker)
- **Bridge Topics**: `bacnet/#` (all BACnet data forwarded with QoS 1)
- **Write Commands**: `bacnet/write/#` (inbound from remote, QoS 1)

### Verification

```bash
# Test local → remote forwarding
# On local broker, publish test message
mosquitto_pub -h 10.0.60.3 -t 'bacnet/test/message' -m 'Hello from local site'

# On remote broker, subscribe to forwarded topics
mosquitto_sub -h 10.0.80.3 -t 'bacnet/#' -v
# Should see: bacnet/test/message Hello from local site
```

### Documentation

See [MQTT_BRIDGE_SETUP.md](MQTT_BRIDGE_SETUP.md) for:
- Complete bridge configuration guide
- Troubleshooting common issues
- Security hardening (TLS/SSL setup)
- Multi-site deployment patterns

---

## Project Structure

```
BacPipes/
├── frontend/                   # Next.js web application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Dashboard
│   │   │   ├── discovery/page.tsx     # BACnet discovery
│   │   │   ├── points/page.tsx        # Point configuration
│   │   │   ├── settings/page.tsx      # System settings
│   │   │   └── api/                   # REST API routes
│   │   ├── components/                # React components
│   │   └── lib/                       # Utilities, Prisma client
│   ├── prisma/
│   │   ├── schema.prisma              # Database schema
│   │   └── migrations/                # Migration history
│   └── package.json
│
├── worker/                     # Python BACnet worker
│   ├── mqtt_publisher.py              # Main worker (BAC0)
│   ├── bacnet_write_handler.py        # Write command handler
│   ├── requirements.txt
│   └── Dockerfile
│
├── monitoring-dashboard/       # Monitoring UI (port 3003)
│   ├── src/app/
│   │   ├── page.tsx                   # Main dashboard
│   │   └── api/                       # TimescaleDB queries
│   └── package.json
│
├── telegraf/                   # MQTT → TimescaleDB ingestion
│   ├── mqtt_to_timescaledb.py         # Custom Python bridge
│   └── requirements.txt
│
├── timescaledb/
│   └── init/
│       └── 01_init.sql                # Hypertable setup
│
├── scripts/                    # Legacy Python scripts (archived)
│   └── *.py                           # Original CSV-based workflow
│
├── doc/
│   └── archive/
│       └── MIGRATION_TO_MODULAR_ARCHITECTURE.md  # Historical docs
│
├── docker-compose.yml          # Core services
├── docker-compose-monitoring.yml  # Monitoring stack
├── .env                        # Configuration (gitignored)
├── MQTT_BRIDGE_SETUP.md        # Bridge configuration guide
├── ROADMAP.md                  # Development roadmap
└── README.md                   # This file
```

---

## Common Operations

### Service Management

```bash
# Start all services
cd /home/ak101/BacPipes
docker compose up -d
docker compose -f docker-compose-monitoring.yml up -d

# Stop all services (graceful)
docker compose stop
docker compose -f docker-compose-monitoring.yml stop

# Stop and remove containers (keeps database data)
docker compose down
docker compose -f docker-compose-monitoring.yml down

# Complete cleanup (⚠️ DELETES DATABASE!)
docker compose down -v
docker compose -f docker-compose-monitoring.yml down -v

# View logs
docker compose logs -f bacnet-worker
docker compose -f docker-compose-monitoring.yml logs -f telegraf

# Restart services
docker compose restart bacnet-worker
docker compose -f docker-compose-monitoring.yml restart

# Force rebuild
docker compose up -d --build
```

### Database Operations

```bash
# Access PostgreSQL (configuration)
docker exec -it bacpipes-postgres psql -U anatoli -d bacpipes

# Access TimescaleDB (time-series)
docker exec -it bacpipes-timescaledb psql -U anatoli -d timescaledb

# Query recent data
docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c "
  SELECT time, haystack_name, dis, value
  FROM sensor_readings
  WHERE time > NOW() - INTERVAL '5 minutes'
  ORDER BY time DESC LIMIT 10;
"

# Run Prisma migrations
cd frontend
npx prisma migrate deploy

# Generate Prisma client
npx prisma generate

# Reset database (⚠️ deletes all data)
npx prisma migrate reset
```

### MQTT Testing

```bash
# Subscribe to all topics on local broker
mosquitto_sub -h 10.0.60.3 -t "bacnet/#" -v

# Subscribe to all topics on remote broker
mosquitto_sub -h 10.0.80.3 -t "bacnet/#" -v

# Publish test message
mosquitto_pub -h 10.0.60.3 -t "bacnet/test" -m '{"value": 123}'

# Test write command
mosquitto_pub -h 10.0.60.3 -t "bacnet/write/command" -m '{
  "deviceId": 2020521,
  "objectType": "analog-value",
  "objectInstance": 120,
  "value": 21.5,
  "priority": 8
}'
```

### Backup & Restore

```bash
# Backup PostgreSQL configuration database
docker exec bacpipes-postgres pg_dump -U anatoli bacpipes > backup_config.sql

# Backup TimescaleDB time-series database
docker exec bacpipes-timescaledb pg_dump -U anatoli timescaledb > backup_timeseries.sql

# Restore configuration database
docker exec -i bacpipes-postgres psql -U anatoli bacpipes < backup_config.sql

# Restore time-series database
docker exec -i bacpipes-timescaledb psql -U anatoli timescaledb < backup_timeseries.sql

# Backup Docker volumes
docker run --rm -v bacpipes_postgres_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/postgres_backup.tar.gz /data
```

---

## User Guide

### BACnet Discovery

1. Navigate to http://192.168.1.35:3001/discovery
2. Click "Start Discovery" button
3. Wait for network scan (15-30 seconds)
4. Review discovered devices:
   - Device 221 "Excelsior" (192.168.1.37) - AHU controller
   - Device 2020521 "POS466.65/100" (192.168.1.42) - Siemens controller
5. Points are automatically saved to database

### Point Configuration with Haystack Tags

1. Navigate to http://192.168.1.35:3001/points
2. Filter by device or object type
3. Click "Edit" on any point
4. Configure 8-field Haystack tags:
   - **Site ID**: klcc, menara, plant_a
   - **Equipment Type**: AHU, VAV, FCU, Chiller, CHWP, CWP, CT
   - **Equipment ID**: 12, north_wing_01
   - **Point Function**: sensor, setpoint, command, status
   - **Measurement Type**: temp, pressure, flow, humidity
   - **Substance**: air, water, steam
   - **Location**: supply, return, outdoor
   - **Descriptor**: actual, effective, setpoint
5. MQTT topic auto-generates: `{site}/{equipment_type}_{equipment_id}/{object}/presentValue`
6. Enable "Publish to MQTT" checkbox
7. Set polling interval (default: 60 seconds)
8. Save changes

**Example Haystack Name**: `klcc.ahu.12.sensor.temp.air.supply.actual`

**Generated MQTT Topic**: `klcc/ahu_12/analogInput1/presentValue`

### Monitoring Dashboard

Access real-time data at http://192.168.1.35:3003

**Features:**
- Live data stream with auto-updates (no page refresh)
- In-place row updates (one row per point)
- Natural scrolling with sticky headers
- Topic filtering and search
- Pause/Resume data stream
- CSV export functionality
- Connection status indicator

**Connection Status:**
- 🟢 Green = Connected to MQTT broker
- 🟡 Yellow = Connecting...
- 🔴 Red = Disconnected

### BACnet Write Commands

Send write commands to BACnet devices from monitoring page:

1. Navigate to http://192.168.1.35:3003
2. Find point to control
3. Click "✏️ Write" button
4. Enter new value
5. Select priority level (1-16, default: 8)
6. Click "Send Write Command"

**Priority Levels:**
- **1-2**: Life safety (highest)
- **8**: Manual operator (recommended)
- **16**: Scheduled/default (lowest)

**Release Priority:**
- Check "Release Priority" to remove manual override
- Point reverts to next active priority or default value

### Timezone Configuration

1. Go to http://192.168.1.35:3001/settings
2. Select timezone from dropdown
3. Click "Save Settings"
4. Restart worker: `docker compose restart bacnet-worker`
5. Wait 30-60 seconds for fresh data

**Available Timezones**: 500+ IANA timezones including Asia/Kuala_Lumpur, Asia/Singapore, Europe/Paris, America/New_York

---

## MQTT Topic Format

### Individual Point Topics

**Format**: `{site}/{equipment}/{point}/presentValue`

**Examples**:
- `klcc/ahu_12/analogInput1/presentValue`
- `menara/chiller_01/analogValue15/presentValue`
- `plant/vav_north_12/binaryInput3/presentValue`

**Payload**:
```json
{
  "value": 22.5,
  "timestamp": "2025-11-23T15:30:00+08:00",
  "units": "degreesCelsius",
  "quality": "good",
  "dis": "Supply Air Temperature",
  "haystackName": "klcc.ahu.12.sensor.temp.air.supply.actual"
}
```

### Equipment Batch Topics (Optional)

**Format**: `{site}/{equipment}/batch`

**Examples**:
- `klcc/ahu_12/batch`
- `menara/chiller_01/batch`

**Payload**:
```json
{
  "timestamp": "2025-11-23T15:30:00+08:00",
  "equipment": "ahu_12",
  "site": "klcc",
  "points": [
    {"name": "ai1", "value": 22.5, "units": "degreesCelsius", "quality": "good"},
    {"name": "ai2", "value": 24.0, "units": "degreesCelsius", "quality": "good"},
    {"name": "ao1", "value": 45.0, "units": "percent", "quality": "good"}
  ],
  "metadata": {
    "pollCycle": 123,
    "totalPoints": 25,
    "successfulReads": 25
  }
}
```

**Note**: Batch publishing is disabled by default. Enable in Settings to avoid data redundancy.

---

## Troubleshooting

### Worker Not Publishing Data

1. **Check worker logs**:
   ```bash
   docker compose logs -f bacnet-worker
   ```

2. **Verify BACnet connectivity**:
   ```bash
   docker exec bacpipes-worker ping 192.168.1.37
   ```

3. **Check MQTT broker**:
   ```bash
   mosquitto_sub -h 10.0.60.3 -t "bacnet/#" -v
   ```

4. **Verify points enabled**:
   ```bash
   docker exec bacpipes-postgres psql -U anatoli -d bacpipes -c \
     'SELECT COUNT(*) FROM "Point" WHERE "mqttPublish" = true;'
   ```

### Discovery Finds No Devices

1. Verify BACnet IP is correct (check Settings page)
2. Ensure worker has network access to BACnet subnet
3. Check firewall rules (UDP port 47808)
4. Try manual BACnet tool (YABE) from same network

### MQTT Bridge Not Forwarding

1. **Check bridge logs on local broker**:
   ```bash
   ssh ak101@10.0.60.3
   sudo journalctl -u mosquitto -n 50 | grep -i bridge
   ```

2. **Expected log entries**:
   - `Connecting bridge remote-bridge (10.0.80.3:1883)`
   - `Received CONNACK on connection remote-bridge`

3. **Test connectivity**:
   ```bash
   # From local broker
   nc -zv 10.0.80.3 1883
   ```

4. **See troubleshooting guide**: [MQTT_BRIDGE_SETUP.md](MQTT_BRIDGE_SETUP.md)

### Database Connection Errors

1. **Check PostgreSQL**:
   ```bash
   docker compose ps postgres
   ```

2. **Verify connection string**:
   ```bash
   grep DATABASE_URL .env
   ```

3. **Restart database**:
   ```bash
   docker compose restart postgres
   ```

### TimescaleDB No Data

1. **Check Telegraf logs**:
   ```bash
   docker compose -f docker-compose-monitoring.yml logs -f telegraf
   ```

2. **Verify data exists**:
   ```bash
   docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c \
     'SELECT COUNT(*) FROM sensor_readings;'
   ```

3. **Restart Telegraf**:
   ```bash
   docker compose -f docker-compose-monitoring.yml restart telegraf
   ```

---

## Development Roadmap

### Completed Features (v1.0.0)

**Phase 1: Foundation & Core Features**
- ✅ Full-stack Docker Compose application
- ✅ Next.js 15 frontend with TypeScript
- ✅ PostgreSQL database with Prisma ORM
- ✅ BACnet discovery via web UI
- ✅ Point management and configuration
- ✅ Haystack tagging system (8-field semantic naming)
- ✅ MQTT publishing to external broker
- ✅ TimescaleDB time-series storage
- ✅ Monitoring dashboard (port 3003)
- ✅ BACnet write command support
- ✅ Priority array control

**Phase 2: Modular Architecture**
- ✅ Separated MQTT broker to dedicated LXC container (10.0.60.3)
- ✅ Removed internal MQTT broker from Docker Compose
- ✅ Database-driven MQTT configuration
- ✅ Dual configuration update (.env + database)
- ✅ Verified external broker connectivity

**Phase 3: Monitoring & MQTT Bridge**
- ✅ TimescaleDB hypertable for sensor_readings
- ✅ Telegraf MQTT consumer (custom Python bridge)
- ✅ Monitoring dashboard on port 3003
- ✅ CSV export functionality
- ✅ Time-range selection
- ✅ Real-time point value display
- ✅ MQTT bridge configured (10.0.60.3 → 10.0.80.3)

### Short-Term Roadmap (Next 3 Months)

**1. Enhanced Monitoring** (Priority: High)
- [ ] Add Grafana dashboards for visual analytics
- [ ] Create pre-built panels for common metrics
- [ ] Implement alerting rules (temperature thresholds, offline devices)
- [ ] Add trend analysis (7-day, 30-day patterns)
- [ ] Integration with external monitoring systems

**2. Data Quality & Retention** (Priority: High)
- [ ] Implement TimescaleDB compression policies (automatic after 7 days)
- [ ] Configure retention policies (default: 90 days, configurable)
- [ ] Add data quality indicators (good/uncertain/bad)
- [ ] Implement outlier detection
- [ ] Add data validation rules

**3. User Authentication & Security** (Priority: Medium)
- [ ] Add authentication to web UI (NextAuth.js)
- [ ] Role-based access control (viewer, operator, admin)
- [ ] API key management for external integrations
- [ ] MQTT authentication (username/password)
- [ ] Audit logging for configuration changes

**4. Enhanced BACnet Features** (Priority: Medium)
- [ ] Support for BACnet trends (historical data from devices)
- [ ] Support for BACnet schedules (read/write)
- [ ] Support for BACnet alarms and events
- [ ] COV (Change of Value) subscription support
- [ ] BACnet device grouping and organization

### Mid-Term Roadmap (3-6 Months)

**1. Multi-Site Management**
- [ ] Central dashboard showing all sites
- [ ] Per-site filtering and navigation
- [ ] Aggregated analytics across sites
- [ ] Site identifier in MQTT topics (`site_id/equipment/point`)

**2. Configuration Management**
- [ ] Configuration templates (AHU, FCU, Chiller presets)
- [ ] Bulk import/export (CSV, JSON, Excel)
- [ ] Configuration versioning (track changes over time)
- [ ] Clone configuration between sites
- [ ] Configuration backup/restore

**3. Advanced Analytics**
- [ ] Equipment performance metrics (runtime hours, start/stop counts)
- [ ] Energy consumption tracking
- [ ] Efficiency calculations (COP, kW/ton)
- [ ] Fault detection and diagnostics (FDD)
- [ ] Predictive maintenance alerts

### Long-Term Roadmap (6-12 Months)

**1. Machine Learning Integration**
- [ ] Anomaly detection (sensor drift, unusual patterns)
- [ ] Energy optimization recommendations
- [ ] Predictive maintenance (equipment failure prediction)
- [ ] Occupancy pattern learning
- [ ] Setpoint optimization

**2. Integration Ecosystem**
- [ ] RESTful API for external systems
- [ ] GraphQL API for flexible queries
- [ ] Webhook support for events
- [ ] IFTTT/Zapier-style automation rules
- [ ] Integration with BMS systems (Tridium, Siemens, JCI)

**3. Advanced Scheduling**
- [ ] Web-based schedule editor (weekly, exception, calendar)
- [ ] Holiday calendar management
- [ ] Occupancy-based scheduling
- [ ] Demand response integration
- [ ] Energy pricing integration (peak/off-peak)

**4. Mobile Application**
- [ ] Native iOS/Android apps
- [ ] Push notifications for alarms
- [ ] Mobile-optimized dashboard
- [ ] Offline mode (cached data)
- [ ] QR code scanning for equipment identification

---

## Performance & Scaling

### Typical Resource Usage (Per Site)

| Resource | Usage | Notes |
|----------|-------|-------|
| **CPU** | 5-10% | 2-4 cores sufficient |
| **RAM** | 1-2GB | Docker stack total |
| **Disk** | 1GB/week | TimescaleDB with 7-day retention |
| **Network** | 10KB/s | Per 100 points at 60s intervals |
| **MQTT msgs/sec** | 1-5 | Depends on polling frequency |

### Scaling Guidelines

- **Single site**: Raspberry Pi 4 (4GB RAM) sufficient
- **10 sites**: Standard VM (8GB RAM, 4 vCPU)
- **100+ points**: Tested and working (current deployment)
- **1000+ points**: Consider batching, increase worker resources

### Known Limitations

1. **Single BACnet Network**: Only supports devices on same network (192.168.1.0/24)
   - Future: Support for BACnet/IP routing (BBMD)

2. **No Authentication**: Web UI is open to anyone on network
   - Mitigation: Deploy on trusted network only
   - Roadmap: Add NextAuth.js authentication

3. **Manual Haystack Tagging**: Requires user to tag each point
   - Roadmap: Add AI-assisted tagging (pattern recognition)

4. **Polling Interval**: Current default 60 seconds
   - Can be reduced to 10-30 seconds for critical points
   - Not recommended <10 seconds (network overhead)

---

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Detailed technical documentation and project context
- **[ROADMAP.md](ROADMAP.md)** - Full development roadmap with future features
- **[MQTT_BRIDGE_SETUP.md](MQTT_BRIDGE_SETUP.md)** - Complete MQTT bridge configuration guide
- **[doc/archive/MIGRATION_TO_MODULAR_ARCHITECTURE.md](doc/archive/MIGRATION_TO_MODULAR_ARCHITECTURE.md)** - Historical migration documentation

---

## Repository

- **Gitea**: http://10.0.10.2:30008/ak101/dev-bacnet-discovery-docker
- **Branch**: `development` (active development)
- **Branches**:
  - `main`: Production releases
  - `development`: Active development
  - `legacy-csv-workflow`: Archived CSV-based workflow

---

## Support

For issues or questions:
- Check logs: `docker compose logs -f bacnet-worker`
- Review troubleshooting section above
- Verify network connectivity: `ping`, `nc -zv`
- Test with `mosquitto_pub` and `mosquitto_sub` tools
- Create issue on Gitea repository

---

**Last Updated**: 2025-11-23
**Status**: Production-ready for single-site deployment with MQTT bridge support
**Version**: v1.0.0

---

**Built for the building automation community** 🏢

# BacPipes - BACnet Discovery & MQTT Publishing Platform

## Current Status (2025-11-21)

**Production Ready**: Full-stack Docker Compose application for BACnet point discovery, configuration, and MQTT publishing.

**Completed Features**:
- ✅ BACnet device/point discovery with web UI
- ✅ Haystack tagging system (8-field semantic naming)
- ✅ MQTT publishing to external broker (modular architecture)
- ✅ TimescaleDB time-series storage
- ✅ Monitoring dashboard (port 3003)
- ✅ BACnet write command support (priority array control)
- ✅ Site-to-remote data synchronization

## Technology Stack

- **Frontend**: Next.js 15 + TypeScript + Shadcn/ui
- **Database**: PostgreSQL 15 (configuration) + TimescaleDB (time-series)
- **Worker**: Python 3.10 + BAC0 + paho-mqtt
- **Ingestion**: Telegraf (MQTT → TimescaleDB)
- **Deployment**: Docker Compose

## Architecture

```
┌─────────────────────────────────────────────┐
│ LXC: bacpipes-discovery (192.168.1.35)     │
│ Docker Compose Stack                        │
├─────────────────────────────────────────────┤
│  Frontend (Next.js) - Port 3001             │
│  ├─ Discovery                               │
│  ├─ Points (Haystack tagging)               │
│  └─ Monitoring                              │
│                                             │
│  PostgreSQL - Port 5434                     │
│  └─ Devices, Points, MqttConfig             │
│                                             │
│  BACnet Worker (Python/BAC0)                │
│  ├─ Polls BACnet devices (192.168.1.0/24)  │
│  ├─ Publishes to MQTT (10.0.60.3)           │
│  └─ Handles write commands                  │
│                                             │
│  TimescaleDB - Port 5435                    │
│  └─ sensor_readings (hypertable)            │
│                                             │
│  Telegraf (MQTT → TimescaleDB)              │
│  └─ Subscribes from external MQTT           │
│                                             │
│  Monitoring Dashboard - Port 3003           │
│  └─ View/export time-series data            │
│                                             │
└─────────────────────────────────────────────┘
                  ↓ MQTT publish
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

## Key Features

### 1. BACnet Discovery
- Network scan via web UI
- Automatic device/point detection
- Save to PostgreSQL database
- View discovered devices and points

### 2. Haystack Tagging
- 8-field semantic naming system:
  - `{site}.{equip}.{equipRef}.{point}.{measurement}.{substance}.{condition}.{descriptor}`
- Example: `klcc.ahu.12.sensor.temp.air.supply.actual`
- MQTT topics auto-generated from tags
- Supports all BACnet object types (AI, AO, BI, BO, AV, BV, MSI, MSO, MSV, CSV, IV, DV, DTV)

### 3. MQTT Publishing
- External broker architecture (10.0.60.3:1883)
- Minute-aligned polling for synchronized timestamps
- JSON payloads with full metadata
- QoS 1 (at least once delivery)
- Write command support via `bacnet/write/command` topic

### 4. Time-Series Storage
- TimescaleDB hypertable (`sensor_readings`)
- Automatic compression and retention policies
- Indexed on `time DESC` for fast queries
- Haystack name + display name for semantic queries

### 5. Monitoring Dashboard
- Real-time point value display
- Time-range selection
- CSV export functionality
- Historical data visualization

## Quick Start

```bash
cd /home/ak101/BacPipes

# Start core services (discovery + publishing)
docker compose up -d

# Start monitoring stack (TimescaleDB + dashboard)
docker compose -f docker-compose-monitoring.yml up -d

# Access UIs
# Discovery/Configuration: http://192.168.1.35:3001
# Monitoring Dashboard:    http://192.168.1.35:3003
```

## Common Commands

### Service Management
```bash
# View logs
docker compose logs -f bacnet-worker
docker compose -f docker-compose-monitoring.yml logs -f telegraf

# Restart services
docker compose restart bacnet-worker
docker compose -f docker-compose-monitoring.yml restart telegraf

# Check service status
docker compose ps
```

### Database Access
```bash
# PostgreSQL (configuration)
docker exec -it bacpipes-postgres psql -U anatoli -d bacpipes

# TimescaleDB (time-series)
docker exec -it bacpipes-timescaledb psql -U anatoli -d timescaledb

# Query recent data
docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c "
  SELECT time, haystack_name, dis, value
  FROM sensor_readings
  WHERE time > NOW() - INTERVAL '5 minutes'
  ORDER BY time DESC LIMIT 10;
"
```

### MQTT Testing
```bash
# Subscribe to all topics
mosquitto_sub -h 10.0.60.3 -t "bacnet/#" -v

# Publish write command
mosquitto_pub -h 10.0.60.3 -t "bacnet/write/command" -m '{
  "deviceId": 2020521,
  "objectType": "analog-value",
  "objectInstance": 120,
  "value": 21.5,
  "priority": 8
}'
```

## Port Allocation

- **3001**: Frontend (Discovery + Points)
- **3003**: Monitoring Dashboard
- **5434**: PostgreSQL (configuration)
- **5435**: TimescaleDB (time-series)
- **47808**: BACnet worker (protocol)

## Environment Configuration

Key variables in `.env`:
```bash
# BACnet
BACNET_IP=192.168.1.35
BACNET_PORT=47808
BACNET_DEVICE_ID=3001234

# MQTT (external broker)
MQTT_BROKER=10.0.60.3
MQTT_PORT=1883

# Databases
DATABASE_URL="postgresql://anatoli@postgres:5432/bacpipes"
TIMESCALEDB_URL="postgresql://anatoli@timescaledb:5432/timescaledb"

# System
TZ=Asia/Kuala_Lumpur
```

## Project Structure

```
BacPipes/
├── docker-compose.yml                  # Core services
├── docker-compose-monitoring.yml       # Monitoring stack
├── .env                                # Environment config
├── frontend/                           # Next.js app (port 3001)
│   ├── src/app/
│   │   ├── page.tsx                    # Dashboard
│   │   ├── discovery/                  # BACnet discovery UI
│   │   ├── points/                     # Point configuration
│   │   ├── monitoring/                 # Real-time monitoring
│   │   └── api/                        # API routes
│   └── prisma/
│       ├── schema.prisma               # Database schema
│       └── migrations/                 # Migration history
├── worker/                             # Python BACnet worker
│   ├── mqtt_publisher.py               # MQTT publishing logic
│   ├── bacnet_write_handler.py         # Write command handler
│   └── requirements.txt
├── telegraf/                           # MQTT → TimescaleDB
│   ├── Dockerfile
│   ├── mqtt_to_timescaledb.py          # Custom Python bridge
│   └── requirements.txt
├── monitoring-dashboard/               # Monitoring UI (port 3003)
│   └── src/app/
│       ├── page.tsx                    # Main dashboard
│       └── api/                        # TimescaleDB queries
├── timescaledb/
│   └── init/
│       └── 01_init.sql                 # Hypertable setup
└── MIGRATION_TO_MODULAR_ARCHITECTURE.md  # Migration history
```

## Documentation

- **MIGRATION_TO_MODULAR_ARCHITECTURE.md**: Migration from internal to external MQTT broker
- **ROADMAP.md**: Future development plans
- **ARCHITECTURE_SPLIT.md**: Service separation rationale
- **QUICK_START.md**: User-facing quick start guide

## Gitea Repository

- **URL**: http://10.0.10.2:30008/ak101/dev-bacnet-discovery-docker
- **Branch**: `development` (active)
- **Branches**:
  - `main`: Production releases
  - `development`: Active development
  - `legacy-csv-workflow`: Old CSV-based workflow

## Known Issues / Future Enhancements

See ROADMAP.md for detailed future plans.

**Immediate Improvements**:
- [ ] Add authentication to web UI
- [ ] Implement data retention policies
- [ ] Add alerting/notification system
- [ ] Support for BACnet trends and schedules
- [ ] Multi-site management interface

---

**Last Updated**: 2025-11-21
**Status**: Production-ready for single-site deployment

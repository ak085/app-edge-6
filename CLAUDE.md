# BacPipes - BACnet Discovery & MQTT Publishing Platform

## Current Status (2025-12-01)

**Production Ready**: Full-stack Docker Compose application for BACnet point discovery, configuration, and MQTT publishing with flexible MQTT broker support.

**Completed Features**:
- ✅ BACnet device/point discovery with web UI
- ✅ Haystack tagging system (8-field semantic naming)
- ✅ MQTT publishing to external broker (modular architecture)
- ✅ **Flexible MQTT broker** - Works with any broker on any network
- ✅ **Graceful degradation** - App works even without MQTT broker
- ✅ **Real-time MQTT status** - Dashboard shows connection status (🟢/🔴)
- ✅ TimescaleDB time-series storage
- ✅ BACnet write command support (priority array control)
- ✅ Site-to-remote data synchronization
- ✅ Production-optimized deployment (99.6% memory reduction)
- ✅ Bulk poll interval settings with per-point granularity

## Technology Stack

- **Frontend**: Next.js 15 (Production Build) + TypeScript + Shadcn/ui
- **Database**: PostgreSQL 15 (configuration) + TimescaleDB (time-series)
- **Worker**: Python 3.10 + BACpypes3 + paho-mqtt
- **Ingestion**: Custom Python bridge (MQTT → TimescaleDB)
- **Deployment**: Docker Compose (Production Mode)

## Architecture

```
┌─────────────────────────────────────────────┐
│ BacPipes Application (Docker Compose)       │
├─────────────────────────────────────────────┤
│  Frontend (Next.js) - Port 3001             │
│  ├─ Discovery                               │
│  ├─ Points (Haystack tagging)               │
│  ├─ Monitoring                              │
│  └─ Settings                                │
│                                             │
│  PostgreSQL - Port 5434                     │
│  └─ Devices, Points, Config                 │
│                                             │
│  BACnet Worker (Python/BACpypes3)           │
│  ├─ Polls BACnet devices                    │
│  ├─ Publishes to MQTT                       │
│  ├─ Auto-reconnects if disconnected         │
│  └─ Handles write commands                  │
│                                             │
│  TimescaleDB - Port 5435                    │
│  └─ sensor_readings (hypertable)            │
│                                             │
│  Telegraf (MQTT → TimescaleDB)              │
│  └─ Data ingestion bridge                   │
│                                             │
└─────────────────────────────────────────────┘
                  ↓ MQTT publish
┌─────────────────────────────────────────────┐
│ External MQTT Broker (Configurable)         │
│ - Default: 10.0.60.3:1883                   │
│ - Configurable via Settings GUI             │
│ - Can be any broker on any network          │
│ - Supports MQTT bridging to remote sites    │
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

### 3. MQTT Publishing (Enhanced)
- **Flexible broker configuration** - Works with any MQTT broker on any network
- Configurable via Settings GUI (no code changes needed)
- **Graceful degradation** - App starts successfully even if broker unreachable
- **Auto-reconnection** - Retries connection every 5 seconds if disconnected
- **Real-time status** - Dashboard shows 🟢 Connected / 🔴 Disconnected
- Minute-aligned polling for synchronized timestamps
- JSON payloads with full metadata
- QoS 1 (at least once delivery)
- Write command support via `bacnet/write/command` topic

### 4. Time-Series Storage
- TimescaleDB hypertable (`sensor_readings`)
- Automatic compression and retention policies
- Indexed on `time DESC` for fast queries
- Haystack name + display name for semantic queries
- Easy cleanup commands (see README.md)
- Data accessible via SQL queries

## Quick Start

```bash
# Clone repository
git clone http://10.0.10.2:30008/ak101/app-bacnet-local.git
cd BacPipes

# Configure environment
cp .env.example .env
nano .env  # Edit BACNET_IP and MQTT_BROKER

# Deploy
docker compose up -d
docker compose -f docker-compose-monitoring.yml up -d

# Access UI
# Discovery/Configuration: http://192.168.1.35:3001
```

## Common Commands

### Service Management
```bash
# Start all services
docker compose up -d
docker compose -f docker-compose-monitoring.yml up -d

# Stop all services
docker compose down
docker compose -f docker-compose-monitoring.yml down

# Restart worker (e.g., after MQTT config change)
docker compose restart bacnet-worker

# View logs
docker compose logs -f bacnet-worker
docker compose -f docker-compose-monitoring.yml logs -f telegraf

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

### Data Management
```bash
# Clean time-series data (stop telegraf first)
docker compose -f docker-compose-monitoring.yml stop telegraf

# Delete all time-series data
docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c "TRUNCATE sensor_readings;"

# Delete recent bad data (last 2 hours)
docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c "
  DELETE FROM sensor_readings WHERE time > NOW() - INTERVAL '2 hours';
"

# Restart telegraf
docker compose -f docker-compose-monitoring.yml start telegraf

# Complete reset (deletes all data including configuration)
docker compose down -v
docker compose -f docker-compose-monitoring.yml down -v
```

### MQTT Testing
```bash
# Subscribe to all topics
mosquitto_sub -h <broker-ip> -t "bacnet/#" -v

# Publish write command
mosquitto_pub -h <broker-ip> -t "bacnet/write/command" -m '{
  "deviceId": 2020521,
  "objectType": "analog-value",
  "objectInstance": 120,
  "value": 21.5,
  "priority": 8
}'
```

## Configuration

### MQTT Broker Setup
1. Navigate to Settings page (http://your-ip:3001/settings)
2. Enter MQTT Broker IP (can be any broker on any network)
3. Save settings
4. Restart worker: `docker compose restart bacnet-worker`
5. Check dashboard for 🟢 connection status

**Note:** Worker only loads MQTT configuration at startup. After changing broker settings, restart is required.

### Environment Variables
Key variables in `.env`:
```bash
# BACnet
BACNET_IP=192.168.1.35        # Your local IP on BACnet network
BACNET_PORT=47808              # Standard BACnet/IP port
BACNET_DEVICE_ID=3001234       # Unique device ID

# MQTT (external broker - configurable in GUI)
MQTT_BROKER=10.0.60.3          # Default, change in Settings
MQTT_PORT=1883                 # Standard MQTT port

# Databases
DATABASE_URL="postgresql://anatoli@postgres:5432/bacpipes"
TIMESCALEDB_URL="postgresql://anatoli@timescaledb:5432/timescaledb"

# System
TZ=Asia/Kuala_Lumpur           # Timezone for timestamps
NODE_ENV=production            # production or development
```

## Port Allocation

- **3001**: Frontend (Discovery + Points + Settings + Monitoring)
- **5434**: PostgreSQL (configuration)
- **5435**: TimescaleDB (time-series)
- **47808**: BACnet worker (protocol)

## Project Structure

```
BacPipes/
├── docker-compose.yml                  # Core services
├── docker-compose-monitoring.yml       # Monitoring stack
├── .env                                # Environment config
├── README.md                           # Complete user guide
├── CLAUDE.md                           # This file (AI context)
│
├── frontend/                           # Next.js app (port 3001)
│   ├── src/app/
│   │   ├── page.tsx                    # Dashboard
│   │   ├── discovery/                  # BACnet discovery UI
│   │   ├── points/                     # Point configuration
│   │   ├── monitoring/                 # Real-time monitoring
│   │   ├── settings/                   # System settings
│   │   └── api/                        # API routes
│   └── prisma/
│       ├── schema.prisma               # Database schema
│       └── migrations/                 # Migration history
│
├── monitoring-dashboard/               # Monitoring UI (port 3003)
│   └── src/app/
│       ├── page.tsx                    # Main dashboard
│       └── api/                        # TimescaleDB queries
│
├── worker/                             # Python BACnet worker
│   ├── mqtt_publisher.py               # MQTT publishing logic
│   ├── config.py                       # Configuration
│   └── requirements.txt
│
├── telegraf/                           # MQTT → TimescaleDB
│   ├── mqtt_to_timescaledb.py          # Custom Python bridge
│   └── requirements.txt
│
└── timescaledb/
    └── init/
        └── 01_init.sql                 # Hypertable setup
```

## Recent Updates

### 2025-12-07: Monitoring Dashboard Removal & BACnet Discovery Fix

**Monitoring Dashboard Removed** - Redundant visualization service
- Removed `monitoring-dashboard` service from `docker-compose-monitoring.yml`
- Deleted `monitoring-dashboard/` directory
- TimescaleDB and Telegraf remain operational for data storage
- Historical data accessible via SQL queries
- Port 3003 no longer in use

**BACnet Discovery Fixed** - Missing discovery files in worker container
- Root cause: Dockerfile only copied `mqtt_publisher.py`, missing `discovery.py` and `job_processor.py`
- Updated Dockerfile to `COPY . .` (all worker files)
- Updated CMD to run both job processor and MQTT publisher concurrently
- Discovery now working: 2 devices, 50 points found
- Impact: Discovery feature restored after ~1 month outage

---

### 2025-12-06: Cleanup of Legacy Services & Code

**Major Cleanup: Removed Unused Services and Legacy Code**

#### Services Removed:
1. **Grafana** - Legacy visualization service
   - Removed from `docker-compose-monitoring.yml`
   - Removed environment variables from `.env.example`
   - Stopped and removed running container
   - Deleted Docker volumes (~500MB freed)
   - Removed `grafana/` directory

2. **Orphaned MQTT Broker Container** - Internal broker no longer used
   - Container `mqtt-broker-local` was running but not defined in compose files
   - Leftover from migration to external MQTT broker architecture
   - Removed container and 10+ associated Docker volumes
   - Freed ~500MB disk space

3. **InfluxDB Integration** - Abandoned optional feature
   - Removed `InfluxConfig` model from Prisma schema
   - Removed InfluxDB seeding from seed file
   - Removed `influxdb-client` Python package from worker requirements
   - Removed environment variables from `.env` and `.env.example`
   - Dropped `InfluxConfig` table from database
   - Current architecture uses TimescaleDB exclusively

4. **Docker Infrastructure Cleanup**
   - Removed orphaned network: `bacpipes_remote-db-network`
   - Removed 10+ orphaned MQTT volumes
   - Total disk space freed: ~500MB

#### Code Fixes:
- **Frontend MQTT Broker Resolution** - Fixed hardcoded `mqtt-broker` service references
  - Updated `frontend/src/app/api/monitoring/stream/route.ts`
  - Updated `frontend/src/app/api/bacnet/write/route.ts`
  - Localhost now explicitly not supported (throws clear error message)
  - Frontend requires external broker IP addresses only (e.g., 10.0.60.3)

#### Impact:
- **1 fewer running container** (from 7 to 6)
- **500MB+ disk space freed**
- **Cleaner codebase** (removed dead code and unused models)
- **Better error messages** for localhost broker misconfiguration
- **Simplified architecture** (external MQTT only, no legacy code paths)

---

### 2025-12-01: MQTT Broker Flexibility & Graceful Degradation

**Major Enhancement: Flexible MQTT Architecture**

#### Changes Made:
1. **Standardized Default MQTT Broker IP** (`10.0.60.3`)
   - Updated across all files: `.env`, `.env.example`, `schema.prisma`, `worker/mqtt_publisher.py`, `worker/config.py`
   - Consistent defaults ensure predictable first-time behavior
   - Fully configurable via Settings GUI

2. **Graceful MQTT Connection Handling**
   - Worker starts successfully even if MQTT broker unreachable
   - Shows clear warnings when broker unavailable
   - BACnet discovery and point configuration work without MQTT
   - Auto-reconnects every 5 seconds if broker becomes available
   - No more startup failures due to MQTT issues

3. **Real-Time MQTT Status in Dashboard**
   - Dashboard API now includes `mqttConnected` and `mqttConfigured` flags
   - Frontend displays connection status with visual indicators:
     - 🟢 Green pulsing dot + "Connected" (when active)
     - 🔴 Red dot + "Disconnected" (when inactive)
     - Warning message if broker not configured
   - System status reflects MQTT health:
     - `error`: MQTT not configured
     - `degraded`: No points enabled OR no recent data
     - `operational`: All systems working

4. **Code Changes Summary:**
   - `worker/mqtt_publisher.py:195-222` - Graceful connection handling
   - `worker/mqtt_publisher.py:242-259` - Auto-reconnection logic
   - `worker/mqtt_publisher.py:929-931` - Main loop reconnection check
   - `frontend/src/app/api/dashboard/summary/route.ts:113-153` - MQTT status detection
   - `frontend/src/app/page.tsx:22-29,277-311` - Visual status indicator

#### Behavior:
- **Fresh Install:** App starts with default broker IP (10.0.60.3), shows disconnected status, user can configure in Settings
- **After Configuration:** User changes broker IP → saves → restarts worker → auto-connects
- **If Broker Goes Down:** Worker detects disconnection → retries every 5 seconds → auto-reconnects when available

#### Configuration Priority:
1. **Database settings** (from Settings GUI) - Source of truth
2. Environment variables (`.env` file) - Fallback
3. Hardcoded defaults - Last resort

**Documentation Cleanup:**
- Removed legacy docs (doc/, MQTT_BRIDGE_SETUP.md, ROADMAP.md)
- Consolidated to README.md (comprehensive user guide) + CLAUDE.md (this file)
- README.md now includes detailed deployment, operations, data management, and troubleshooting sections

### 2025-11-30: MQTT Polling Behavior & Dashboard Fixes

#### MQTT Publishing Architecture
- **Polling Strategy**: Worker checks enabled points every 5 seconds
  - Each point has individual `pollInterval` setting (configurable per-point)
  - Points poll when `current_time - last_poll >= pollInterval`
  - Example: 11 points with 30s interval → 11 messages every 30s
- **Important**: Points with identical intervals poll simultaneously
  - Creates synchronized bursts (not continuous streaming)
  - This is **by design** for minute-aligned timestamps
  - MQTT broker may show cumulative message counts (not real-time rate)
- **Database Polling**: Worker queries database every 5 seconds to check point configurations
  - Allows dynamic reconfiguration without restart
  - Future optimization: Cache points and reload only on config changes

#### Dashboard Request Handling
- **Fixed**: "[Request interrupted by user]" error in browser console
  - Implemented proper AbortController for fetch requests
  - Gracefully cancels pending requests when component unmounts
  - Auto-refresh (10s interval) no longer causes race conditions
- **Behavior**: Dashboard polls `/api/dashboard/summary` every 10 seconds
  - Shows system status, device stats, and recent point values
  - Properly handles cleanup on unmount or auto-refresh toggle

### 2025-11-24: Performance & Stability

#### Production Build
- **Memory Optimization**: Frontend runs in production mode
  - Memory usage reduced from 14.7GB to 62MB (99.6% reduction)
  - Startup time: 417ms (production) vs 3-5s (development)
  - No more memory leaks or frozen web app

#### Monitoring Page Fixes
- **SSE Connection Stability**: Fixed SSE reconnection issue causing duplicate points
- **Clear Button**: Fixed auto-pause behavior when clearing display
- **Operational Topics**: Filtered `bacnet/write/*` topics from monitoring display

#### Settings Page Fixes
- **Bulk Poll Interval**: Fixed "Failed to apply bulk poll interval" error
  - Regenerated Prisma client to sync with database schema
  - Apply button now successfully updates all MQTT-enabled points

## Documentation

- **README.md** - Complete user guide with deployment instructions, troubleshooting, data management
- **CLAUDE.md** - This file, AI development context and project status
- **Git History** - All changes, migrations, and feature implementations

For detailed deployment instructions, see README.md.

## Repository

- **Gitea**: http://10.0.10.2:30008/ak101/app-bacnet-local.git
- **Branch**: `development` (active development)
- **Branch**: `main` (production releases)

---

**Last Updated**: 2025-12-07
**Status**: Production-ready for single-site deployment with flexible MQTT broker support

# BacPipes - BACnet to MQTT Edge Data Collection

**Production-ready BACnet-to-MQTT bridge with web-based configuration and remote monitoring**

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](docker-compose.yml)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.10-yellow?logo=python)](https://www.python.org/)

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Detailed Installation Guide](#detailed-installation-guide)
- [Configuration](#configuration)
- [Common Operations](#common-operations)
- [Data Management](#data-management)
- [Monitoring & Dashboards](#monitoring--dashboards)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## Quick Start

**For experienced users who know Docker Compose**

### Prerequisites
- ✅ Docker & Docker Compose installed
- ✅ 4GB RAM minimum (8GB recommended)
- ✅ Linux host (Ubuntu/Debian recommended)
- ✅ Network access to BACnet devices (UDP port 47808)
- ✅ MQTT broker accessible (or configure after deployment)

### Deploy in 60 Seconds

```bash
# 1. Clone repository
git clone http://10.0.10.2:30008/ak101/app-bacnet-local.git
cd BacPipes

# 2. Configure environment
cp .env.example .env
nano .env  # Edit BACNET_IP and MQTT_BROKER

# 3. Deploy
docker compose up -d
docker compose -f docker-compose-monitoring.yml up -d

# 4. Access UI
# Discovery & Config: http://<your-ip>:3001
```

### Common Commands

| Operation | Command |
|-----------|---------|
| **Start all services** | `docker compose up -d && docker compose -f docker-compose-monitoring.yml up -d` |
| **Stop all services** | `docker compose down && docker compose -f docker-compose-monitoring.yml down` |
| **Restart worker** | `docker compose restart bacnet-worker` |
| **View logs** | `docker compose logs -f bacnet-worker` |
| **Clean time-series data** | See [Data Management](#data-management) |
| **Complete reset** | `docker compose down -v && docker compose -f docker-compose-monitoring.yml down -v` |

### First-Time Workflow

1. **Configure Settings** → http://localhost:3001/settings
   - Set BACnet IP (your local IP on BACnet network)
   - Set MQTT Broker IP (external broker or 10.0.60.3 default)
   - **Restart worker:** `docker compose restart bacnet-worker`

2. **Discover Devices** → http://localhost:3001/discovery
   - Click "Start Discovery"
   - Save discovered devices

3. **Tag Points** → http://localhost:3001/points
   - Select points → Add Haystack tags
   - Enable "Publish to MQTT"
   - Set poll intervals

4. **Monitor Data** → http://localhost:3001/monitoring
   - Real-time MQTT stream
   - Dashboard: http://localhost:3003

---

## Architecture Overview

### System Components

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
│  └─ Handles write commands                  │
│                                             │
│  TimescaleDB - Port 5435                    │
│  └─ Time-series storage                     │
│                                             │
│  Telegraf (MQTT → TimescaleDB)              │
│  └─ Data ingestion bridge                   │
└─────────────────────────────────────────────┘
                  ↓ MQTT publish
┌─────────────────────────────────────────────┐
│ External MQTT Broker (10.0.60.3:1883)       │
│ - Configurable via Settings GUI             │
│ - Can be any broker on any network          │
│ - Supports MQTT bridging to remote sites    │
└─────────────────────────────────────────────┘
```

### Key Features

- 🔍 **BACnet Discovery** - Automatic network scanning and device detection
- 🏷️ **Haystack Tagging** - Industry-standard semantic naming (8-field structure)
- 📡 **MQTT Publishing** - Real-time data streaming with configurable intervals
- ⚙️ **Flexible MQTT** - Works with any MQTT broker on any network
- 📊 **Real-time Monitoring** - Live point values on main dashboard
- ✏️ **BACnet Write** - Remote control with priority array support
- ⏱️ **TimescaleDB** - Time-series data storage with automatic compression
- 🐳 **Docker Compose** - Production-optimized deployment
- 🔄 **Graceful Degradation** - App works even if MQTT broker unavailable

---

## Detailed Installation Guide

### System Requirements

**Hardware:**
- CPU: 2 cores minimum (4 cores recommended)
- RAM: 4GB minimum (8GB recommended for monitoring stack)
- Disk: 20GB minimum (depends on data retention)

**Software:**
- Operating System: Linux (Ubuntu 22.04+ or Debian 11+ recommended)
- Docker Engine: 24.0+
- Docker Compose: 2.20+

**Network:**
- BACnet/IP network access (UDP port 47808)
- MQTT broker (local or remote)
- Outbound internet access (for Docker image pulls)

### Step 1: Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### Step 2: Clone Repository

```bash
# Clone from Gitea
git clone http://10.0.10.2:30008/ak101/app-bacnet-local.git BacPipes
cd BacPipes

# Check branch
git branch -a
git checkout development  # or main for production
```

### Step 3: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Settings:**

```bash
# BACnet Configuration
BACNET_IP=192.168.1.35        # YOUR local IP on BACnet network
BACNET_PORT=47808              # Standard BACnet/IP port
BACNET_DEVICE_ID=3001234       # Unique device ID

# MQTT Broker
MQTT_BROKER=10.0.60.3          # YOUR MQTT broker IP
MQTT_PORT=1883                 # Standard MQTT port

# System
TZ=Asia/Kuala_Lumpur           # YOUR timezone
NODE_ENV=production            # production or development
```

### Step 4: Deploy Services

```bash
# Start core services (discovery, polling, MQTT publishing)
docker compose up -d

# Start monitoring stack (TimescaleDB, dashboard)
docker compose -f docker-compose-monitoring.yml up -d

# Check status
docker compose ps
docker compose -f docker-compose-monitoring.yml ps

# View logs
docker compose logs -f
```

### Step 5: Initial Configuration

**1. Access Web UI:**
```bash
# Discovery & Configuration
http://192.168.1.35:3001
```

**2. Configure System Settings:**
- Navigate to **Settings** page
- Verify/update BACnet IP address
- Configure MQTT broker IP (must match your network)
- Set timezone
- Save settings
- **Restart worker:** `docker compose restart bacnet-worker`

**3. Discover BACnet Devices:**
- Go to **Discovery** page
- Click "Start Discovery"
- Wait for scan to complete (~30 seconds)
- Review discovered devices and points
- Click "Save All Devices" or selectively save

**4. Configure Points:**
- Go to **Points** page
- Select points to configure
- Add Haystack tags:
  - Site ID (e.g., `klcc`, `menara`)
  - Equipment Type (e.g., `ahu`, `vav`, `chiller`)
  - Equipment ID (e.g., `12`, `north-wing`)
  - Point Function (e.g., `sensor`, `sp`, `cmd`)
- Enable "Publish to MQTT"
- Set poll interval (seconds)
- Save changes

**5. Verify Data Flow:**
- Check **Monitoring** page for real-time data
- Check **Dashboard** for MQTT connection status (🟢 = connected)
- Verify MQTT broker receives data:
  ```bash
  mosquitto_sub -h <broker-ip> -t "bacnet/#" -v
  ```

---

## Configuration

### MQTT Broker Setup

**Important:** BacPipes requires an **external MQTT broker**. The broker can be:
- On the same network (e.g., `192.168.1.100`)
- On a different network (e.g., `10.0.60.3`)
- A cloud MQTT service

**Configure via GUI:**
1. Settings page → MQTT Broker IP
2. Save settings
3. Restart worker: `docker compose restart bacnet-worker`

**MQTT Connection Status:**
- Dashboard shows 🟢 Green = Connected
- Dashboard shows 🔴 Red = Disconnected (check broker IP in Settings)

**Graceful Degradation:**
- App starts successfully even if MQTT broker unreachable
- BACnet discovery and configuration work without MQTT
- Worker auto-reconnects when broker becomes available (every 5 seconds)

### Haystack Tagging System

BacPipes uses an 8-field semantic naming structure:

```
{site}.{equip}.{equipRef}.{point}.{measurement}.{substance}.{condition}.{descriptor}
```

**Example:**
```
klcc.ahu.12.sensor.temp.air.supply.actual
└─┬─┘ └┬┘ └┬┘ └──┬──┘ └─┬─┘ └┬─┘ └──┬──┘ └──┬──┘
Site Equip ID Function Qty  Subj  Loc    Desc
```

**MQTT Topics Auto-Generated:**
```
bacnet/klcc/ahu_12/sensor/temp/air/supply/actual/presentValue
```

### Poll Intervals

- **Per-Point Configuration:** Each point has individual poll interval (1-3600 seconds)
- **Bulk Update:** Settings page → Set default interval → Apply to all MQTT-enabled points
- **Worker Behavior:** Checks points every 5 seconds, polls only if interval elapsed
- **Minute-Aligned:** New points initialize to poll at next minute boundary

---

## Common Operations

### Start Services

```bash
# Start core services
docker compose up -d

# Start monitoring stack
docker compose -f docker-compose-monitoring.yml up -d

# Start specific service
docker compose start bacnet-worker
```

### Stop Services

```bash
# Stop all services (data preserved in volumes)
docker compose down
docker compose -f docker-compose-monitoring.yml down

# Stop specific service
docker compose stop bacnet-worker
```

### Restart Services

```bash
# Restart worker (e.g., after MQTT config change)
docker compose restart bacnet-worker

# Restart frontend
docker compose restart frontend

# Restart all
docker compose restart
```

### View Logs

```bash
# Follow all logs
docker compose logs -f

# Follow specific service
docker compose logs -f bacnet-worker
docker compose logs -f frontend

# Last 100 lines
docker compose logs --tail=100 bacnet-worker

# Monitoring stack logs
docker compose -f docker-compose-monitoring.yml logs -f telegraf
```

### Update Application

```bash
# Pull latest changes
git pull origin development

# Rebuild and restart
docker compose down
docker compose up -d --build

# Same for monitoring
docker compose -f docker-compose-monitoring.yml down
docker compose -f docker-compose-monitoring.yml up -d --build
```

---

## Data Management

### Database Access

**PostgreSQL (Configuration Database):**
```bash
# Connect to database
docker exec -it bacpipes-postgres psql -U anatoli -d bacpipes

# List tables
\dt

# Query devices
SELECT "deviceId", "deviceName", "ipAddress" FROM "Device";

# Query points
SELECT COUNT(*) FROM "Point" WHERE "mqttPublish" = true;

# Exit
\q
```

**TimescaleDB (Time-Series Data):**
```bash
# Connect to database
docker exec -it bacpipes-timescaledb psql -U anatoli -d timescaledb

# Check data volume
SELECT COUNT(*) FROM sensor_readings;

# Recent data
SELECT time, haystack_name, dis, value
FROM sensor_readings
WHERE time > NOW() - INTERVAL '1 hour'
ORDER BY time DESC
LIMIT 20;

# Exit
\q
```

### Clean Time-Series Data

**Stop data ingestion first:**
```bash
docker compose -f docker-compose-monitoring.yml stop telegraf
```

**Option 1: Delete All Data (Fresh Start)**
```bash
docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c "TRUNCATE sensor_readings;"
```

**Option 2: Delete Recent Bad Data**
```bash
# Delete last 2 hours
docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c "
  DELETE FROM sensor_readings WHERE time > NOW() - INTERVAL '2 hours';
"

# Delete by haystack pattern
docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c "
  DELETE FROM sensor_readings WHERE haystack_name LIKE 'bad_site%';
"
```

**Option 3: Set Retention Policy (Auto-Cleanup)**
```bash
docker exec -it bacpipes-timescaledb psql -U anatoli -d timescaledb

# Keep only last 7 days
SELECT add_retention_policy('sensor_readings', INTERVAL '7 days');

# Keep last 30 days
SELECT add_retention_policy('sensor_readings', INTERVAL '30 days');

\q
```

**Restart data ingestion:**
```bash
docker compose -f docker-compose-monitoring.yml start telegraf
```

### Data Persistence

**What persists across restarts:**
- ✅ All discovered devices and points (PostgreSQL volume)
- ✅ Configuration settings (PostgreSQL volume)
- ✅ Historical sensor data (TimescaleDB volume)
- ✅ Haystack tags and MQTT topics (PostgreSQL volume)

**What is preserved:**
| Operation | PostgreSQL | TimescaleDB |
|-----------|------------|-------------|
| `docker compose restart` | ✅ Kept | ✅ Kept |
| `docker compose down && up` | ✅ Kept | ✅ Kept |
| `docker compose down -v` | ❌ **DELETED** | ❌ **DELETED** |

**⚠️ Warning:** Never use `-v` flag unless you want to wipe all data!

### Complete Reset

**Delete all data and start fresh:**
```bash
# Stop all services and delete volumes
docker compose down -v
docker compose -f docker-compose-monitoring.yml down -v

# Verify volumes deleted
docker volume ls | grep bacpipes

# Restart fresh
docker compose up -d
docker compose -f docker-compose-monitoring.yml up -d
```

---

## Monitoring & Dashboards

### Dashboard (Port 3001)

**Main Operations Dashboard:**
- URL: `http://<your-ip>:3001`
- Real-time system status
- Device statistics
- MQTT connection status (🟢/🔴)
- Recent point values

**Pages:**
- `/` - Operations dashboard
- `/discovery` - BACnet device discovery
- `/points` - Point configuration and tagging
- `/monitoring` - Real-time MQTT stream
- `/settings` - System configuration

### MQTT Monitoring

**Subscribe to all topics:**
```bash
mosquitto_sub -h <broker-ip> -t "bacnet/#" -v
```

**Publish write command:**
```bash
mosquitto_pub -h <broker-ip> -t "bacnet/write/command" -m '{
  "deviceId": 2020521,
  "objectType": "analog-value",
  "objectInstance": 120,
  "value": 21.5,
  "priority": 8
}'
```

### Database Queries

**Active publishing points:**
```bash
docker exec bacpipes-postgres psql -U anatoli -d bacpipes -c "
  SELECT COUNT(*) FROM \"Point\" WHERE \"mqttPublish\" = true AND enabled = true;
"
```

**Poll interval distribution:**
```bash
docker exec bacpipes-postgres psql -U anatoli -d bacpipes -c "
  SELECT \"pollInterval\", COUNT(*) as count
  FROM \"Point\"
  WHERE \"mqttPublish\" = true
  GROUP BY \"pollInterval\"
  ORDER BY \"pollInterval\";
"
```

**Recent sensor readings:**
```bash
docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c "
  SELECT time, haystack_name, value
  FROM sensor_readings
  WHERE time > NOW() - INTERVAL '5 minutes'
  ORDER BY time DESC
  LIMIT 10;
"
```

---

## Troubleshooting

### Worker Won't Start

**Symptoms:** Worker container exits immediately

**Solutions:**
```bash
# Check logs
docker compose logs bacnet-worker

# Common issues:
# 1. Database not ready
docker compose ps postgres  # Should be "healthy"

# 2. BACnet port conflict
sudo netstat -tulpn | grep 47808

# 3. Restart worker
docker compose restart bacnet-worker
```

### MQTT Not Connected (🔴 Red)

**Symptoms:** Dashboard shows disconnected, no data in monitoring

**Solutions:**
1. **Verify MQTT broker IP:**
   - Settings page → Check MQTT Broker field
   - Ping broker: `ping <broker-ip>`
   - Check broker running: `mosquitto_sub -h <broker-ip> -t test`

2. **Fix configuration:**
   - Update broker IP in Settings
   - Save settings
   - Restart worker: `docker compose restart bacnet-worker`

3. **Check worker logs:**
   ```bash
   docker compose logs bacnet-worker | grep MQTT
   # Look for: "✅ Connected to MQTT broker"
   # Or: "⚠️ MQTT broker unreachable"
   ```

### No Data in TimescaleDB

**Symptoms:** No time-series data being stored

**Solutions:**
1. **Check Telegraf logs:**
   ```bash
   docker compose -f docker-compose-monitoring.yml logs telegraf
   # Should show: "✅ Saved to TimescaleDB"
   ```

2. **Verify MQTT data flow:**
   ```bash
   mosquitto_sub -h <broker-ip> -t "bacnet/#" -v
   # Should see JSON messages
   ```

3. **Check TimescaleDB:**
   ```bash
   docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -c "
     SELECT COUNT(*) FROM sensor_readings;
   "
   # Should show row count > 0
   ```

4. **Restart Telegraf:**
   ```bash
   docker compose -f docker-compose-monitoring.yml restart telegraf
   ```

### BACnet Discovery Fails

**Symptoms:** Discovery finds no devices

**Solutions:**
1. **Check network connectivity:**
   ```bash
   # From host machine
   ping <bacnet-device-ip>
   ```

2. **Verify BACnet IP configuration:**
   - Settings page → BACnet IP must match your local network interface
   - Find correct IP: `ip addr show` or `ifconfig`
   - Update if wrong, restart worker

3. **Check firewall:**
   ```bash
   # Allow BACnet/IP (UDP 47808)
   sudo ufw allow 47808/udp
   ```

4. **Check worker logs:**
   ```bash
   docker compose logs bacnet-worker | grep "Discovery"
   ```

### High Memory Usage

**Symptoms:** System running slow, OOM errors

**Solutions:**
1. **Check container stats:**
   ```bash
   docker stats
   ```

2. **Ensure production mode:**
   ```bash
   # .env file should have:
   NODE_ENV=production
   ```

3. **Clean old data:**
   ```bash
   # Set retention policy (keep 7 days)
   docker exec -it bacpipes-timescaledb psql -U anatoli -d timescaledb
   SELECT add_retention_policy('sensor_readings', INTERVAL '7 days');
   \q
   ```

4. **Reduce poll frequency:**
   - Settings page → Increase default poll interval
   - Apply to all points

### Permission Denied Errors

**Symptoms:** Cannot delete files, access denied

**Solutions:**
```bash
# Fix ownership
sudo chown -R $USER:$USER /path/to/BacPipes

# Fix permissions
chmod -R u+w /path/to/BacPipes
```

---

## Development

### Project Structure

```
BacPipes/
├── docker-compose.yml                  # Core services
├── docker-compose-monitoring.yml       # Monitoring stack
├── .env                                # Environment config
├── README.md                           # This file
├── CLAUDE.md                           # AI development context
│
├── frontend/                           # Next.js 15 app (port 3001)
│   ├── src/app/
│   │   ├── page.tsx                    # Dashboard
│   │   ├── discovery/                  # BACnet discovery
│   │   ├── points/                     # Point configuration
│   │   ├── monitoring/                 # Real-time monitoring
│   │   ├── settings/                   # System settings
│   │   └── api/                        # API routes
│   └── prisma/
│       ├── schema.prisma               # Database schema
│       └── migrations/                 # Migration history
│
├── worker/                             # Python BACnet worker
│   ├── mqtt_publisher.py               # Main polling loop
│   ├── config.py                       # Configuration
│   └── requirements.txt
│
├── telegraf/                           # MQTT → TimescaleDB
│   ├── mqtt_to_timescaledb.py          # Python bridge
│   └── requirements.txt
│
└── timescaledb/
    └── init/
        └── 01_init.sql                 # Hypertable setup
```

### Database Schema

**PostgreSQL (Configuration):**
- `Device` - BACnet devices
- `Point` - BACnet points with Haystack tags
- `SystemSettings` - BACnet IP, timezone, poll intervals
- `MqttConfig` - MQTT broker settings
- `WriteHistory` - Write command audit trail

**TimescaleDB (Time-Series):**
- `sensor_readings` - Hypertable for all sensor data
  - Columns: `time`, `haystack_name`, `dis`, `value`, `units`, `device_id`, `object_type`, `object_instance`
  - Indexed on `time DESC` for fast queries
  - Compressed with retention policies

### API Endpoints

**Discovery:**
- `POST /api/discovery/start` - Start BACnet discovery
- `POST /api/discovery/save` - Save discovered devices

**Points:**
- `GET /api/points` - List all points
- `PUT /api/points/:id` - Update point configuration
- `POST /api/points/bulk-poll-interval` - Update all intervals

**Dashboard:**
- `GET /api/dashboard/summary` - System status and statistics

**Settings:**
- `GET /api/settings` - Get system settings
- `PUT /api/settings` - Update system settings

**Monitoring:**
- `GET /api/monitoring/stream` - Server-sent events for real-time data

### Environment Variables

See `.env.example` for full reference.

**Core:**
- `BACNET_IP` - Local IP on BACnet network
- `BACNET_PORT` - BACnet/IP port (default: 47808)
- `MQTT_BROKER` - MQTT broker IP
- `MQTT_PORT` - MQTT port (default: 1883)
- `TZ` - Timezone for timestamps

**Database:**
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_DB` - PostgreSQL database name
- `DATABASE_URL` - PostgreSQL connection string

---

## Port Allocation

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3001 | Web UI (discovery, points, settings, monitoring) |
| PostgreSQL | 5434 | Configuration database |
| TimescaleDB | 5435 | Time-series database |
| BACnet Worker | 47808 | BACnet/IP protocol |

---

## Support & Documentation

**Documentation:**
- This README.md - Complete user guide
- CLAUDE.md - AI development context
- Git history - All changes and migrations

**Repository:**
- Gitea: http://10.0.10.2:30008/ak101/app-bacnet-local.git
- Branch: `development` (active development)
- Branch: `main` (production releases)

**Logging:**
```bash
# View all logs
docker compose logs -f

# Worker logs (BACnet + MQTT)
docker compose logs -f bacnet-worker

# Frontend logs
docker compose logs -f frontend

# Monitoring logs
docker compose -f docker-compose-monitoring.yml logs -f
```

---

## License

Proprietary - Internal use only

---

**Last Updated:** 2025-12-01
**Version:** 1.0.0
**Status:** Production-ready for single-site deployment

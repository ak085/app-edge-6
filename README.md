# BacPipes - BACnet-to-MQTT Data Pipeline

**Production-ready BMS data collection platform for multi-site building automation**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](docker-compose.yml)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.10-yellow?logo=python)](https://www.python.org/)

---

## Overview

BacPipes is a distributed BACnet-to-MQTT data pipeline designed for enterprise building management systems (BMS). It enables:

- 🏢 **Multi-site data collection** from 100s-1000s of buildings
- 📊 **Real-time monitoring** with Grafana dashboards
- 🤖 **ML-powered optimization** (edge inference, centralized training)
- 🔒 **Secure, encrypted replication** between sites and central servers
- 📡 **Resilient architecture** (works offline, auto-recovery)
- 🐳 **Docker Compose deployment** (single command setup)

### Current Status

- ✅ **M1: Foundation** - Docker Compose, PostgreSQL, Prisma ORM
- ✅ **M2: BACnet Discovery** - Web UI for network scanning, device/point discovery
- ✅ **M3: Point Configuration** - Haystack tagging, MQTT topic generation
- ✅ **M4: MQTT Publishing** - Real-time data publishing with per-point intervals
- ✅ **M5: Monitoring Dashboard** - Real-time point values, batch publishing controls
- 🚧 **M6: Time-Series Storage** - TimescaleDB integration (planned)
- ⏳ **M7: Central Replication** - PostgreSQL logical replication (planned)

See [STRATEGIC_PLAN.md](STRATEGIC_PLAN.md) for full roadmap.

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB RAM minimum (8GB recommended)
- Linux (Ubuntu/Debian) or macOS
- Network access to BACnet devices

### Installation

```bash
# Clone repository
git clone https://gitea.yourserver.com/user/bacpipes.git
cd BacPipes

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env

# Start all services
docker compose up -d

# View logs
docker compose logs -f bacnet-worker

# Open web UI
open http://localhost:3001
```

### First-Time Setup

1. **Configure Network Settings**
   - Navigate to http://localhost:3001/settings
   - Enter your local BACnet IP address
   - Configure MQTT broker (default: 10.0.60.2:1883)
   - Set timezone for your site

2. **Discover BACnet Devices**
   - Go to http://localhost:3001/discovery
   - Click "Start Discovery"
   - Wait for scan to complete (~30 seconds)
   - Review discovered devices and points

3. **Tag Points with Haystack**
   - Go to http://localhost:3001/points
   - Select points to configure
   - Add site ID, equipment type, equipment ID
   - MQTT topics auto-generate from tags
   - Enable "Publish to MQTT"

4. **Verify Data Flow**
   - Subscribe to MQTT broker: `mosquitto_sub -h 10.0.60.2 -t "#" -v`
   - Check logs: `docker compose logs -f bacnet-worker`
   - Monitor dashboard: http://localhost:3001

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│               SITE (Docker Compose Stack)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐       │
│  │PostgreSQL├─→│ Next.js UI   ├─→│ BacPipes Worker│       │
│  │(Config DB)│  │(Web GUI)     │  │(Python+BACpy3) │       │
│  └──────────┘  └──────────────┘  └───────┬────────┘       │
│                                           │                 │
│                                           ↓                 │
│                                   ┌───────────────┐        │
│                                   │ MQTT Broker   │        │
│                                   │(Mosquitto)    │        │
│                                   └───────┬───────┘        │
│                                           │                 │
│         ┌─────────────────────────────────┘                │
│         │                                                   │
│         ↓                                                   │
│  ┌────────────────┐                                        │
│  │ BACnet Devices │ ← DDCs, Controllers, Sensors          │
│  └────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

**Future Architecture** (See [STRATEGIC_PLAN.md](STRATEGIC_PLAN.md)):
- TimescaleDB for time-series storage
- PostgreSQL logical replication to central server
- Grafana dashboards
- ML inference at edge

---

## Key Features

### 1. Web-Based Configuration

- **No manual CSV editing** - Configure everything through GUI
- **Real-time discovery** - Automatic BACnet device scanning
- **Haystack tagging** - Industry-standard semantic tags
- **MQTT topic preview** - See generated topics before enabling
- **Bulk operations** - Enable/disable multiple points at once

### 2. Flexible MQTT Publishing

**Individual Topics:**
```
macau-casino/ahu_301/analogInput1/presentValue
{
  "value": 22.5,
  "timestamp": "2025-11-04T09:16:04+08:00",
  "units": "degreesCelsius",
  "quality": "good",
  "dis": "Supply Air Temperature"
}
```

**Batch Topics** (optional, for ML/AI):
```
macau-casino/ahu_301/batch
{
  "timestamp": "2025-11-04T09:16:04+08:00",
  "equipment": "ahu_301",
  "site": "macau-casino",
  "points": [
    {"name": "ai1", "value": 22.5, "units": "degreesCelsius"},
    {"name": "ai2", "value": 24.0, "units": "degreesCelsius"},
    {"name": "ao1", "value": 45.0, "units": "percent"}
  ]
}
```

### 3. Intelligent Polling

- **Per-point intervals** - Each point can have different poll rates (15s, 30s, 60s)
- **Minute-aligned polling** - Synchronized timestamps for ML/AI
- **Automatic retries** - Exponential backoff on BACnet failures
- **Resource efficient** - Only polls when interval elapsed

### 4. Resilient by Design

- **Offline operation** - Continues working during network outages
- **Automatic reconnection** - MQTT and BACnet auto-recovery
- **Graceful shutdown** - SIGTERM handling, clean disconnects
- **Health checks** - Docker container health monitoring

---

## Configuration

### Environment Variables

Key settings in `.env`:

```bash
# Database
POSTGRES_USER=anatoli
POSTGRES_DB=bacpipes

# BACnet Network
BACNET_IP=192.168.1.35
BACNET_PORT=47808

# MQTT Broker
MQTT_BROKER=10.0.60.2
MQTT_PORT=1883

# System
TZ=Asia/Kuala_Lumpur
```

### Web UI Settings

Access http://localhost:3001/settings to configure:

- **BACnet Network**: IP address, port
- **MQTT Broker**: Host, port, batch publishing toggle
- **System**: Timezone (50+ timezones supported)

All settings stored in database, no .env editing required!

---

## Project Structure

```
BacPipes/
├── frontend/                  # Next.js web application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx              # Dashboard
│   │   │   ├── discovery/page.tsx    # BACnet discovery
│   │   │   ├── points/page.tsx       # Point configuration
│   │   │   ├── settings/page.tsx     # System settings
│   │   │   └── api/                  # REST API routes
│   │   ├── components/               # React components
│   │   └── lib/                      # Utilities, Prisma client
│   ├── prisma/
│   │   ├── schema.prisma             # Database schema
│   │   └── migrations/               # Migration history
│   └── package.json
│
├── worker/                    # Python BACnet worker
│   ├── mqtt_publisher.py             # Main worker (BACpypes3)
│   ├── requirements.txt
│   └── Dockerfile
│
├── scripts/                   # Legacy Python scripts (pre-Docker)
│   └── *.py                          # Original CSV-based workflow
│
├── docker-compose.yml         # Service orchestration
├── .env                       # Configuration (gitignored)
├── CLAUDE.md                  # Project documentation
├── STRATEGIC_PLAN.md          # Architecture roadmap
└── README.md                  # This file
```

---

## Common Tasks

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f bacnet-worker
docker compose logs -f frontend

# Last 50 lines
docker compose logs --tail=50 bacnet-worker
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart worker only
docker compose restart bacnet-worker

# Rebuild and restart
docker compose up -d --build
```

### Database Operations

```bash
# Access PostgreSQL
docker exec -it bacpipes-postgres psql -U anatoli -d bacpipes

# Run Prisma migrations
cd frontend
npx prisma migrate deploy

# Generate Prisma client
npx prisma generate

# Reset database (⚠️ deletes all data)
npx prisma migrate reset
```

### Backup & Restore

```bash
# Backup database
docker exec bacpipes-postgres pg_dump -U anatoli bacpipes > backup.sql

# Restore database
docker exec -i bacpipes-postgres psql -U anatoli bacpipes < backup.sql

# Backup Docker volumes
docker run --rm -v bacpipes_postgres_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/postgres_backup.tar.gz /data
```

---

## MQTT Topic Format

### Individual Topics

Format: `{site}/{equipment}/{point}/presentValue`

Examples:
- `macau-casino/ahu_301/analogInput1/presentValue`
- `klcc-tower/chiller_01/analogValue15/presentValue`
- `singapore-office/vav_north_12/binaryInput3/presentValue`

### Batch Topics

Format: `{site}/{equipment}/batch`

Examples:
- `macau-casino/ahu_301/batch`
- `klcc-tower/chiller_01/batch`

**Enable batch publishing in Settings** (disabled by default to avoid data redundancy).

---

## Troubleshooting

### Worker Not Publishing Data

1. Check worker logs:
   ```bash
   docker compose logs -f bacnet-worker
   ```

2. Verify BACnet connectivity:
   ```bash
   # Check if devices are reachable
   docker exec bacpipes-worker ping 192.168.1.37
   ```

3. Check MQTT broker:
   ```bash
   # Test MQTT connection
   mosquitto_sub -h 10.0.60.2 -t "#" -v
   ```

4. Verify points enabled:
   ```sql
   SELECT COUNT(*) FROM "Point" WHERE "mqttPublish" = true;
   ```

### Discovery Finds No Devices

1. Verify BACnet IP is correct (check Settings page)
2. Ensure worker has network access to BACnet subnet
3. Check firewall rules (UDP port 47808)
4. Try manual BACnet tool (YABE) from same network

### Database Connection Errors

1. Check PostgreSQL is running:
   ```bash
   docker compose ps postgres
   ```

2. Verify connection string in .env:
   ```bash
   grep DATABASE_URL .env
   ```

3. Restart database:
   ```bash
   docker compose restart postgres
   ```

### Frontend Build Errors

1. Clear Next.js cache:
   ```bash
   cd frontend
   rm -rf .next
   ```

2. Regenerate Prisma client:
   ```bash
   npx prisma generate
   ```

3. Reinstall dependencies:
   ```bash
   rm -rf node_modules
   npm install
   ```

---

## Development

### Running in Development Mode

```bash
# Frontend with hot-reload
cd frontend
npm run dev

# Worker with auto-reload
cd worker
source venv/bin/activate
python mqtt_publisher.py
```

### Making Database Changes

```bash
cd frontend

# 1. Edit prisma/schema.prisma
nano prisma/schema.prisma

# 2. Create migration
npx prisma migrate dev --name add_new_field

# 3. Generate Prisma client
npx prisma generate

# 4. Restart services
docker compose restart
```

### Adding New Features

1. Update database schema (Prisma)
2. Create API routes (`frontend/src/app/api/`)
3. Create UI components (`frontend/src/components/`)
4. Update worker logic (`worker/mqtt_publisher.py`)
5. Test locally
6. Commit to Git
7. Deploy via Docker Compose

---

## Performance

### Typical Resource Usage (Per Site)

| Resource | Usage | Notes |
|----------|-------|-------|
| **CPU** | 5-10% | 2-4 cores sufficient |
| **RAM** | 500MB | 2GB recommended |
| **Disk** | 1GB/week | With 7-day retention |
| **Network** | 10KB/s | Per 100 points at 60s intervals |
| **MQTT msgs/sec** | 1-5 | Depends on polling frequency |

### Scaling

- **Single site**: Raspberry Pi 4 (4GB RAM) sufficient
- **10 sites**: Standard VM (8GB RAM, 4 vCPU)
- **100 sites**: Dedicated server or 10× VMs
- **1000 sites**: Distributed cluster (see STRATEGIC_PLAN.md)

---

## Security

### Current Implementation

- ✅ PostgreSQL trust authentication (localhost only)
- ✅ MQTT without auth (internal network)
- ✅ No TLS (internal deployment)
- ⚠️ Suitable for trusted networks only

### Production Hardening (TODO)

- [ ] PostgreSQL SSL + password authentication
- [ ] MQTT TLS + username/password
- [ ] Frontend authentication (OAuth/SAML)
- [ ] Role-based access control (RBAC)
- [ ] Audit logging

**For WAN deployment**, see [STRATEGIC_PLAN.md](STRATEGIC_PLAN.md) security section.

---

## Roadmap

See [STRATEGIC_PLAN.md](STRATEGIC_PLAN.md) for detailed 7-phase implementation plan:

- **Phase 1-5**: Complete (Foundation → Monitoring)
- **Phase 6**: TimescaleDB integration (in progress)
- **Phase 7**: Multi-site replication (planned)
- **Phase 8+**: ML optimization, advanced features

---

## Contributing

### Reporting Issues

Please include:
- Docker Compose logs
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Docker version)

### Development Workflow

1. Fork repository
2. Create feature branch
3. Test locally with Docker Compose
4. Update documentation (README, CLAUDE.md)
5. Submit pull request

---

## License

MIT License - See [LICENSE](LICENSE) file

---

## Acknowledgments

- **BACpypes3** - Modern BACnet stack for Python
- **Next.js** - React framework for web UI
- **Prisma** - Type-safe database ORM
- **Shadcn/ui** - Component library
- **TimescaleDB** - PostgreSQL extension for time-series

---

## Support

- **Documentation**: See [CLAUDE.md](CLAUDE.md) for detailed technical docs
- **Architecture**: See [STRATEGIC_PLAN.md](STRATEGIC_PLAN.md) for system design
- **Issues**: Create issue on Gitea repository
- **Email**: support@yourcompany.com (replace with actual)

---

**Built with ❤️ for the building automation community**

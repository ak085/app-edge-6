# BacPipes - AI Development Context

## Current Status (December 2025)

**Production Ready**: BACnet-to-MQTT edge gateway with web-based configuration.

**Core Features**:
- BACnet device/point discovery via web UI
- Haystack tagging (8-field semantic naming)
- MQTT publishing to external broker
- MQTT TLS/SSL with certificate verification
- MQTT authentication (username/password)
- Configurable MQTT Client ID (displayed on broker)
- BACnet write command support
- Automatic setup wizard for first-run
- Database-driven configuration (no .env editing needed)
- Minute-aligned polling (starts at second :00)
- UTC timestamps with timezone offset for ML applications

---

## Architecture

```
┌─────────────────────────────────────────────┐
│ BacPipes (Docker Compose)                   │
├─────────────────────────────────────────────┤
│  Frontend (Next.js 15) - Port 3001          │
│  ├─ Dashboard                               │
│  ├─ Discovery                               │
│  ├─ Points (Haystack tagging)               │
│  └─ Settings                                │
│                                             │
│  PostgreSQL 15 - Port 5434                  │
│  └─ Devices, Points, Config                 │
│                                             │
│  BACnet Worker (Python/BACpypes3)           │
│  ├─ Polls BACnet devices                    │
│  ├─ Publishes to MQTT                       │
│  └─ Handles write commands                  │
└─────────────────────────────────────────────┘
                  ↓ MQTT
┌─────────────────────────────────────────────┐
│ External MQTT Broker                        │
│ - Supports TLS/SSL                          │
│ - Supports authentication                   │
└─────────────────────────────────────────────┘
```

---

## Technology Stack

- **Frontend**: Next.js 15 + TypeScript + Shadcn/ui
- **Database**: PostgreSQL 15
- **Worker**: Python 3.10 + BACpypes3 + paho-mqtt
- **Deployment**: Docker Compose

---

## Quick Commands

```bash
# Deploy
docker compose up -d

# Access UI
http://<your-ip>:3001

# View logs
docker compose logs -f bacnet-worker

# Restart worker
docker compose restart bacnet-worker

# Database access
docker exec -it bacpipes-postgres psql -U anatoli -d bacpipes
```

---

## MQTT Payload Format

```json
{
  "value": 23.5,
  "timestamp": "2025-12-16T12:31:00.847Z",
  "tz": 8,
  "units": "degC",
  "quality": "good",
  "dis": "Supply Air Temp",
  "haystackName": "site.ahu.12.sensor.temp.air.supply.actual",
  "objectType": "analog-input"
}
```

| Field | Description |
|-------|-------------|
| `timestamp` | UTC time (ISO 8601 with Z suffix) |
| `tz` | Timezone offset from Settings (e.g., 8 for +08:00) |
| `haystackName` | Full Haystack semantic name |
| `objectType` | BACnet object type |

---

## Key Files

| File | Purpose |
|------|---------|
| `worker/mqtt_publisher.py` | Main BACnet polling and MQTT publishing |
| `worker/discovery.py` | BACnet device/point discovery |
| `frontend/src/app/page.tsx` | Dashboard |
| `frontend/src/app/settings/page.tsx` | Settings UI |
| `frontend/prisma/schema.prisma` | Database schema |

---

## Port Allocation

| Port | Service |
|------|---------|
| 3001 | Frontend (Web UI) |
| 5434 | PostgreSQL |
| 47808 | BACnet/IP (UDP) |

---

## Optional: Time-Series Storage

For historical data storage, deploy the storage stack separately:

```bash
docker compose -f docker-compose-storage.yml up -d
```

This adds:
- TimescaleDB (port 5435)
- Telegraf (MQTT → TimescaleDB ingestion)

The storage stack can be deployed on the same machine or a separate server.

---

## Repository

- **Gitea**: http://10.0.10.2:30008/ak101/app-edge3.git
- **Branch**: main

---

**Last Updated**: 2025-12-16

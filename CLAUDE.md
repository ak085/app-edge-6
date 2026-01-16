# BacPipes - AI Development Context

## Current Status (December 2025)

**Production Ready**: BACnet-to-MQTT edge gateway with web-based configuration.

**Core Features**:
- Web UI authentication with session management
- Master PIN protection for password changes
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
│  ├─ Login (session-based auth)              │
│  ├─ Dashboard                               │
│  ├─ Discovery                               │
│  ├─ Points (Haystack tagging)               │
│  └─ Settings (Master PIN, password)         │
│                                             │
│  PostgreSQL 15 - Port 5434                  │
│  └─ Devices, Points, Config, Auth           │
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

## Authentication System

### Login
- Default credentials: `admin` / `admin`
- Session-based with iron-session (encrypted cookies)
- 3-hour session timeout
- All pages/APIs protected except `/login`

### Master PIN
- 4-6 digit PIN protects password changes
- Set via Settings page or CLI
- Only system administrator should know the PIN
- Prevents unauthorized password changes by other users

### CLI Recovery Commands

```bash
# Reset password to "admin" (if forgotten)
docker exec bacpipes-frontend node scripts/reset-password.js

# Reset Master PIN (if forgotten)
docker exec bacpipes-frontend node scripts/reset-pin.js

# Set Master PIN directly (remote management)
docker exec bacpipes-frontend node scripts/set-pin.js 1234
```

---

## Technology Stack

- **Frontend**: Next.js 15 + TypeScript + Shadcn/ui
- **Auth**: iron-session + bcryptjs
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

# Recovery commands
docker exec bacpipes-frontend node scripts/reset-password.js
docker exec bacpipes-frontend node scripts/reset-pin.js
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
  "objectType": "analog-input",
  "objectInstance": 435
}
```

| Field | Description |
|-------|-------------|
| `timestamp` | UTC time (ISO 8601 with Z suffix) |
| `tz` | Timezone offset from Settings (e.g., 8 for +08:00) |
| `haystackName` | Full Haystack semantic name (may not be unique) |
| `objectType` | BACnet object type |
| `objectInstance` | BACnet object instance (unique within device + objectType) |

**Note:** Use `objectInstance` together with `haystackName` for unique identification when storing data. Points with identical haystack names can be differentiated by their object instance.

---

## Key Files

| File | Purpose |
|------|---------|
| `frontend/src/lib/session.ts` | Session configuration |
| `frontend/src/lib/auth.ts` | Password hashing (bcrypt) |
| `frontend/src/middleware.ts` | Auth middleware |
| `frontend/src/app/api/auth/*` | Auth API routes |
| `frontend/scripts/*.js` | CLI recovery scripts |
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

## Repository

- **Gitea**: http://10.0.10.2:30008/ak101/app-edge-5.git
- **Branch**: main

---

**Last Updated**: 2025-12-22

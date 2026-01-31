# BacPipes - AI Development Context

## Current Status (January 2026)

**Production Ready**: BACnet-to-MQTT edge gateway - now a pure Python Reflex application.

**Architecture Change**: Converted from Next.js + Python worker to single Python Reflex app.

**Core Features**:
- Web UI authentication with session management
- Master PIN protection for password changes
- Dark mode toggle (Reflex standard color mode)
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
- Headless mode (worker only, no web UI)

---

## Architecture (Reflex Version)

```
┌─────────────────────────────────────────────┐
│ BacPipes (Single Python App)                │
├─────────────────────────────────────────────┤
│  Reflex Framework                           │
│  ├─ Frontend (React via Reflex)             │
│  │   ├─ Login (session-based auth)          │
│  │   ├─ Dashboard (tabs UI)                 │
│  │   │   ├─ Dashboard tab                   │
│  │   │   ├─ Discovery tab                   │
│  │   │   ├─ Points tab                      │
│  │   │   └─ Settings tab                    │
│  │   └─ Setup Wizard                        │
│  │                                          │
│  ├─ Backend (Reflex State)                  │
│  │   ├─ AuthState                           │
│  │   ├─ DashboardState                      │
│  │   ├─ DiscoveryState                      │
│  │   ├─ PointsState                         │
│  │   ├─ SettingsState                       │
│  │   └─ WorkerState                         │
│  │                                          │
│  └─ Worker (Lifespan Task)                  │
│      ├─ BACnet polling (BACpypes3)          │
│      ├─ MQTT publishing (paho-mqtt)         │
│      └─ Write command handling              │
│                                             │
│  PostgreSQL 15 - Port 5432                  │
│  └─ SQLModel ORM                            │
└─────────────────────────────────────────────┘
                  ↓ MQTT
┌─────────────────────────────────────────────┐
│ External MQTT Broker                        │
└─────────────────────────────────────────────┘
```

---

## Project Structure

```
bacpipes/
├── bacpipes/                     # Reflex app package
│   ├── __init__.py
│   ├── __main__.py               # CLI entry (--headless support)
│   ├── bacpipes.py               # Main app entry, routes
│   │
│   ├── models/                   # SQLModel database models
│   │   ├── device.py
│   │   ├── point.py
│   │   ├── mqtt_config.py
│   │   ├── system_settings.py
│   │   ├── discovery_job.py
│   │   └── write_history.py
│   │
│   ├── state/                    # Reflex State classes
│   │   ├─ auth_state.py
│   │   ├── dashboard_state.py
│   │   ├── discovery_state.py
│   │   ├── points_state.py
│   │   ├── settings_state.py
│   │   └── worker_state.py
│   │
│   ├── pages/                    # Page components
│   │   ├── login.py
│   │   ├── dashboard.py
│   │   └── setup_wizard.py
│   │
│   ├── components/               # Reusable UI
│   │   ├── layout.py
│   │   ├── status_card.py
│   │   ├── point_table.py
│   │   └── point_editor.py
│   │
│   ├── worker/                   # BACnet/MQTT worker
│   │   ├── bacnet_client.py
│   │   ├── mqtt_client.py
│   │   ├── discovery.py
│   │   └── polling.py
│   │
│   └── utils/
│       ├── auth.py
│       └── network.py
│
├── rxconfig.py                   # Reflex config
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Quick Commands

```bash
# Development
pip install -r requirements.txt
reflex run

# Run with web UI
python -m bacpipes

# Run headless (worker only)
python -m bacpipes --headless

# Docker deployment
docker compose up -d

# Access UI
http://localhost:3000

# Database access
docker exec -it bacpipes-postgres psql -U bacpipes -d bacpipes
```

---

## Technology Stack

- **Framework**: Reflex (Python full-stack)
- **Frontend**: React (via Reflex, auto-generated)
- **Backend**: Reflex State + Lifespan Tasks
- **Database**: PostgreSQL 15 with SQLModel ORM
- **Auth**: bcrypt + session-based
- **BACnet**: BACpypes3
- **MQTT**: paho-mqtt

---

## Authentication

### Login
- Default credentials: `admin` / `admin`
- Session-based with 3-hour timeout
- All pages protected except `/login`

### Master PIN
- 4-6 digit PIN protects password changes
- Set via Settings tab
- Prevents unauthorized password changes

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

**Note:** Use `objectInstance` together with `haystackName` for unique identification when storing data.

---

## Key Files

| File | Purpose |
|------|---------|
| `bacpipes/bacpipes.py` | Main Reflex app entry |
| `bacpipes/state/*.py` | State management |
| `bacpipes/pages/dashboard.py` | Main UI with tabs |
| `bacpipes/worker/polling.py` | BACnet polling loop |
| `bacpipes/worker/discovery.py` | BACnet discovery |
| `bacpipes/models/*.py` | SQLModel ORM models |
| `rxconfig.py` | Database configuration |

---

## Port Allocation

| Port | Service |
|------|---------|
| 3000 | Reflex Frontend |
| 8000 | Reflex Backend |
| 5432 | PostgreSQL |
| 47808 | BACnet/IP (UDP) |

---

## Database Models

| Model | Table | Purpose |
|-------|-------|---------|
| Device | Device | BACnet devices |
| Point | Point | BACnet objects + Haystack tags |
| MqttConfig | MqttConfig | MQTT broker settings |
| SystemSettings | SystemSettings | Auth + BACnet config |
| DiscoveryJob | DiscoveryJob | Scan tracking |
| WriteHistory | WriteHistory | Write audit log |
---

**Last Updated**: 2026-01-31

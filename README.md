# BacPipes - BACnet to MQTT Edge Gateway

**Production-ready BACnet-to-MQTT bridge built with Python Reflex**

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](docker-compose.yml)
[![Reflex](https://img.shields.io/badge/Reflex-Python-purple)](https://reflex.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.10-yellow?logo=python)](https://www.python.org/)

---

## Quick Start

```bash
# Clone and deploy
git clone <repository-url> bacpipes
cd bacpipes
docker compose up -d

# Access UI
# http://<your-ip>:3000
# Default login: admin / admin
```

**Setup wizard appears automatically on first run** - configures BACnet IP and MQTT broker.

---

## What is BacPipes?

BacPipes is an edge gateway that:
1. **Discovers** BACnet devices on your network
2. **Tags** points using Haystack semantic naming
3. **Publishes** selected points to any MQTT broker
4. **Supports** BACnet write commands for remote control

Perfect for integrating building automation systems with IoT platforms, time-series databases, or cloud services.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│ BacPipes (Single Python App)                │
├─────────────────────────────────────────────┤
│  Reflex Framework                           │
│  ├─ Frontend (React via Reflex) - Port 3000 │
│  │   ├─ Login (session-based auth)          │
│  │   ├─ Dashboard (tabs UI)                 │
│  │   │   ├─ Dashboard tab                   │
│  │   │   ├─ Discovery tab                   │
│  │   │   ├─ Points tab                      │
│  │   │   └─ Settings tab                    │
│  │   └─ Setup Wizard                        │
│  │                                          │
│  ├─ Backend (Reflex State) - Port 8000      │
│  │   └─ SQLModel ORM                        │
│  │                                          │
│  └─ Worker (Lifespan Task)                  │
│      ├─ BACnet polling (BACpypes3)          │
│      ├─ MQTT publishing (paho-mqtt)         │
│      └─ Write command handling              │
│                                             │
│  PostgreSQL 15 - Port 5432                  │
└─────────────────────────────────────────────┘
                  ↓ MQTT publish
┌─────────────────────────────────────────────┐
│ External MQTT Broker                        │
│ - Any broker (Mosquitto, EMQX, HiveMQ)      │
│ - Supports TLS/SSL encryption               │
│ - Supports username/password auth           │
└─────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Web Authentication** | Login required, 3-hour session timeout |
| **Master PIN** | Protects password changes (admin-only control) |
| **Dark Mode** | Toggle between light and dark themes |
| **BACnet Discovery** | Auto-scan network for devices and points |
| **Haystack Tagging** | 8-field semantic naming for ML/analytics |
| **MQTT Publishing** | Real-time data streaming to any broker |
| **TLS Support** | Secure MQTT with certificate verification |
| **Configurable Client ID** | Custom identifier shown on MQTT broker |
| **Write Commands** | Remote control with priority array support |
| **Setup Wizard** | Zero-config first-run experience |
| **Minute-Aligned Polling** | Data starts at second :00 for synchronization |
| **Timezone Support** | UTC timestamps with `tz` offset for ML applications |
| **Headless Mode** | Run worker only without web UI |

---

## Authentication

### Default Credentials
- **Username**: `admin`
- **Password**: `admin`

### Master PIN
The Master PIN protects password changes. Only the system administrator should know it.
- Set via Settings page after login
- 4-6 digits
- Required when changing the password

---

## First-Time Setup

1. **Access Dashboard**: http://your-ip:3000
2. **Login**: Use `admin` / `admin`
3. **Complete Setup Wizard**:
   - Select BACnet network interface (auto-detected)
   - Enter MQTT broker IP (optional - can configure later)
4. **Set Master PIN**: Go to Settings, set a PIN to protect password changes
5. **Change Password**: Update the default password
6. **Run Discovery**: Click "Start Discovery" to find BACnet devices
7. **Tag Points**: Add Haystack tags, enable MQTT publishing
8. **Verify**: Check Dashboard for MQTT connection status

---

## Common Commands

| Operation | Command |
|-----------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Restart after shutdown | `docker compose up -d` |
| Restart running container | `docker compose restart bacpipes` |
| Logs | `docker compose logs -f bacpipes` |
| Rebuild | `docker compose build && docker compose up -d` |
| Reset (delete data) | `docker compose down -v` |

---

## Haystack Tagging

BacPipes uses an 8-field semantic naming structure:

```
{site}.{equip}.{equipRef}.{point}.{measurement}.{substance}.{condition}.{descriptor}
```

**Example:**
```
klcc.ahu.12.sensor.temp.air.supply.actual
```

**MQTT Topic Generated:**
```
bacnet/klcc/ahu_12/sensor/temp/air/supply/actual/presentValue
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
| `timestamp` | UTC time (ISO 8601) |
| `tz` | Timezone offset from Settings (e.g., 8 for +08:00) |
| `haystackName` | Full Haystack semantic name |
| `objectType` | BACnet object type |
| `objectInstance` | BACnet object instance (unique within device + objectType) |

---

## Port Allocation

| Port | Service |
|------|---------|
| 3000 | Web UI (Reflex Frontend) |
| 8000 | Reflex Backend |
| 5432 | PostgreSQL |
| 47808 | BACnet/IP (UDP) |

---

## Configuration

### Via Settings Page (Recommended)

All configuration is done via the web UI at `/settings`:
- BACnet Network IP, Port, Device ID
- MQTT Broker IP, Port, Client ID
- MQTT Authentication (username/password)
- TLS/SSL settings with certificate upload
- Timezone for timestamps
- Poll intervals
- Master PIN management
- Password change

---

## Troubleshooting

### Can't Login
1. Try default credentials: `admin` / `admin`
2. Check container logs: `docker compose logs bacpipes`

### Worker Not Starting
```bash
docker compose logs -f bacpipes
```
Common: Database not ready. Wait 30s and check again.

### MQTT Shows Disconnected
1. Check broker IP in Settings
2. Test: `ping <broker-ip>`
3. Restart: `docker compose restart bacpipes`

### Discovery Finds No Devices
1. Verify BACnet IP matches your network interface
2. Check firewall: `sudo ufw allow 47808/udp`
3. Confirm devices are on same network

---

## Development

See `CLAUDE.md` for detailed development context.

**Project Structure:**
```
bacpipes/
├── docker-compose.yml          # Docker deployment
├── Dockerfile                  # Container build
├── requirements.txt            # Python dependencies
├── rxconfig.py                 # Reflex configuration
└── bacpipes/                   # Reflex Python app
    ├── bacpipes.py             # Main app entry
    ├── models/                 # SQLModel database models
    ├── state/                  # Reflex State classes
    ├── pages/                  # Page components
    ├── components/             # Reusable UI components
    ├── worker/                 # BACnet/MQTT worker
    └── utils/                  # Utilities
```

---

**Last Updated:** January 2026
**Status:** Production-ready

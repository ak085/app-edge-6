# BacPipes - BACnet to MQTT Edge Gateway

**Production-ready BACnet-to-MQTT bridge with web-based configuration**

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](docker-compose.yml)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.10-yellow?logo=python)](https://www.python.org/)

---

## Quick Start

```bash
# Clone and deploy
git clone http://10.0.10.2:30008/ak101/app-edge3.git bacpipes
cd bacpipes
docker compose up -d

# Access UI
# http://<your-ip>:3001
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
│ BacPipes (Docker Compose)                   │
├─────────────────────────────────────────────┤
│  Frontend (Next.js) - Port 3001             │
│  ├─ Dashboard (system status)               │
│  ├─ Discovery (BACnet scan)                 │
│  ├─ Points (Haystack tagging)               │
│  └─ Settings (BACnet/MQTT config)           │
│                                             │
│  PostgreSQL - Port 5434                     │
│  └─ Devices, Points, Config                 │
│                                             │
│  BACnet Worker (Python/BACpypes3)           │
│  ├─ Polls BACnet devices                    │
│  ├─ Publishes to MQTT                       │
│  └─ Handles write commands                  │
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
| **BACnet Discovery** | Auto-scan network for devices and points |
| **Haystack Tagging** | 8-field semantic naming for ML/analytics |
| **MQTT Publishing** | Real-time data streaming to any broker |
| **TLS Support** | Secure MQTT with certificate verification |
| **Configurable Client ID** | Custom identifier shown on MQTT broker |
| **Write Commands** | Remote control with priority array support |
| **Setup Wizard** | Zero-config first-run experience |
| **Minute-Aligned Polling** | Data starts at second :00 for synchronization |
| **Timezone Support** | UTC timestamps with `tz` offset for ML applications |

---

## First-Time Setup

1. **Access Dashboard**: http://your-ip:3001
2. **Complete Setup Wizard**:
   - Select BACnet network interface (auto-detected)
   - Enter MQTT broker IP (optional - can configure later)
3. **Run Discovery**: Click "Start Discovery" to find BACnet devices
4. **Tag Points**: Add Haystack tags, enable MQTT publishing
5. **Verify**: Check Dashboard for MQTT connection status

---

## Common Commands

| Operation | Command |
|-----------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Logs | `docker compose logs -f bacnet-worker` |
| Restart worker | `docker compose restart bacnet-worker` |
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
  "objectType": "analog-input"
}
```

| Field | Description |
|-------|-------------|
| `timestamp` | UTC time (ISO 8601) |
| `tz` | Timezone offset from Settings (e.g., 8 for +08:00) |
| `haystackName` | Full Haystack semantic name |
| `objectType` | BACnet object type |

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

---

## Port Allocation

| Port | Service |
|------|---------|
| 3001 | Web UI (Frontend) |
| 5434 | PostgreSQL |
| 47808 | BACnet/IP (UDP) |

---

## Troubleshooting

### Worker Not Starting
```bash
docker compose logs bacnet-worker
```
Common: Database not ready. Wait 30s and check again.

### MQTT Shows Disconnected
1. Check broker IP in Settings
2. Test: `ping <broker-ip>`
3. Restart: `docker compose restart bacnet-worker`

### Discovery Finds No Devices
1. Verify BACnet IP matches your network interface
2. Check firewall: `sudo ufw allow 47808/udp`
3. Confirm devices are on same network

---

## Optional: Time-Series Storage

For historical data storage, deploy the storage stack separately:

```bash
docker compose -f docker-compose-storage.yml up -d
```

This adds:
- TimescaleDB (port 5435) - Time-series database
- Telegraf - MQTT to TimescaleDB ingestion

The storage stack can run on the same machine or a separate server.

---

## Development

See `CLAUDE.md` for detailed development context.

**Project Structure:**
```
bacpipes/
├── docker-compose.yml          # Core services (frontend, postgres, worker)
├── docker-compose-storage.yml  # Optional storage (timescaledb, telegraf)
├── frontend/                   # Next.js web app
│   ├── src/app/               # Pages and API routes
│   └── prisma/                # Database schema
├── worker/                     # Python BACnet worker
│   └── mqtt_publisher.py      # Main polling loop
└── telegraf/                   # MQTT to TimescaleDB bridge
```

---

## Repository

- **Gitea**: http://10.0.10.2:30008/ak101/app-edge3.git

---

**Last Updated:** December 2025
**Status:** Production-ready

# Plan: Central Configuration App for Edge Devices (YAGNI Approach)

This document outlines the architecture for a centralized configuration system to manage multiple BacPipes edge devices remotely.

---

## Table of Contents

1. [Core Requirements](#core-requirements)
2. [YAGNI Analysis](#yagni-analysis)
3. [Architecture](#architecture)
4. [MQTT Bridge Configuration](#mqtt-bridge-configuration)
5. [MQTT Topic Structure](#mqtt-topic-structure)
6. [Database Schema](#database-schema)
7. [User Flow](#user-flow)
8. [Implementation Path](#implementation-path)
9. [Verification Plan](#verification-plan)

---

## Core Requirements

1. **Site Registry**: Database of 300-500 MQTT broker bridges
2. **Site Selection**: Search → Select → Connect to ONE edge device
3. **Configuration**: Discovery + point tagging + push config
4. **Status**: Simple up/down monitoring (not real-time dashboards)
5. **Data Display**: Handled elsewhere (TimescaleDB + separate dashboard)

---

## YAGNI Analysis

### What You DON'T Need

| Feature | Verdict | Why |
|---------|---------|-----|
| Always-on connections to all sites | ❌ SKIP | Connect on-demand, configure, disconnect |
| Real-time data streaming | ❌ SKIP | TimescaleDB dashboard handles this |
| Complex multi-tenant schemas | ❌ SKIP | Simple site_id foreign key is enough |
| Sophisticated alerting system | ❌ SKIP | Basic last_seen timestamp suffices |
| Multi-admin simultaneous editing | ❌ SKIP | One admin, one site at a time |
| Point values in config app | ❌ SKIP | Config only, no live data display |

### What You're NOT Building

1. ❌ Real-time point value display (TimescaleDB dashboard does this)
2. ❌ Historical charts in config app
3. ❌ Alert notifications (maybe later, not MVP)
4. ❌ User management/multi-tenant (one admin is fine)
5. ❌ Audit logging (maybe later)
6. ❌ Firmware updates (manual for now)
7. ❌ Complex device/point tables in central DB

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CENTRAL SERVER                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Config Dashboard (Reflex)                            │  │
│  │  - Site registry (300-500 entries)                    │  │
│  │  - Search/select site                                 │  │
│  │  - Connect to ONE edge at a time                      │  │
│  │  - Run discovery, configure, push, disconnect         │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Central MQTT Broker (Mosquitto)                      │  │
│  │  - Receives heartbeats from all edge devices          │  │
│  │  - Routes commands to edge devices                    │  │
│  │  - Receives responses from edge devices               │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  PostgreSQL + TimescaleDB                             │  │
│  │  - Site registry                                      │  │
│  │  - Point data (for separate analytics dashboard)      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↕
              MQTT Bridge (TLS) - each edge bridges to central
                              ↕
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Edge Device     │    │  Edge Device     │    │  Edge Device     │
│  - MQTT Broker   │    │  - MQTT Broker   │    │  - MQTT Broker   │
│  - BacPipes      │    │  - BacPipes      │    │  - BacPipes      │
│    (headless)    │    │    (headless)    │    │    (headless)    │
│  - Local config  │    │  - Local config  │    │  - Local config  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## MQTT Bridge Configuration

Each edge device runs a local Mosquitto broker that bridges to the central broker. This section documents the bridge configuration.

### Edge Device Bridge Configuration

File: `/etc/mosquitto/conf.d/bridge.conf`

```conf
# =============================================================================
# MQTT Bridge Configuration - Edge Device to Central Server
# =============================================================================

# Connection name (unique per edge device)
connection central-bridge

# Central broker address (TLS port)
address central.example.com:8883

# =============================================================================
# AUTHENTICATION
# =============================================================================

# Client ID sent to central broker (use site_code for identification)
remote_clientid edge-klcc-tower-a

# Credentials for central broker
remote_username edge-klcc-tower-a
remote_password <secure-password>

# =============================================================================
# TLS CONFIGURATION
# =============================================================================

bridge_cafile /etc/mosquitto/certs/ca.crt
bridge_certfile /etc/mosquitto/certs/client.crt
bridge_keyfile /etc/mosquitto/certs/client.key
bridge_tls_version tlsv1.2

# =============================================================================
# BRIDGE BEHAVIOR
# =============================================================================

# Start bridge on broker startup
start_type automatic

# Reconnect settings
restart_timeout 5 30

# Clean session (false = persistent subscriptions)
cleansession false

# Bridge protocol version
bridge_protocol_version mqttv311

# Notification topic (optional - for bridge status)
notifications true
notification_topic bridge/status/klcc-tower-a

# =============================================================================
# TOPIC MAPPINGS
# =============================================================================

# Syntax: topic <pattern> <direction> <qos> <local-prefix> <remote-prefix>
# Direction: in = central→edge, out = edge→central, both = bidirectional

# -----------------------------------------------------------------------------
# HEARTBEAT (Edge → Central)
# -----------------------------------------------------------------------------
# Edge publishes to local topic, bridges to central
topic heartbeat/klcc-tower-a out 1

# -----------------------------------------------------------------------------
# COMMANDS (Central → Edge)
# -----------------------------------------------------------------------------
# Central publishes commands, edge receives via bridge
topic cmd/klcc-tower-a/# in 1

# -----------------------------------------------------------------------------
# RESPONSES (Edge → Central)
# -----------------------------------------------------------------------------
# Edge publishes responses, bridges to central
topic response/klcc-tower-a/# out 1

# -----------------------------------------------------------------------------
# DATA POINTS (Edge → Central) - For TimescaleDB ingestion
# -----------------------------------------------------------------------------
# Point values published by BacPipes worker
topic data/klcc-tower-a/# out 0
```

### Topic Direction Reference

| Topic Pattern | Direction | QoS | Purpose |
|---------------|-----------|-----|---------|
| `heartbeat/{site_code}` | `out` | 1 | Edge → Central: Device online status |
| `cmd/{site_code}/#` | `in` | 1 | Central → Edge: Commands from central |
| `response/{site_code}/#` | `out` | 1 | Edge → Central: Command responses |
| `data/{site_code}/#` | `out` | 0 | Edge → Central: Point values for TimescaleDB |

### QoS Selection Rationale

| QoS | Used For | Why |
|-----|----------|-----|
| **QoS 0** | Point data (`data/#`) | High volume, occasional loss acceptable, TimescaleDB handles gaps |
| **QoS 1** | Heartbeat, commands, responses | Guaranteed delivery, no duplicates needed (idempotent operations) |
| **QoS 2** | Not used | Overhead not justified for this use case |

### Central Broker Configuration

File: `/etc/mosquitto/conf.d/central.conf`

```conf
# =============================================================================
# Central MQTT Broker Configuration
# =============================================================================

# Standard listener for local services (Reflex app, heartbeat processor)
listener 1883 127.0.0.1

# TLS listener for edge device bridges
listener 8883
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
tls_version tlsv1.2
require_certificate true

# Authentication
password_file /etc/mosquitto/passwd
allow_anonymous false

# ACL for topic access control
acl_file /etc/mosquitto/acl
```

### Central Broker ACL

File: `/etc/mosquitto/acl`

```conf
# Edge devices can only access their own topics
pattern read cmd/%c/#
pattern write heartbeat/%c
pattern write response/%c/#
pattern write data/%c/#

# Central services (Reflex app, heartbeat processor) can access all
user central-admin
topic readwrite #

user heartbeat-processor
topic read heartbeat/#
```

### Bridge Health Check

Edge device should verify bridge connectivity:

```bash
# Check bridge status
mosquitto_sub -t 'bridge/status/#' -v

# Test publish from edge (should appear on central)
mosquitto_pub -t 'heartbeat/klcc-tower-a' -m '{"test": true}'

# Test command from central (should appear on edge)
# Run on central:
mosquitto_pub -h central.example.com -t 'cmd/klcc-tower-a/ping' -m '{}'
# Verify on edge:
mosquitto_sub -t 'cmd/klcc-tower-a/#' -v
```

---

## MQTT Topic Structure

### Complete Topic Reference

```
Central Broker Topics:

# HEARTBEATS (edge → central)
# Direction: out | QoS: 1 | Frequency: every 60 seconds
heartbeat/{site_code}
  Payload: {
    "ts": 1706745600,           # Unix timestamp
    "devices": 5,               # BACnet device count
    "points": 234,              # Total point count
    "publishing": 180,          # Points actively publishing
    "mqtt": "connected",        # Local MQTT status
    "worker": "running",        # Worker status
    "version": "1.2.3"          # BacPipes version
  }

# COMMANDS (central → edge)
# Direction: in | QoS: 1

cmd/{site_code}/discovery/start
  Payload: {"timeout": 15}
  Response: response/{site_code}/discovery/result

cmd/{site_code}/config/push
  Payload: {full config JSON - devices, points, settings}
  Response: response/{site_code}/config/ack

cmd/{site_code}/config/pull
  Payload: {}
  Response: response/{site_code}/config/current

cmd/{site_code}/worker/restart
  Payload: {}
  Response: response/{site_code}/worker/status

cmd/{site_code}/ping
  Payload: {}
  Response: response/{site_code}/pong

# RESPONSES (edge → central)
# Direction: out | QoS: 1

response/{site_code}/discovery/result
  Payload: {
    "success": true,
    "devices": [...],           # Array of discovered devices
    "points": [...],            # Array of discovered points
    "duration": 12.5            # Seconds taken
  }

response/{site_code}/config/ack
  Payload: {
    "success": true,
    "version": 3,               # New config version
    "applied_at": "2026-02-01T10:30:00Z"
  }

response/{site_code}/config/current
  Payload: {full current config JSON}

response/{site_code}/pong
  Payload: {"ts": 1706745600}

# DATA POINTS (edge → central, for TimescaleDB)
# Direction: out | QoS: 0

data/{site_code}/{mqtt_topic}
  Payload: {
    "value": 23.5,
    "timestamp": "2026-02-01T10:30:00.847Z",
    "tz": 8,
    "units": "degC",
    "quality": "good"
  }
```

---

## Database Schema

### Central Database (PostgreSQL)

```sql
-- Site registry
CREATE TABLE site (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    site_code VARCHAR(50) UNIQUE NOT NULL,
    mqtt_topic_prefix VARCHAR(100),        -- defaults to site_code
    status VARCHAR(20) DEFAULT 'unknown',  -- online/offline/unknown
    last_seen TIMESTAMP,
    device_count INT DEFAULT 0,
    point_count INT DEFAULT 0,
    config_version INT DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Config snapshots (after each push)
CREATE TABLE site_config_snapshot (
    id SERIAL PRIMARY KEY,
    site_id INT REFERENCES site(id),
    config_json JSONB,
    pushed_at TIMESTAMP DEFAULT NOW(),
    pushed_by VARCHAR(100)
);

-- Config templates
CREATE TABLE config_template (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    equipment_type VARCHAR(50),
    point_mappings JSONB,
    default_poll_interval INT DEFAULT 60,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Example point_mappings:
-- {
--   "analog-input:Supply Air Temp*": {"quantity": "temp", "subject": "air", "location": "supply"},
--   "analog-output:*Damper*": {"quantity": "pos", "pointFunction": "cmd"},
--   "binary-input:*Status*": {"quantity": "run", "pointFunction": "sensor"}
-- }

-- Bulk operation tracking
CREATE TABLE bulk_operation (
    id SERIAL PRIMARY KEY,
    operation_type VARCHAR(50),
    site_ids INT[],
    status VARCHAR(20) DEFAULT 'pending',
    progress JSONB,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

## User Flow

### Minimum Steps to Configure a Site

```
1. Open Central Dashboard
2. Search: "klcc" → See matching sites
3. Click site → Connect to edge MQTT
4. See edge status (devices, points count)
5. Click "Run Discovery" if needed
6. Configure points (same UI as current BacPipes)
7. Click "Push Config" → Edge applies it
8. Close → Disconnect → Done
```

**Total: 4-5 clicks to configure a site**

### UI Mockups

#### Sites List Page
```
┌─────────────────────────────────────────────────────────────┐
│  Sites                                    [Search: ____]    │
├─────────────────────────────────────────────────────────────┤
│  ● KLCC Tower A        Online     Last: 2 min ago   [Open] │
│  ● KLCC Tower B        Online     Last: 1 min ago   [Open] │
│  ○ Pavilion Mall       Offline    Last: 3 hours     [Open] │
│  ● Sunway Pyramid      Online     Last: 30 sec ago  [Open] │
│  ...                                                        │
│                                      Showing 1-50 of 347    │
└─────────────────────────────────────────────────────────────┘
```

#### Site Detail Page
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back    KLCC Tower A                    ● Connected      │
├─────────────────────────────────────────────────────────────┤
│  Tabs: [Status] [Discovery] [Points] [Settings]            │
│                                                             │
│  (Same UI as current BacPipes, but for remote edge device) │
│                                                             │
│  [Push Config to Edge]  [Disconnect]                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Path

### Phase 1: Edge Device Modifications (2-3 days)

**Goal**: Make BacPipes headless mode remote-controllable

| Task | Description |
|------|-------------|
| MQTT bridge config | Configure edge broker to bridge to central |
| Heartbeat publisher | Publish status every 60s to `heartbeat/{site_code}` |
| Command handlers | Subscribe to `cmd/{site_code}/#`, execute commands |
| Response publisher | Publish results to `response/{site_code}/#` |
| Config receiver | Accept config push, apply to local DB, restart worker |

**Files to modify:**
- `worker/mqtt_client.py` - Add command subscription
- `worker/polling.py` - Add heartbeat publishing
- New: `worker/remote_commands.py` - Command handlers

### Phase 2: Central App MVP (3-4 days)

**Goal**: Basic site management and configuration

```
central-config/
├── models/
│   ├── site.py
│   └── config_template.py
├── state/
│   ├── sites_state.py          # List, search, CRUD
│   ├── site_session_state.py   # Active connection to one edge
│   └── template_state.py       # Template management
├── pages/
│   ├── sites.py                # Site list with search
│   ├── site_detail.py          # Single site config (tabs)
│   └── templates.py            # Template editor
├── services/
│   └── mqtt_bridge.py          # Pub/sub to central broker
└── components/
    └── (reuse from BacPipes)   # Point table, editor, etc.
```

### Phase 3: Templates & Bulk Operations (2-3 days)

| Feature | Implementation |
|---------|----------------|
| Template editor | CRUD for config_template table |
| Auto-apply | Match BACnet point names to template patterns |
| Bulk select | Multi-select in sites list |
| Bulk apply | Queue commands to multiple sites, show progress |

### Phase 4: Heartbeat Monitoring (1 day)

| Component | Implementation |
|-----------|----------------|
| Heartbeat listener | Python script subscribing to `heartbeat/#` |
| DB updater | Update `site.status` and `site.last_seen` |
| Stale checker | Cron: mark offline if last_seen > 5 min |
| UI indicator | Green/red dot in sites list |

---

## Reusable Components from BacPipes

| Component | Reuse? | Notes |
|-----------|--------|-------|
| `point_table.py` | ✅ Yes | Change data source from local DB to MQTT response |
| `point_editor.py` | ✅ Yes | Same UI, push via MQTT instead of local DB |
| `status_card.py` | ✅ Yes | Display edge device stats |
| Discovery tab UI | ✅ Yes | Trigger via MQTT command |
| Settings tab | ⚠️ Partial | Edge settings pushed via MQTT |
| Auth/login | ✅ Yes | Same session-based auth |

---

## Verification Plan

1. **Edge device test:**
   - Start BacPipes headless with bridge config
   - Verify heartbeat appears at central broker
   - Send discovery command, verify response

2. **Central app test:**
   - Add a site to registry
   - Verify status updates from heartbeat
   - Open site detail, run discovery
   - Configure points, push config
   - Verify edge applies config

3. **Template test:**
   - Create template with point mappings
   - Apply to site after discovery
   - Verify tags auto-populated correctly

4. **Bulk test:**
   - Select 3 sites
   - Apply template to all
   - Verify all 3 receive config

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 1: Edge modifications | 2-3 days |
| Phase 2: Central app MVP | 3-4 days |
| Phase 3: Templates & bulk | 2-3 days |
| Phase 4: Monitoring | 1 day |
| **Total** | **~2 weeks** |

---

## Decisions Made

| Question | Decision |
|----------|----------|
| Connectivity | **MQTT Bridge to Central** - all edges bridge to central broker |
| Config Storage | **Both** - edge authoritative, central stores JSON snapshot |
| Additional Features | **Config templates** + **Bulk operations** |

---

**Last Updated**: 2026-02-01

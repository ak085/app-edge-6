# BacPipes Strategic Architecture Plan

**Version:** 2.0
**Date:** 2025-11-08
**Status:** Revised - Single Site Focus

---

## Executive Summary

BacPipes is a Docker Compose-based BACnet-to-MQTT data pipeline with web UI for building automation. This plan focuses on **proving the architecture at single-site scale** before considering multi-site deployment. The priority is reliability, data persistence, remote monitoring, and eventual ML optimization.

### Current State (v0.6.1):
- ✅ Single Proxmox LXC deployment
- ✅ BACnet discovery and polling (2 devices, 5 points active)
- ✅ MQTT publishing (individual topics only)
- ✅ Real-time monitoring dashboard (SSE)
- ✅ BACnet write commands (via MQTT)
- ✅ PostgreSQL for configuration
- ❌ No historical storage yet (TimescaleDB needed)

### Key Design Decisions:
- ✅ **PostgreSQL** for configuration + current state
- ✅ **TimescaleDB** for historical time-series data (local + central)
- ✅ **PostgreSQL Replication** for site-to-central sync (SSL encrypted)
- ✅ **Docker Compose** deployment (entire stack in one LXC container)
- ✅ **No Redis** (not needed at current scale)
- ✅ **No VPN** for data flow (PostgreSQL SSL sufficient)
- ⏳ **ML optimization** (future - after baseline measurement)

---

## System Requirements

### Current Scale (Proven)
- **Sites:** 1 (Proxmox LXC)
- **Devices:** 2 BACnet controllers
- **Active Points:** 5 (target: 50+ in Phase 1)
- **Polling frequency:** 30-60 seconds per point
- **Throughput:** ~5-10 sensor readings/minute

### Phase 1 Target Scale
- **Sites:** 1 (same Proxmox LXC)
- **Devices:** 2 (existing)
- **Active Points:** 50+ (scale up discovery)
- **Historical storage:** 1 day local (TimescaleDB)
- **Visualization:** Grafana dashboards

### Phase 2 Target Scale
- **Sites:** 1 local + 1 central DB
- **Central location:** Home DMZ or cloud (testing)
- **Replication:** PostgreSQL logical replication (SSL)
- **Historical storage:** 30 days central (TimescaleDB)
- **Monitoring:** Remote Grafana viewing all sites

### Network Requirements
- **Local network:** Existing (BACnet devices on 192.168.1.0/24)
- **Internet:** Home broadband or 4G LTE
- **Central connectivity:** Port 5432 forwarded (PostgreSQL)
- **Bandwidth:** ~100KB/day per 50 points (minimal)
- **Latency:** Not critical (5-60 second replication lag acceptable)

### Security
- **Data in transit:** PostgreSQL SSL/TLS 1.3 encryption
- **Authentication:** Client certificates for replication
- **No VPN needed:** SSL sufficient for data flow
- **VPN (optional):** Tailscale for admin SSH access only
- **Firewall:** Allow port 5432 from known IPs only

---

## Architecture Overview

### Current Architecture (v0.6.1)

```
┌──────────────────────────────────────────────────────────────┐
│ SITE (Proxmox LXC - Docker Compose)                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  BACnet DDC (192.168.1.37, 192.168.1.42)                    │
│    ↓ BACnet/IP (UDP 47808)                                  │
│  BacPipes Worker (polls every 30s)                          │
│    ↓ MQTT publish                                           │
│  MQTT Broker (10.0.60.2:1883)                               │
│    ↓ Subscribe (2 consumers)                                │
│    ├─→ Frontend SSE → Browser (real-time monitoring)        │
│    └─→ [Not connected yet - Phase 1]                        │
│                                                              │
│  PostgreSQL (config only)                                    │
│    - Devices, Points, Settings, MqttConfig                   │
│    - NO time-series data                                     │
│                                                              │
│  Frontend (Next.js + Prisma)                                 │
│    - Dashboard, Discovery, Points, Monitoring, Settings      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Missing:** Historical storage, trend visualization

---

### Phase 1 Architecture (Target: 1-2 months)

```
┌──────────────────────────────────────────────────────────────┐
│ SITE (Proxmox LXC - Docker Compose)                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  BACnet DDC → Worker → MQTT Broker                          │
│                           ↓                                  │
│                       Telegraf ← NEW                         │
│                           ↓                                  │
│                   TimescaleDB (local) ← NEW                  │
│                   - sensor_readings hypertable               │
│                   - 1 day retention                          │
│                   - Automatic compression                    │
│                           ↑                                  │
│                     Grafana ← NEW                            │
│                   - Trend dashboards                         │
│                   - Equipment performance                    │
│                   - Alert visualization                      │
│                                                              │
│  PostgreSQL (config + current state)                         │
│    - Point.currentValue (ML updates here)                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**New capabilities:**
- Historical trend viewing (last 24 hours)
- Equipment performance dashboards
- Baseline energy measurement

---

### Phase 2 Architecture (Target: 3-6 months)

```
┌──────────────────────────────────────────────────────────────┐
│ SITE (Proxmox LXC)                                           │
├──────────────────────────────────────────────────────────────┤
│  BACnet DDC → Worker → MQTT → Telegraf                      │
│                                  ↓                           │
│                          TimescaleDB (local)                 │
│                          - 1 day retention                   │
│                                  ↓                           │
│                     PostgreSQL Logical                       │
│                       Replication (SSL)                      │
│                                  ↓                           │
└──────────────────────────────────┼───────────────────────────┘
                                   │ Encrypted over Internet
                                   │ (4G LTE or broadband)
                                   ↓
┌──────────────────────────────────────────────────────────────┐
│ CENTRAL (Home DMZ or Cloud VM)                               │
├──────────────────────────────────────────────────────────────┤
│  TimescaleDB (central)                                       │
│    - 30 day retention (future: 1 year)                       │
│    - Data from all sites (future multi-site)                 │
│                                                              │
│  Grafana (central)                                           │
│    - Remote monitoring                                       │
│    - Multi-site comparison (future)                          │
│    - Historical analysis                                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**New capabilities:**
- Remote monitoring from anywhere
- Central data backup/archive
- Foundation for multi-site (future)

---

## Data Flow Explained

### Flow 1: Sensor Data Collection (Current - v0.6.1)

```
BACnet DDC Controller
  ↓ BACnet/IP read (every 30s)
BacPipes Worker
  ↓ MQTT publish
    Topic: macau-casino/pau_212/analog-input444/presentValue
    Payload: {value: 21.0, timestamp: "...", units: "percent"}
  ↓
MQTT Broker (10.0.60.2:1883)
  ↓ Subscribe
Frontend SSE endpoint
  ↓ Server-Sent Events
Browser (Monitoring page)
  → Real-time updates!
```

**Characteristics:**
- Real-time (< 1 second latency)
- No historical storage yet
- Perfect for live monitoring

---

### Flow 2: Sensor Data + Historical Storage (Phase 1)

```
BACnet DDC → Worker → MQTT Broker
                         ↓ (same as above to Frontend)
                         ↓
                     Telegraf
                       ↓ SQL INSERT
                   TimescaleDB
                     INSERT INTO sensor_readings (
                       time, point_id, value, units, quality
                     )
                       ↑ SQL queries
                     Grafana
                       → Charts, trends, dashboards
```

**Characteristics:**
- Dual consumption: Live (Frontend) + Historical (Telegraf)
- 1 day local retention
- Trend analysis capability

---

### Flow 3: BACnet Write Commands - Local (Current)

```
User clicks "Write" in Monitoring page
  ↓
Frontend POST /api/bacnet/write
  ↓ MQTT publish
    Topic: bacnet/write/command
    Payload: {pointId: 14, value: 25, priority: 8}
  ↓
MQTT Broker
  ↓ Subscribe
BacPipes Worker (write_command_handler)
  ↓ BACnet WriteProperty
BACnet DDC Controller
  → Setpoint changed! (<1 second total)
  ↓
Worker publishes result
  Topic: bacnet/write/result
  Payload: {success: true}
  ↓
Frontend displays "Write successful"
```

**Characteristics:**
- Fast (< 1 second)
- Current implementation ✅
- Perfect for manual operator adjustments

---

### Flow 4: ML Setpoint Override (Future - Phase 3)

```
ML Model decides optimal setpoint
  ↓
UPDATE Point SET currentValue = 23.0 WHERE id = 14
  ↓
PostgreSQL (Point table updated)
  ↓
Worker polls Point table (every 5 seconds)
  ↓ Detects change
Worker writes to BACnet DDC
  ↓
DDC operates at new setpoint
  ↓
Worker reads new temperature
  ↓ MQTT publish
Telegraf → TimescaleDB
  → Historical record of ML optimization
```

**Key insight:** ML updates `Point.currentValue` in PostgreSQL (NOT TimescaleDB)

---

## Database Strategy

### Two Databases, Different Purposes

| Database | Purpose | Data Type | Updates | Retention |
|----------|---------|-----------|---------|-----------|
| **PostgreSQL** | Configuration + Current State | Relational | Frequent | Permanent |
| **TimescaleDB** | Historical Measurements | Time-series | Insert-only | 1 day (site)<br>30 days (central) |

### PostgreSQL Tables:

```sql
-- Configuration (changes rarely)
Device (id, deviceName, ipAddress, enabled)
Point (id, pointName, objectType, enabled, mqttPublish)
MqttConfig (broker, port, clientId)
SystemSettings (timezone, pollInterval)

-- Current State (changes frequently)
Point.currentValue  ← ML model updates THIS
Point.lastPollTime  ← Worker updates THIS
Point.lastValue     ← Worker updates THIS
```

### TimescaleDB Hypertable:

```sql
-- Historical measurements (insert-only, millions of rows)
CREATE TABLE sensor_readings (
  time TIMESTAMPTZ NOT NULL,
  point_id INT NOT NULL,
  value REAL,
  units TEXT,
  quality TEXT CHECK (quality IN ('good', 'uncertain', 'bad')),
  device_id INT,
  object_type TEXT
);

SELECT create_hypertable('sensor_readings', 'time');
```

### Why NOT Redis?

**Redis** is an in-memory key-value store for caching "current state"

**Do you need it?**
- ✅ **YES** if: 1000+ points, multiple dashboards, sub-second queries
- ❌ **NO** if: < 100 points, single dashboard, PostgreSQL fast enough

**Current scale (5 points):** PostgreSQL `Point.lastValue` is instant. No Redis needed.

**Future scale (1000+ points):** Consider Redis for caching latest values if Grafana queries get slow.

---

## Component Stack

### Current Stack (v0.6.1)

| Service | Technology | Purpose |
|---------|-----------|---------|
| **postgres** | PostgreSQL 15 | Configuration database |
| **bacnet-worker** | Python 3.10 + BACpypes3 | BACnet polling, MQTT publishing |
| **frontend** | Next.js 15 + Prisma | Web UI (Dashboard, Discovery, Points, Monitoring, Settings) |
| **mosquitto** | Eclipse Mosquitto 2.x | MQTT broker (external: 10.0.60.2) |

---

### Phase 1 Stack (Target)

| Service | Technology | Purpose |
|---------|-----------|---------|
| **postgres** | PostgreSQL 15 | Configuration database (existing) |
| **timescaledb** | TimescaleDB 2.x | Time-series storage (NEW) |
| **telegraf** | Telegraf 1.x | MQTT → TimescaleDB writer (NEW) |
| **grafana** | Grafana 10+ | Visualization dashboards (NEW) |
| **bacnet-worker** | Python 3.10 | BACnet polling (existing) |
| **frontend** | Next.js 15 | Web UI (existing) |

### Per-Site Stack (Docker Compose)

| Service | Technology | Purpose |
|---------|-----------|---------|
| **postgres** | PostgreSQL 15 | Configuration database (devices, points, settings) |
| **timescaledb** | TimescaleDB (PostgreSQL extension) | Time-series sensor data (7-day retention) |
| **bacnet-worker** | Python 3.10 + BACpypes3 | BACnet polling, MQTT publishing, write command execution |
| **telegraf** | Telegraf 1.x | MQTT subscriber → TimescaleDB writer |
| **mosquitto** | Eclipse Mosquitto 2.x | Local MQTT broker (optional if external broker used) |
| **frontend** | Next.js 15 + Prisma | Web UI for configuration, monitoring, control |

**Deployment:**
- Single LXC container on Proxmox
- `docker-compose up -d` deploys entire stack
- Persistent volumes for data (postgres_data, timescaledb_data, mqtt_data)

### Central Server Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **TimescaleDB** | TimescaleDB (PostgreSQL) | Central aggregation (1-year retention) |
| **Grafana** | Grafana 10+ | Visualization, dashboards, alerting |
| **ML Training** | Python + PyTorch/TensorFlow | Model training on aggregated data |
| **Model Registry** | MinIO or S3-compatible | ONNX model storage and versioning |
| **API Server** | FastAPI or Django | REST API for external integrations |

**Hardware (Initial - 100 sites):**
- Dell PowerEdge R740 or equivalent
- 64GB RAM, 4TB SSD RAID 1, dual 10Gbps NICs
- Cost: ~$5K-8K (used/refurbished)

**Scaling (1000 sites):**
- 10x horizontal (10 servers) or 1x vertical (128GB RAM, 20TB storage)
- Estimated: $50K-80K total hardware

---

## Data Flow

### Flow 1: Sensor Data Collection (Site → Central)

```
[Site]
BACnet Device (DDC)
    ↓ BACnet/IP (UDP 47808)
BacPipes Worker (polls every 15-60s)
    ↓ MQTT publish (localhost:1883)
Mosquitto Broker
    ↓ MQTT subscribe
Telegraf
    ↓ SQL INSERT
TimescaleDB (local)
    ↓ PostgreSQL Logical Replication (SSL, port 5432)
    ↓ [Over 4G LTE - auto-buffers if network fails]
TimescaleDB (central)
    ↓ SQL queries
Grafana / ML Training
```

**Characteristics:**
- **Latency:** 5-30 seconds (site → central)
- **Offline resilience:** PostgreSQL WAL buffers days of data
- **Encryption:** TLS 1.3
- **Bandwidth:** ~10KB/second per site (~1MB/day per 100 points)

---

### Flow 2: BACnet Writes - Local (Real-time)

```
[Site]
Grafana/Local UI
    ↓ MQTT publish (topic: bacnet/write/command)
Mosquitto Broker
    ↓ MQTT subscribe
BacPipes Worker (write_command_handler)
    ↓ BACpypes3 WriteProperty
BACnet Device (DDC)
```

**Characteristics:**
- **Latency:** <1 second
- **Use case:** Manual operator adjustments, emergency overrides
- **Requires:** Local access to MQTT broker

---

### Flow 3: BACnet Writes - Remote (Scheduled)

```
[Central]
ML Model / API / Grafana Automation
    ↓ SQL INSERT into write_commands table
TimescaleDB (central)
    ↓ PostgreSQL Replication (bidirectional!)
    ↓ [Over 4G LTE]
TimescaleDB (local - site)
    ↓ Worker polls write_commands every 5 seconds
BacPipes Worker
    ↓ SQL UPDATE status = 'executing'
    ↓ BACpypes3 WriteProperty
BACnet Device (DDC)
    ↓ Success/Failure
    ↓ SQL UPDATE status = 'completed'/'failed'
    ↓ PostgreSQL Replication (status back to central)
TimescaleDB (central)
    ↓ Central sees result (audit trail)
```

**Characteristics:**
- **Latency:** 5-60 seconds (depends on 4G LTE + replication lag)
- **Use case:** Automated optimization, scheduled setpoint changes
- **Offline resilience:** Commands queue on both sides
- **Audit trail:** Full history in write_commands table
- **No new ports:** Uses existing replication connection

---

## Database Schema

### Configuration Database (PostgreSQL)

**Key Tables:**
- `Device` - Discovered BACnet devices
- `Point` - BACnet points with Haystack tags
- `SystemSettings` - BACnet IP, timezone, etc.
- `MqttConfig` - MQTT broker settings
- `write_commands` ← **NEW** - Remote write command queue

**write_commands Schema:**
```sql
CREATE TABLE write_commands (
  id SERIAL PRIMARY KEY,
  site_id TEXT NOT NULL,
  point_id INT NOT NULL REFERENCES "Point"(id),
  command_type TEXT NOT NULL CHECK (command_type IN ('write_value', 'release_priority')),
  value REAL,
  priority INT NOT NULL DEFAULT 8 CHECK (priority BETWEEN 1 AND 16),

  -- Status tracking
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'executing', 'completed', 'failed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  executed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  error_message TEXT,

  -- Audit trail
  created_by TEXT NOT NULL,
  source_ip TEXT,

  INDEX idx_status_site (status, site_id),
  INDEX idx_point (point_id),
  INDEX idx_created_at (created_at)
);
```

### Time-Series Database (TimescaleDB)

**Hypertable:**
```sql
CREATE TABLE sensor_readings (
  time TIMESTAMPTZ NOT NULL,
  site_id TEXT NOT NULL,
  point_id INT NOT NULL,
  value REAL,
  quality TEXT CHECK (quality IN ('good', 'uncertain', 'bad')),
  units TEXT,
  device_id INT,
  object_type TEXT,
  object_instance INT
);

SELECT create_hypertable('sensor_readings', 'time');

-- Compression (reduce storage by 10-20x)
ALTER TABLE sensor_readings SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'site_id, point_id'
);

-- Retention policy (7 days on site, 1 year on central)
SELECT add_retention_policy('sensor_readings', INTERVAL '7 days'); -- Site
SELECT add_retention_policy('sensor_readings', INTERVAL '1 year'); -- Central
```

---

## PostgreSQL Replication Setup

### Site Database (Publisher)

```sql
-- Enable logical replication
ALTER SYSTEM SET wal_level = logical;
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET max_replication_slots = 10;
ALTER SYSTEM SET wal_keep_size = '10GB'; -- Buffer for network outages

-- Restart PostgreSQL
-- systemctl restart postgresql

-- Create replication user
CREATE USER replicator WITH REPLICATION PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO replicator;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO replicator;

-- Create publication (what to replicate)
CREATE PUBLICATION site_data FOR TABLE sensor_readings, write_commands;
```

### Central Database (Subscriber)

```sql
-- Create subscription (per site)
CREATE SUBSCRIPTION site_macau_sub
  CONNECTION 'host=site-macau-ip port=5432 dbname=bacpipes user=replicator password=xxxxx sslmode=require sslcert=/path/to/client.crt sslkey=/path/to/client.key'
  PUBLICATION site_data;

-- Repeat for each site:
CREATE SUBSCRIPTION site_klcc_sub ...;
CREATE SUBSCRIPTION site_singapore_sub ...;
```

### Monitoring Replication

```sql
-- On central database
SELECT
  subname AS site,
  pid,
  received_lsn,
  latest_end_lsn,
  pg_size_pretty(pg_wal_lsn_diff(latest_end_lsn, received_lsn)) AS lag,
  EXTRACT(EPOCH FROM (NOW() - latest_end_time)) AS lag_seconds
FROM pg_stat_subscription;

-- Alert if lag > 5 minutes
SELECT subname
FROM pg_stat_subscription
WHERE EXTRACT(EPOCH FROM (NOW() - latest_end_time)) > 300;
```

---

## Security Configuration

### SSL/TLS Setup

**Generate Certificates (per site):**
```bash
# On site server
openssl req -new -x509 -days 3650 -nodes \
  -out /var/lib/postgresql/ssl/client.crt \
  -keyout /var/lib/postgresql/ssl/client.key \
  -subj "/CN=site-macau"

chmod 600 /var/lib/postgresql/ssl/client.key
chown postgres:postgres /var/lib/postgresql/ssl/*
```

**PostgreSQL Configuration (`postgresql.conf`):**
```conf
ssl = on
ssl_cert_file = '/var/lib/postgresql/ssl/server.crt'
ssl_key_file = '/var/lib/postgresql/ssl/server.key'
ssl_ca_file = '/var/lib/postgresql/ssl/ca.crt'
ssl_min_protocol_version = 'TLSv1.3'
```

**Client Authentication (`pg_hba.conf`):**
```conf
# Only allow SSL connections from known IPs
hostssl  all  replicator  203.0.113.0/24  cert  clientcert=verify-full
```

### Firewall Rules (pfsense)

```
# Allow PostgreSQL replication from site IPs only
allow tcp from 203.0.113.0/24 to central-server port 5432
deny tcp from any to central-server port 5432

# Allow sites to download ML models
allow tcp from 203.0.113.0/24 to central-server port 443
```

---

## ML Architecture

### Training (Central Server - Nightly/Weekly)

```python
# ml_training/train_hvac_model.py
import pandas as pd
import torch
from sqlalchemy import create_engine

# Read data from all sites (last 30 days)
engine = create_engine("postgresql://central-db")
df = pd.read_sql("""
    SELECT * FROM sensor_readings
    WHERE time > NOW() - INTERVAL '30 days'
      AND site_id IN ('macau', 'klcc', 'singapore')
""", engine)

# Train model
model = train_pytorch_model(df)

# Export to ONNX
torch.onnx.export(model, dummy_input, "models/hvac_v2.onnx")

# Upload to model registry
upload_to_s3("hvac_v2.onnx", bucket="ml-models")

print("✅ Model trained and deployed!")
```

### Inference (Edge - Real-time)

```python
# edge_inference/predict.py
import onnxruntime as ort
import psycopg2

# Load model
session = ort.InferenceSession("hvac_model.onnx")

# Read recent sensor data
conn = psycopg2.connect("postgresql://localhost/bacpipes")
sensor_data = get_recent_readings(conn)

# Predict optimal setpoint
prediction = session.run(None, {input_name: sensor_data})

# Write to BACnet via command queue
write_command(
    site_id="macau",
    point_id=14,  # Cooling setpoint
    value=prediction[0],
    priority=8,
    created_by="ml_model_v2"
)
```

**Model Update Process:**
1. Central server trains nightly (if new data available)
2. Uploads ONNX model to S3/MinIO
3. Sites check for new model daily (HTTP GET)
4. Download if version changed
5. Hot-swap model (no restart)

---

## Implementation Phases

### Phase 1: Local Time-Series Storage & Visualization (Target: 1-2 months)

**Goal:** Add historical data storage and Grafana dashboards to current single-site deployment

**Current State (v0.6.1):**
- ✅ BACnet discovery and polling (2 devices, 5 active points)
- ✅ MQTT publishing to external broker (10.0.60.2)
- ✅ Real-time monitoring via SSE
- ✅ BACnet write commands via MQTT
- ❌ No historical data storage
- ❌ No trend visualization

**Phase 1 Tasks:**
- [ ] Add `timescaledb` service to docker-compose.yml
- [ ] Add `telegraf` service to docker-compose.yml
- [ ] Add `grafana` service to docker-compose.yml
- [ ] Create TimescaleDB hypertable for sensor_readings
- [ ] Configure Telegraf (MQTT input → TimescaleDB output)
- [ ] Update frontend Settings page (add TimescaleDB/Grafana config)
- [ ] Create Grafana dashboards:
  - [ ] Equipment performance dashboard (AHU, chillers)
  - [ ] Point trend charts (last 24 hours)
  - [ ] System health dashboard
- [ ] Set up 1-day data retention policy
- [ ] Test data persistence after container restart
- [ ] Test offline buffering (disconnect MQTT, verify catch-up)

**Deliverables:**
- All sensor data written to local TimescaleDB (1-day retention)
- Grafana accessible at http://localhost:3002
- Equipment performance dashboards operational
- Baseline energy consumption measured
- Foundation for future ML optimization

**Success Criteria:**
```bash
# Verify TimescaleDB data
docker exec -it bacpipes-timescaledb psql -U anatoli -d timescaledb
SELECT COUNT(*) FROM sensor_readings;  -- Should show thousands of rows

# Verify Grafana dashboards
# Open http://localhost:3002
# Should see equipment trends, no errors
```

---

### Phase 2: Remote Monitoring & Central Database (Target: 3-6 months)

**Goal:** Enable remote monitoring from home/cloud with secure PostgreSQL replication

**Prerequisites:**
- Phase 1 complete (local TimescaleDB operational)
- Central server provisioned (Home DMZ or cloud VM)
- SSL certificates configured
- Firewall port 5432 forwarded

**Phase 2 Tasks:**
- [ ] Provision central server (Home DMZ or small cloud VM)
- [ ] Install TimescaleDB on central server
- [ ] Configure PostgreSQL SSL/TLS certificates
- [ ] Create publication on site database
- [ ] Create subscription on central database
- [ ] Configure firewall rules (allow port 5432 from site IP)
- [ ] Test replication (insert test row, verify on central)
- [ ] Test network failure recovery (disconnect, reconnect, verify WAL catch-up)
- [ ] Set up replication monitoring dashboard
- [ ] Install Grafana on central server
- [ ] Configure Grafana to query central TimescaleDB
- [ ] Test remote access via HTTPS
- [ ] Extend central retention to 30 days

**Deliverables:**
- Site data replicates to central database (< 30 second lag)
- Central Grafana accessible remotely
- 30-day historical data on central (vs 1-day on site)
- Automatic recovery from network outages
- Secure encrypted data transmission (no VPN needed)

**Success Criteria:**
```bash
# On central server
psql -U anatoli -d timescaledb
SELECT COUNT(*) FROM sensor_readings;  -- Should match site database

# Monitor replication lag
SELECT subname,
       EXTRACT(EPOCH FROM (NOW() - latest_end_time)) AS lag_seconds
FROM pg_stat_subscription;
-- Should show < 30 seconds
```

---

### Phase 3: ML Optimization (Future - After 3+ months of baseline data)

**Goal:** Deploy machine learning models for energy optimization

**Prerequisites:**
- Phase 2 complete (90+ days of historical data)
- Baseline energy consumption measured
- Equipment operating patterns understood

**Phase 3 Tasks:**
- [ ] Export 90-day dataset from TimescaleDB
- [ ] Train initial HVAC optimization model (Python notebook)
- [ ] Validate model performance (A/B test simulation)
- [ ] Export to ONNX format
- [ ] Update worker to poll `Point.currentValue` field
- [ ] Implement ML override logic in worker
- [ ] Deploy model to site (test mode - no writes)
- [ ] Monitor predictions vs actual for 2 weeks
- [ ] Enable ML writes (priority 8)
- [ ] A/B test: ML-optimized vs baseline
- [ ] Measure energy savings
- [ ] Document model versioning and rollback

**Deliverables:**
- Proven ML model reducing energy consumption 10-20%
- Safe override mechanism (ML updates PostgreSQL, worker writes to BACnet)
- Automatic rollback if performance degrades
- Foundation for multi-site deployment (future)

---

## Operational Considerations

### Backup Strategy

**Site Databases:**
- Automated daily backups (pg_dump)
- 7-day retention locally
- Upload to central S3/MinIO

**Central Database:**
- Continuous WAL archiving
- Daily full backups
- 30-day retention
- Off-site backup (cloud or secondary data center)

**Docker Volumes:**
- Daily snapshots of postgres_data, timescaledb_data
- Stored on separate disk (RAID 1)

### Monitoring & Alerting

**Metrics to Monitor:**
- Replication lag (per site)
- Write command latency
- BACnet read success rate
- MQTT message throughput
- Database size growth
- Disk space usage
- CPU/RAM utilization

**Alert Thresholds:**
- Replication lag > 5 minutes
- Write command failure rate > 5%
- BACnet read failure rate > 10%
- Disk space < 20% free
- Database not responding > 1 minute

**Alerting Channels:**
- Telegram bot (real-time)
- Email (digest + critical)
- SMS (critical only)
- PagerDuty (on-call escalation)

### Disaster Recovery

**Site Failure:**
- Central retains all historical data (1 year)
- Deploy new LXC container
- Restore from backup
- Reconfigure replication
- RTO: 4 hours

**Central Failure:**
- Sites continue operating independently (edge ML, local control)
- Deploy standby server
- Restore from backup
- Reconfigure subscriptions
- RTO: 8 hours


---

## Alternative Technologies Considered (and Why Not Chosen)

### InfluxDB vs TimescaleDB
**Why TimescaleDB:**
- ✅ Built-in replication (InfluxDB = enterprise feature, $7K+/year)
- ✅ Already using PostgreSQL (Prisma)
- ✅ SQL queries (no learning curve)

### EMQX vs Mosquitto
**Why Mosquitto:**
- ✅ Simpler (one config file)
- ✅ Proven at scale (Facebook, AWS IoT)
- ✅ Sufficient for 1000 sites with local brokers
- ⏳ Upgrade to EMQX if central MQTT aggregation needed

### MQTT Bridging vs PostgreSQL Replication
**Why PostgreSQL:**
- ✅ No new ports (already using 5432 for replication)
- ✅ Automatic buffering (WAL)
- ✅ Bidirectional (commands + data)
- ✅ Built-in audit trail

### Cloud vs Physical Servers
**Why Physical (initially):**
- ✅ No cloud budget yet
- ✅ Break-even at ~800 sites
- ✅ Data sovereignty (some countries require local storage)
- ⏳ Migrate to cloud at 500+ sites if operational costs justify

---

## Success Metrics

### Phase 1 Success Criteria (Local Time-Series Storage)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Data Collection** | >99% | Successful BACnet reads / total attempts |
| **MQTT Publishing** | >99.5% | Messages published / messages attempted |
| **Data Persistence** | 100% | No data loss after container restarts |
| **TimescaleDB Write** | >99% | Telegraf successful inserts |
| **Query Performance** | <1 second | Grafana dashboard load time |
| **1-Day Retention** | Verified | Old data auto-deleted after 24 hours |
| **Point Coverage** | 50+ points | All discovered points configured |
| **Polling Accuracy** | ±5 seconds | Actual vs configured poll interval |

### Phase 2 Success Criteria (Remote Monitoring)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Replication Lag** | <30 seconds | pg_stat_subscription.lag_seconds |
| **Network Resilience** | 100% recovery | WAL buffer survives 24hr outage |
| **Central Uptime** | >99.5% | Central server availability |
| **Data Completeness** | >99% | Central data matches site data |
| **Remote Access** | <2 seconds | Grafana dashboard load (via HTTPS) |
| **30-Day Retention** | Verified | Central database retains full month |
| **SSL Security** | 100% | All traffic TLS 1.3 encrypted |

### Phase 3 Success Criteria (ML Optimization)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Energy Savings** | 10-20% | kWh after ML vs baseline (90-day avg) |
| **Model Accuracy** | >85% | Predictions vs actual outcomes |
| **Override Safety** | 100% | No equipment damage from ML writes |
| **Rollback Speed** | <5 minutes | Detect bad model → rollback |
| **Baseline Measurement** | 90+ days | Sufficient data before ML deployment |
| **A/B Test Duration** | 14+ days | Statistical significance achieved |

### Overall System Health

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Worker Uptime** | >99.9% | Docker container availability |
| **BACnet Network** | <1% errors | Failed reads / total reads |
| **Database Health** | <80% disk | Disk usage monitoring |
| **MQTT Broker** | >99.9% | External broker availability |

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **BACnet network failure** | No data collection | Medium | Worker auto-reconnect, error logging, alerts |
| **MQTT broker failure** | Data loss | Low | External broker (high availability), worker buffers locally |
| **PostgreSQL corruption** | Config loss | Very Low | Daily backups, Docker volume snapshots |
| **TimescaleDB disk full** | Cannot write data | Medium | 1-day retention policy, disk monitoring, auto-cleanup |
| **Worker crash** | Polling stops | Low | Docker auto-restart, health checks, systemd monitoring |
| **ML model degrades performance** | Increased energy use | Medium (Phase 3) | A/B testing, automatic rollback, baseline comparison |
| **Network isolation** | Cannot reach BACnet devices | Low | Same subnet deployment, network monitoring |
| **Data loss during restart** | Gap in historical data | Low | Graceful shutdown, MQTT persistence, WAL buffering |

---

## Future Enhancements (Phase 7+)

### Multi-Tenant SaaS Platform
- White-label BacPipes for resellers
- Per-tenant data isolation
- Billing/metering integration
- RESTful API for external apps

### Advanced ML Features
- Anomaly detection (predictive maintenance)
- Fault diagnosis (root cause analysis)
- Demand response (grid integration)
- Weather-based optimization

### Mobile App
- iOS/Android app for field technicians
- Offline configuration
- Push notifications (alerts)
- QR code scanning (equipment pairing)

### Enhanced Security
- Role-based access control (RBAC)
- Audit logs (compliance)
- Two-factor authentication (2FA)
- SOC 2 compliance

---

## Appendix

### Glossary

- **BACnet:** Building Automation and Control Networks (ISO 16484-5)
- **DDC:** Direct Digital Controller (HVAC equipment controller)
- **HVAC:** Heating, Ventilation, and Air Conditioning
- **LXC:** Linux Containers (lightweight virtualization)
- **MQTT:** Message Queuing Telemetry Transport (pub/sub protocol)
- **ONNX:** Open Neural Network Exchange (ML model format)
- **WAL:** Write-Ahead Log (PostgreSQL transaction log)

### References

- [PostgreSQL Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [BACpypes3 GitHub](https://github.com/JoelBender/bacpypes3)
- [MQTT Specification](https://mqtt.org/mqtt-specification/)
- [ONNX Runtime](https://onnxruntime.ai/)

---

**Document Maintained By:** BacPipes Development Team
**Last Updated:** 2025-11-08 (v2.0 - Single Site Focus)
**Next Review:** After Phase 1 completion (TimescaleDB + Grafana deployment)

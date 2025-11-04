# BacPipes Strategic Architecture Plan

**Version:** 1.0
**Date:** 2025-11-04
**Status:** Approved for Implementation

---

## Executive Summary

BacPipes will evolve into a distributed, multi-site BMS data collection and optimization platform capable of managing 100-1000+ buildings across different countries. The architecture prioritizes reliability, security, offline resilience, and zero cloud dependency in early phases.

### Key Design Decisions:
- ✅ **PostgreSQL Replication** for site-to-central data sync (not MQTT over WAN)
- ✅ **TimescaleDB** for time-series storage (extends PostgreSQL)
- ✅ **Docker Compose** deployment (entire stack in one LXC container)
- ✅ **Hybrid ML** (train centrally, infer at edge)
- ✅ **Bidirectional writes** via PostgreSQL command queue
- ✅ **Physical servers** initially (cloud migration after scale/budget)

---

## System Requirements

### Scale
- **Target:** 100-1000+ buildings
- **Points per building:** 50-500 BACnet points
- **Polling frequency:** 15-60 seconds per point
- **Expected throughput:** 10K-100K sensor readings/minute (aggregated)

### Network
- **Site connectivity:** 4G LTE (ISP managed)
- **Bandwidth:** ~1-10 Mbps per site (sufficient for time-series data)
- **Latency:** 50-200ms to central server
- **Reliability:** Must handle multi-hour outages gracefully

### Security
- **Data in transit:** TLS encryption (PostgreSQL SSL, HTTPS)
- **Authentication:** Client certificates for database replication
- **No VPN for data flow:** VPN (Tailscale) only for admin/troubleshooting
- **Firewall:** pfsense on Proxmox (allow port 5432 from known IPs)

### Budget Constraints
- **Phase 1-2:** No cloud budget (physical servers)
- **Phase 3+:** Consider cloud migration if operational costs justify it

---

## Architecture Overview

### Deployment Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                      SITE 1 (Proxmox LXC)                       │
│  Docker Compose: postgres, timescaledb, bacnet-worker,         │
│                  telegraf, mosquitto, frontend                  │
└────────────────┬────────────────────────────────────────────────┘
                 │ PostgreSQL Replication (SSL, port 5432)
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│               CENTRAL (Physical Servers)                        │
│  TimescaleDB (master), Grafana, ML Training, API                │
└────────────────┬────────────────────────────────────────────────┘
                 │ Model deployment (ONNX via HTTP/S3)
                 ↓
           [Sites download models for edge inference]
```

---

## Component Stack

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

### Phase 1: Local Time-Series Storage (Weeks 1-2)

**Goal:** Add TimescaleDB and Telegraf to Docker Compose stack

**Tasks:**
- [ ] Add `timescaledb` service to docker-compose.yml
- [ ] Add `telegraf` service to docker-compose.yml
- [ ] Create TimescaleDB hypertable for sensor_readings
- [ ] Configure Telegraf (MQTT input → PostgreSQL output)
- [ ] Update frontend Settings page (TimescaleDB config section)
- [ ] Test: BacPipes → MQTT → Telegraf → TimescaleDB
- [ ] Verify data persists after container restart
- [ ] Test offline buffering (stop Telegraf, restart, verify catch-up)

**Deliverables:**
- All sensor data written to local TimescaleDB
- Grafana can query local data (localhost:5432)
- 7-day retention policy active

---

### Phase 2: Central Replication (Weeks 3-4)

**Goal:** Sync data from site to central server

**Tasks:**
- [ ] Provision central physical server (or VM for testing)
- [ ] Install TimescaleDB on central
- [ ] Configure SSL certificates (site + central)
- [ ] Create publication on site database
- [ ] Create subscription on central database
- [ ] Configure firewall rules (pfsense)
- [ ] Test replication (insert row on site, verify on central)
- [ ] Test network failure (unplug Ethernet, verify WAL buffering)
- [ ] Set up monitoring (pg_stat_subscription dashboard)
- [ ] Document replication lag alerts

**Deliverables:**
- Real-time data sync (< 30 second lag)
- Automatic recovery from network outages
- Central database has data from all sites

---

### Phase 3: Remote Write Commands (Weeks 5-6)

**Goal:** Control BACnet devices from central server

**Tasks:**
- [ ] Create `write_commands` table (Prisma schema + migration)
- [ ] Update worker to poll `write_commands` table
- [ ] Implement `execute_write_command()` function
- [ ] Test local writes (insert command, verify execution)
- [ ] Test remote writes (insert on central, verify execution on site)
- [ ] Add write command API endpoint (`/api/bacnet/write`)
- [ ] Create frontend UI for manual writes
- [ ] Add audit trail dashboard (Grafana)

**Deliverables:**
- Central server can send write commands to any site
- 5-60 second latency (acceptable for HVAC)
- Full audit trail (who, when, what, result)

---

### Phase 4: Grafana Dashboards (Week 7)

**Goal:** Visualization and monitoring

**Tasks:**
- [ ] Install Grafana on central server
- [ ] Connect to central TimescaleDB
- [ ] Create site overview dashboard (all buildings)
- [ ] Create equipment drill-down dashboard (per AHU/chiller)
- [ ] Create replication lag dashboard
- [ ] Create write command history dashboard
- [ ] Set up alerts (Telegram, email, SMS)
- [ ] Document dashboard templates

**Deliverables:**
- Real-time building performance dashboards
- Alerting for offline sites or failed writes
- Exportable dashboard JSON templates

---

### Phase 5: Edge ML Inference (Weeks 8-10)

**Goal:** Deploy ML models to edge for real-time optimization

**Tasks:**
- [ ] Train initial HVAC model (Python notebook)
- [ ] Export to ONNX format
- [ ] Create inference Docker service
- [ ] Test inference on sample data
- [ ] Integrate with write_commands table
- [ ] Deploy to one pilot site
- [ ] Monitor for 2 weeks (A/B test vs baseline)
- [ ] Measure energy savings
- [ ] Document model versioning process

**Deliverables:**
- One pilot site running ML-optimized setpoints
- Measurable energy savings (target: 10-20%)
- Proven model deployment pipeline

---

### Phase 6: Multi-Site Rollout (Weeks 11-16)

**Goal:** Scale to 10-100 sites

**Tasks:**
- [ ] Create site deployment playbook (Ansible/Terraform)
- [ ] Automate LXC container creation
- [ ] Automate Docker Compose deployment
- [ ] Automate PostgreSQL replication setup
- [ ] Create site onboarding checklist
- [ ] Train field technicians (deployment procedure)
- [ ] Deploy to 10 pilot sites
- [ ] Monitor for 1 month
- [ ] Refine based on feedback
- [ ] Scale to 100 sites

**Deliverables:**
- 100 sites live with data flowing to central
- <5% downtime across fleet
- <1 hour deployment time per site

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

## Cost Analysis

### Initial Setup (100 Sites)

| Item | Cost | Notes |
|------|------|-------|
| Central Server (physical) | $8,000 | Dell R740, 64GB RAM, 4TB SSD |
| Network (4G LTE per site) | $20/site/month | ISP managed, 10GB data/month |
| SSL Certificates | $500/year | Wildcard cert for all sites |
| Backup Storage (S3) | $100/month | 5TB, 30-day retention |
| **Total First Year** | **$32,500** | $8K hardware + $24K connectivity + $500 SSL |

### Ongoing Costs (per year, 100 sites)

| Item | Cost | Notes |
|------|------|-------|
| 4G LTE (100 sites) | $24,000 | $20/site/month × 100 × 12 |
| Backup Storage | $1,200 | $100/month |
| SSL Renewal | $500 | Annual |
| **Total Annual** | **$25,700** | Mainly connectivity |

### Scaling to 1000 Sites

| Item | Cost | Notes |
|------|------|-------|
| Central Servers (10×) | $80,000 | Horizontal scaling |
| 4G LTE (1000 sites) | $240,000/year | $20/site/month |
| Backup Storage | $5,000/year | 50TB |
| **Total First Year** | **$325,000** | $80K hardware + $240K/year connectivity |

### Cloud Comparison (AWS)

**100 sites:**
- RDS (db.r6g.4xlarge): $3,000/month
- EC2 (Grafana/ML): $500/month
- S3 Storage: $100/month
- **Total: $43,200/year** (vs $25,700 physical)

**1000 sites:**
- RDS cluster: $15,000/month
- EC2 fleet: $3,000/month
- **Total: $216,000/year** (vs $240,000 physical)

**Break-even: ~800 sites** (cloud becomes cheaper at scale)

**Recommendation:** Physical servers for Phase 1-2, evaluate cloud at 500+ sites.

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

### Technical KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Data Availability** | >99.5% | Time series completeness |
| **Replication Lag** | <30 seconds | pg_stat_subscription |
| **Write Command Latency** | <60 seconds | write_commands.completed_at - created_at |
| **BACnet Read Success** | >95% | successful_reads / total_reads |
| **Deployment Time** | <1 hour | Site onboarding to data flowing |

### Business KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Energy Savings** | 10-20% | kWh before/after ML optimization |
| **Uptime** | >99% | Site availability (24×7) |
| **TCO per Site** | <$300/year | Connectivity + maintenance |
| **Payback Period** | <12 months | Energy savings vs deployment cost |

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **4G network outages** | Data loss | Medium | PostgreSQL WAL buffering (days) |
| **Central server failure** | No dashboards | Low | Sites continue autonomously, standby server |
| **PostgreSQL replication bug** | Data corruption | Very Low | Daily backups, WAL archiving |
| **ML model degrades performance** | Increased energy use | Medium | A/B testing, automatic rollback |
| **Scaling beyond 1000 sites** | Performance | Medium | Horizontal sharding, cloud migration |

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
**Last Updated:** 2025-11-04
**Next Review:** 2025-12-04 (after Phase 1 completion)

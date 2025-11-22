# BacPipes Development Roadmap

**Last Updated**: 2025-11-21
**Current Status**: Production-ready for single-site deployment with external MQTT architecture

---

## Completed Milestones ✅

### Phase 1: Foundation & Core Features (Completed 2025-11-21)
- ✅ Full-stack Docker Compose application
- ✅ Next.js 15 frontend with TypeScript
- ✅ PostgreSQL database with Prisma ORM
- ✅ BACnet discovery via web UI
- ✅ Point management and configuration
- ✅ Haystack tagging system (8-field semantic naming)
- ✅ MQTT publishing to external broker
- ✅ TimescaleDB time-series storage
- ✅ Monitoring dashboard (port 3003)
- ✅ BACnet write command support
- ✅ Priority array control

### Phase 2: Modular Architecture Migration (Completed 2025-11-21)
- ✅ Separated MQTT broker to dedicated LXC container (10.0.60.3)
- ✅ Removed internal MQTT broker from Docker Compose
- ✅ Database-driven MQTT configuration
- ✅ Dual configuration update (.env + database)
- ✅ Verified external broker connectivity
- ✅ Updated comprehensive documentation

### Phase 3: Monitoring Stack (Completed 2025-11-21)
- ✅ TimescaleDB hypertable for sensor_readings
- ✅ Telegraf MQTT consumer (custom Python bridge)
- ✅ Monitoring dashboard on port 3003
- ✅ CSV export functionality
- ✅ Time-range selection
- ✅ Real-time point value display

---

## Current Architecture

```
┌─────────────────────────────────────────────┐
│ LXC: bacpipes-discovery (192.168.1.35)     │
├─────────────────────────────────────────────┤
│  Frontend (Next.js) - Port 3001             │
│  PostgreSQL - Port 5434                     │
│  BACnet Worker (Python/BAC0)                │
│  TimescaleDB - Port 5435                    │
│  Telegraf (MQTT → TimescaleDB)              │
│  Monitoring Dashboard - Port 3003           │
└─────────────────────────────────────────────┘
                  ↓ MQTT publish
┌─────────────────────────────────────────────┐
│ LXC: mqtt-broker (10.0.60.3)                │
├─────────────────────────────────────────────┤
│  Mosquitto MQTT Broker - Port 1883          │
│  MQTT Bridge → Remote (10.0.80.3)           │
└─────────────────────────────────────────────┘
                  ↓ MQTT bridge
┌─────────────────────────────────────────────┐
│ LXC: remote-mqtt-broker (10.0.80.3)         │
├─────────────────────────────────────────────┤
│  Mosquitto MQTT Broker - Port 1883          │
│  (Aggregates data from all sites)           │
└─────────────────────────────────────────────┘
                  ↓ MQTT subscribe
┌─────────────────────────────────────────────┐
│ LXC/Docker: bacpipes-remote (10.0.80.2)     │
├─────────────────────────────────────────────┤
│  Remote Monitoring Dashboard                │
│  TimescaleDB (Aggregated Data)              │
│  Telegraf (MQTT → TimescaleDB)              │
└─────────────────────────────────────────────┘
```

**Key Characteristics**:
- Modular LXC-based deployment
- External MQTT broker for high availability
- Separate time-series storage (TimescaleDB)
- Full BACnet point discovery and publishing
- Web-based configuration (no CSV editing)
- Database-driven polling configuration

---

## Short-Term Roadmap (Next 3 Months)

### Immediate Improvements

#### 1. Enhanced Monitoring (Priority: High)
- [ ] Add Grafana dashboards for visual analytics
- [ ] Create pre-built panels for common metrics
- [ ] Implement alerting rules (temperature thresholds, offline devices)
- [ ] Add trend analysis (7-day, 30-day patterns)
- [ ] Integration with external monitoring systems (Prometheus/Grafana)

#### 2. Data Quality & Retention (Priority: High)
- [ ] Implement TimescaleDB compression policies (automatic after 7 days)
- [ ] Configure retention policies (default: 90 days, configurable)
- [ ] Add data quality indicators (good/uncertain/bad)
- [ ] Implement outlier detection
- [ ] Add data validation rules

#### 3. User Authentication & Security (Priority: Medium)
- [ ] Add authentication to web UI (NextAuth.js)
- [ ] Role-based access control (viewer, operator, admin)
- [ ] API key management for external integrations
- [ ] MQTT authentication (username/password)
- [ ] Audit logging for configuration changes

#### 4. Enhanced BACnet Features (Priority: Medium)
- [ ] Support for BACnet trends (historical data from devices)
- [ ] Support for BACnet schedules (read/write)
- [ ] Support for BACnet alarms and events
- [ ] COV (Change of Value) subscription support
- [ ] BACnet device grouping and organization

---

## Mid-Term Roadmap (3-6 Months)

### Multi-Site Management

#### 1. Site-to-Remote Data Synchronization
**Architecture**:
```
┌─────────────────────────────────────┐
│ Site 1 (Current Site)               │
│  - bacpipes-discovery (192.168.1.35)│
│  - Local MQTT (10.0.60.3)           │
└─────────────────────────────────────┘
              ↓ MQTT Bridge
┌─────────────────────────────────────┐
│ Remote HQ (10.0.80.x)               │
│  - Remote MQTT Broker (10.0.80.3)   │
│  - Aggregated TimescaleDB           │
│  - Multi-site Dashboard (10.0.80.2) │
└─────────────────────────────────────┘
              ↑ MQTT Bridge (Future)
┌─────────────────────────────────────┐
│ Site 2 (Future)                     │
│  - bacpipes-discovery (TBD)         │
│  - Local MQTT (TBD)                 │
└─────────────────────────────────────┘
```

**Features**:
- [ ] MQTT bridge configuration (local → remote)
- [ ] Site identifier in MQTT topics (`site_id/equipment/point`)
- [ ] Central dashboard showing all sites
- [ ] Per-site filtering and navigation
- [ ] Aggregated analytics across sites

#### 2. Enhanced Configuration Management
- [ ] Configuration templates (AHU, FCU, Chiller presets)
- [ ] Bulk import/export (CSV, JSON, Excel)
- [ ] Configuration versioning (track changes over time)
- [ ] Clone configuration between sites
- [ ] Configuration backup/restore

#### 3. Advanced Analytics
- [ ] Equipment performance metrics (runtime hours, start/stop counts)
- [ ] Energy consumption tracking
- [ ] Efficiency calculations (COP, kW/ton)
- [ ] Fault detection and diagnostics (FDD)
- [ ] Predictive maintenance alerts

---

## Long-Term Roadmap (6-12 Months)

### Enterprise Features

#### 1. Machine Learning Integration
- [ ] Anomaly detection (sensor drift, unusual patterns)
- [ ] Energy optimization recommendations
- [ ] Predictive maintenance (equipment failure prediction)
- [ ] Occupancy pattern learning
- [ ] Setpoint optimization

#### 2. Integration Ecosystem
- [ ] RESTful API for external systems
- [ ] GraphQL API for flexible queries
- [ ] Webhook support for events
- [ ] IFTTT/Zapier-style automation rules
- [ ] Integration with BMS systems (Tridium, Siemens, JCI)

#### 3. Advanced Scheduling
- [ ] Web-based schedule editor (weekly, exception, calendar)
- [ ] Holiday calendar management
- [ ] Occupancy-based scheduling
- [ ] Demand response integration
- [ ] Energy pricing integration (peak/off-peak)

#### 4. Mobile Application
- [ ] Native iOS/Android apps
- [ ] Push notifications for alarms
- [ ] Mobile-optimized dashboard
- [ ] Offline mode (cached data)
- [ ] QR code scanning for equipment identification

---

## Technical Debt & Improvements

### Code Quality
- [ ] Add comprehensive unit tests (frontend)
- [ ] Add integration tests (API routes)
- [ ] Add end-to-end tests (Playwright/Cypress)
- [ ] Improve TypeScript coverage (strict mode)
- [ ] Add API documentation (OpenAPI/Swagger)

### Performance Optimization
- [ ] Implement Redis caching (point values, device status)
- [ ] Optimize database queries (indexing, query analysis)
- [ ] Add GraphQL for efficient data fetching
- [ ] Implement server-side pagination
- [ ] Add connection pooling for BACnet worker

### Infrastructure
- [ ] Add Docker health checks for all services
- [ ] Implement graceful shutdown for all services
- [ ] Add automated database backups
- [ ] Implement log rotation and aggregation
- [ ] Add container resource limits (CPU, memory)

### Developer Experience
- [ ] Add hot-reload for worker service
- [ ] Improve error messages and logging
- [ ] Add development seed data
- [ ] Create developer documentation
- [ ] Add VS Code debug configurations

---

## Known Issues & Limitations

### Current Limitations
1. **Single BACnet Network**: Only supports devices on same network (192.168.1.0/24)
   - Future: Support for BACnet/IP routing (BBMD)
   - Future: Support for BACnet/SC (secure connect)

2. **No Authentication**: Web UI is open to anyone on network
   - Mitigation: Deploy on trusted network only
   - Roadmap: Add NextAuth.js authentication

3. **Manual Haystack Tagging**: Requires user to tag each point
   - Roadmap: Add AI-assisted tagging (pattern recognition)
   - Roadmap: Add tagging templates

4. **Limited Write Command Validation**: Trusts user input
   - Roadmap: Add value range validation
   - Roadmap: Add confirmation dialogs for critical writes

5. **No Multi-User Support**: Single database, no user isolation
   - Roadmap: Add user management and RBAC

### Performance Considerations
- **Polling Interval**: Current default 60 seconds
  - Can be reduced to 10-30 seconds for critical points
  - Not recommended <10 seconds (network overhead)

- **Database Growth**: TimescaleDB grows ~1MB/day per 100 points
  - Implement compression (10x reduction)
  - Configure retention policies

- **MQTT Message Rate**: ~1 msg/second per enabled point
  - Current architecture handles 500+ points easily
  - For 1000+ points, consider batching

---

## Community & Contribution

### Documentation Needs
- [ ] Video tutorials (discovery, configuration, monitoring)
- [ ] API usage examples
- [ ] Best practices guide
- [ ] Troubleshooting wiki
- [ ] Haystack tagging guide

### Future Open Source
- [ ] Publish to GitHub (when ready)
- [ ] Add contribution guidelines
- [ ] Create issue templates
- [ ] Set up CI/CD (automated testing)
- [ ] Add code of conduct

---

## Version History

### v1.0.0 (2025-11-21) - Production Release
- Full-stack Docker Compose application
- BACnet discovery and point management
- Haystack tagging system
- MQTT publishing (external broker)
- TimescaleDB time-series storage
- Monitoring dashboard
- BACnet write commands
- Modular LXC architecture

### Future Releases

**v1.1.0** (Planned: Q1 2026)
- Authentication and RBAC
- Grafana dashboards
- Data retention policies
- Enhanced monitoring

**v1.2.0** (Planned: Q2 2026)
- Multi-site management
- MQTT bridging
- Configuration templates
- Advanced analytics

**v2.0.0** (Planned: Q3 2026)
- Machine learning integration
- Mobile application
- BACnet trends/schedules/alarms
- Enterprise features

---

## Migration Notes

### From Legacy CSV Workflow
- Old 5-stage Python pipeline fully replaced
- CSV files replaced by PostgreSQL database
- Manual tagging replaced by web UI
- All functionality preserved and enhanced

### From Internal MQTT Broker
- Completed 2025-11-21
- See MIGRATION_TO_MODULAR_ARCHITECTURE.md for details
- External broker provides high availability
- Supports multi-instance deployment

---

**Questions? Issues?**
Repository: http://10.0.10.2:30008/ak101/dev-bacnet-discovery-docker
Branch: `development` (active), `main` (production), `legacy-csv-workflow` (archived)

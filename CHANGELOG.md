# Changelog

All notable changes to BacPipes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.1] - 2025-11-08

### Added

#### Dashboard
- New Dashboard page (`/`) with system overview
- Real-time statistics (devices, points, publishing status)
- System status indicator (operational/degraded/error)
- Configuration summary cards (BACnet, MQTT, System)
- Discovered devices list with point counts
- Recent point values table (top 10 most recent)
- Quick navigation links to all pages
- Auto-refresh every 10 seconds
- Dashboard summary API endpoint (`/api/dashboard/summary`)

#### UI Improvements
- Icons added to all pages (Dashboard, Discovery, Points, Monitoring)
- Consistent color scheme across application:
  - Blue: Network/Infrastructure/Discovery
  - Green: Success/MQTT/Active
  - Red: Error/Inactive
  - Purple: Monitoring/Live data
  - Amber: Devices/Hardware
  - Cyan: Data/Points
- Left border color accents on cards for visual hierarchy
- Professional lucide-react icons throughout
- Navigation component with active route highlighting
- Page headers with descriptive icons

### Fixed
- **MQTT Configuration Loading**: Worker now reads MQTT broker address from database (Settings GUI) instead of `.env` file
  - Settings GUI is now the source of truth for MQTT configuration
  - `.env` file serves as fallback default only
  - Changes in Settings page take effect after worker restart
- Batch publishing configuration correctly loaded from database

### Changed
- Disabled batch publishing by default (can be re-enabled in Settings)
- MQTT configuration loading order: Database → Environment variables
- Worker logs now show "MQTT Broker from database" when loading from Settings GUI

### Documentation
- Clarified batch publishing use cases (ML/AI vs monitoring)
- Documented MQTT configuration hierarchy
- Added explanation of synchronized timestamps in individual topics

## [0.6.0] - 2025-11-07

### Added

#### Phase 5: Monitoring Dashboard
- Real-time MQTT data streaming via Server-Sent Events (SSE)
- Live monitoring page at `/monitoring`
- In-place value updates (stable rows, no scrolling)
- Natural webpage scrolling with sticky table headers
- Topic filtering and search
- Pause/resume data stream
- Connection status indicators (green/yellow/red)
- Unique points counter

#### Phase 6: BACnet Write Commands
- Write command UI in monitoring page
- Write button for all points (with warning for non-writable points)
- Priority level selector (1-16, default: 8)
- Priority release functionality
- Write result feedback (success/error messages)
- Direct presentValue writes (no priority array complexity)
- Support for all object types (AI, AO, AV, BI, BO, BV, MSV, etc.)
- MQTT-based write command architecture
- Write job ID tracking
- Queue-based command processing in worker

#### Timezone Support
- Configurable timezone in Settings page
- 500+ IANA timezones supported
- Worker loads timezone from database on startup
- MQTT timestamps use configured timezone
- Monitoring page displays timestamps from worker (no local override)

### Changed
- Monitoring page timestamp handling (uses worker's timestamp instead of frontend server time)
- SSE endpoint now preserves original MQTT timestamps
- Updated milestone tracking (M1-M6 complete)
- Improved documentation in README.md

### Fixed
- MQTT write command threading issue (callback → queue → async loop)
- BACnet write "property-is-not-an-array" errors (removed priority array logic)
- Monitoring page scrolling UX (removed fixed-height container)
- Timezone changes now reflected in MQTT timestamps
- Worker restart now properly loads new timezone
- Stable table rows prevent UI jumping during writes

### Technical Details

**Architecture:**
- Frontend (Next.js 15) → API `/api/bacnet/write` → MQTT `bacnet/write/command`
- Worker MQTT callback → Queue → Async `execute_write_command()`
- Direct BACnet write via BACpypes3 `WritePropertyRequest`
- Write result published to `bacnet/write/result`

**Database:**
- No schema changes (existing Point table supports write operations)
- SystemSettings.timezone controls worker timestamp generation

**Performance:**
- Write command latency: <500ms typical
- Monitoring page: 50+ points updating every 30-60s
- No memory leaks or connection issues after extended testing

### Known Issues
- Worker must be manually restarted after timezone changes (docker compose restart bacnet-worker)
- Write history not yet stored in database (Phase 7 feature)
- Batch MQTT publishing still optional (disabled by default)

### Migration Notes
- No database migrations required
- No breaking API changes
- Existing deployments: Pull latest code and restart services

---

## [0.5.0] - 2025-11-04

### Added

#### Phase 4: MQTT Publishing
- Python worker with BACpypes3 integration
- Per-point polling intervals (15s, 30s, 60s, etc.)
- Minute-aligned polling for synchronized timestamps
- MQTT connection management with auto-reconnect
- Batch publishing support (optional, disabled by default)
- Graceful shutdown handling (SIGTERM/SIGINT)
- Health checks for Docker containers

#### System Features
- Docker Compose orchestration (postgres, frontend, worker)
- Prisma ORM with type-safe database access
- Environment variable configuration
- Service health monitoring

### Changed
- Replaced CSV-based workflow with database-driven configuration
- Worker reads enabled points from PostgreSQL every 60 seconds
- MQTT topics auto-generated from Haystack tags

### Fixed
- Database connection pooling (Prisma singleton pattern)
- MQTT reconnection logic
- BACnet read error handling

---

## [0.4.0] - 2025-11-03

### Added

#### Phase 3: Point Configuration UI
- Haystack tagging form (8 fields: site, equipment type, equipment ID, point function, quantity, subject, location, qualifier)
- Meta-data point support (schedule, calendar, datetime, date)
- MQTT topic preview (auto-generates from tags)
- Bulk point enable/disable
- Point filtering by device, object type, MQTT status
- Common tagging patterns reference
- Validation for required fields

#### Database
- Point table with Haystack columns
- MQTT configuration storage
- System settings (timezone, polling intervals)

### Changed
- Improved UI/UX with better form validation
- Enhanced table with sorting and filtering

---

## [0.3.0] - 2025-11-02

### Added

#### Phase 2: BACnet Discovery
- Web-based discovery UI at `/discovery`
- BACnet network scanner using BAC0
- Device and point discovery with property reading
- Real-time discovery progress updates
- Auto-save to PostgreSQL database
- Discovered devices display with point counts

#### Database Schema
- Device table (id, deviceId, deviceName, ipAddress, vendorId, etc.)
- Point table (objectType, objectInstance, pointName, units, etc.)
- Prisma migrations

### Changed
- Replaced CSV workflow with database persistence
- Discovery runs in background worker

---

## [0.2.0] - 2025-11-01

### Added

#### Phase 1: Foundation
- Docker Compose setup (postgres, frontend services)
- Next.js 15 frontend with Turbopack
- PostgreSQL 15 database
- Prisma ORM integration
- Basic web UI with navigation
- Settings page
- Points page skeleton
- Dashboard page

#### Infrastructure
- Docker networking (bridge mode)
- Volume persistence for database
- Health checks
- Development hot-reload support

### Technical Debt
- Settled on BACpypes3 over BAC0 for better async support
- Chose PostgreSQL over TimescaleDB for initial simplicity
- Decided on separate MQTT broker (not in Docker Compose)

---

## [0.1.0] - 2025-10-30

### Added
- Initial project structure
- Legacy Python scripts (CSV-based workflow)
- Original 5-stage pipeline:
  - Stage 1: Discovery
  - Stage 2: Point analysis
  - Stage 3: Equipment mapping
  - Stage 4: JSON generation
  - Stage 5: MQTT publishing
- YAML configuration
- LXC container deployment documentation

### Context
- Project started as LXC-based Python scripts
- Manual CSV editing workflow
- 50+ points discovered from 2 production devices
- Proven MQTT publishing to InfluxDB

---

## Future Releases

### [0.7.0] - Planned
- TimescaleDB integration for time-series data
- Historical data visualization
- Grafana dashboard templates
- Data export/import tools
- Alert/notification system

### [0.8.0] - Planned
- Multi-site PostgreSQL replication
- Central data aggregation
- Cross-site analytics
- WAN deployment support
- Enhanced security (TLS, authentication)

### [0.9.0] - Planned
- ML model integration
- Edge inference
- Optimization recommendations
- Anomaly detection
- Predictive maintenance

### [1.0.0] - Planned
- Production-ready release
- Full documentation
- Performance benchmarks
- Security audit
- Multi-tenant support
- Role-based access control (RBAC)

---

## Version History

| Version | Release Date | Key Features |
|---------|-------------|--------------|
| 0.6.0   | 2025-11-07  | Monitoring Dashboard + BACnet Writes |
| 0.5.0   | 2025-11-04  | MQTT Publishing Worker |
| 0.4.0   | 2025-11-03  | Point Configuration UI |
| 0.3.0   | 2025-11-02  | BACnet Discovery |
| 0.2.0   | 2025-11-01  | Foundation (Docker + Web UI) |
| 0.1.0   | 2025-10-30  | Legacy Scripts |

---

**For detailed technical documentation, see:**
- [README.md](README.md) - User guide
- [CLAUDE.md](CLAUDE.md) - Developer documentation
- [STRATEGIC_PLAN.md](STRATEGIC_PLAN.md) - Architecture roadmap

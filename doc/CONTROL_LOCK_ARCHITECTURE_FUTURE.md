# Control Lock Architecture - Edge/Remote GUI Coordination

**Version**: 1.0  
**Date**: 2025-11-14  
**Status**: Approved for Implementation

---

## Executive Summary

BacPipes implements a **Control Lock Pattern** to enable safe, coordinated control between edge (local site) and remote (central) platforms. This architecture ensures:

- ✅ **Edge autonomy**: Edge platform always operational, even offline
- ✅ **No conflicts**: Only one controller active at any time
- ✅ **ML flexibility**: ML models can run on edge OR remote
- ✅ **Troubleshooting**: Configuration always done locally via edge GUI
- ✅ **Clean handoff**: Explicit request/grant/release flow

---

## Design Principles

### 1. Edge-First Architecture
```
Edge Platform = Source of Truth
  ↓
Remote Platform = Observer + Optional Controller
```

**Rationale:**
- BACnet devices physically connected to edge network
- Discovery/configuration requires local network access
- Troubleshooting without site visits is critical
- Network failures should not break local operations

### 2. Exclusive Control Authority

**States:**
- **EDGE_CONTROL** (default): Edge has write authority
- **REMOTE_CONTROL** (temporary): Remote has write authority
- **REQUEST_PENDING**: Remote waiting for edge approval

**Transitions:**
```
EDGE_CONTROL → [Remote requests] → REQUEST_PENDING → [Edge approves] → REMOTE_CONTROL
REMOTE_CONTROL → [Timeout OR Release OR Revoke] → EDGE_CONTROL
```

### 3. Explicit Handoff (No Implicit Takeover)

- Remote **cannot** seize control
- Edge **must** approve control transfer
- Timeout ensures auto-revert to edge
- Emergency revoke available to edge operators

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│           Edge Platform (192.168.1.35)          │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Edge GUI (Full Functionality)           │  │
│  │  - Discovery                             │  │
│  │  - Points Management                     │  │
│  │  - Monitoring + Control                  │  │
│  │  - Control Authority Panel               │  │
│  └──────────────────────────────────────────┘  │
│                    ↕                            │
│  ┌──────────────────────────────────────────┐  │
│  │  Control Authority Manager               │  │
│  │  - Grant/deny remote requests            │  │
│  │  - Track active controller               │  │
│  │  - Enforce timeouts                      │  │
│  │  - Emergency revoke                      │  │
│  └──────────────────────────────────────────┘  │
│                    ↕                            │
│  ┌──────────────────────────────────────────┐  │
│  │  BACnet Worker                           │  │
│  │  - Executes write commands               │  │
│  │  - Checks authority before writes        │  │
│  │  - Publishes command responses           │  │
│  └──────────────────────────────────────────┘  │
│                    ↕                            │
│           PostgreSQL (edge DB)                  │
└─────────────────────────────────────────────────┘
                     ↕ MQTT Bridge
┌─────────────────────────────────────────────────┐
│         Remote Platform (10.0.60.2)             │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Remote GUI (Monitoring + Control)       │  │
│  │  - Dashboard (multi-site)                │  │
│  │  - Monitoring                            │  │
│  │  - Control Request Panel                 │  │
│  │  - Settings                              │  │
│  └──────────────────────────────────────────┘  │
│                    ↕                            │
│  ┌──────────────────────────────────────────┐  │
│  │  Control Authority Client                │  │
│  │  - Request control                       │  │
│  │  - Send commands when authorized         │  │
│  │  - Monitor authority status              │  │
│  │  - Release control                       │  │
│  └──────────────────────────────────────────┘  │
│                    ↕                            │
│     PostgreSQL (bacnet_central DB)              │
└─────────────────────────────────────────────────┘
```

---

## MQTT Topics Specification

### Data Publishing (Existing)
```yaml
# Edge publishes sensor data
Topic: {site}/{equipment}/{object}/presentValue
Payload:
  {
    "value": 22.5,
    "timestamp": "2025-11-14T14:30:00+08:00",
    "units": "degreesCelsius",
    "quality": "good",
    "haystackName": "site.ahu.12.sensor.temp.air.supply",
    "dis": "Supply Air Temperature"
  }
QoS: 1
Retain: true
```

### Control Authority Channel (New)

#### 1. Authority Status
```yaml
Topic: control/{site}/authority/status
Payload:
  {
    "controller": "edge" | "remote",
    "granted_at": "2025-11-14T14:00:00Z",
    "expires_at": "2025-11-14T16:00:00Z" | null,
    "reason": "ML model training" | null
  }
QoS: 1
Retain: true  # Always show current state
Published by: Edge platform
Frequency: On change + every 60s heartbeat
```

#### 2. Control Request
```yaml
Topic: control/{site}/authority/request
Payload:
  {
    "request_id": "uuid",
    "requested_by": "remote",
    "requested_at": "2025-11-14T14:25:00Z",
    "reason": "ML model optimization",
    "duration": 7200  # seconds (2 hours)
  }
QoS: 2  # Exactly once
Retain: false
Published by: Remote platform
```

#### 3. Control Response
```yaml
Topic: control/{site}/authority/response
Payload:
  {
    "request_id": "uuid",
    "granted": true | false,
    "controller": "remote" | "edge",
    "expires_at": "2025-11-14T16:25:00Z",
    "message": "Approved for ML training" | "Denied: operators on site"
  }
QoS: 2
Retain: false
Published by: Edge platform
```

#### 4. Control Release
```yaml
Topic: control/{site}/authority/release
Payload:
  {
    "released_by": "remote" | "edge",
    "reason": "ML training complete" | "Emergency revoke"
  }
QoS: 2
Retain: false
Published by: Either platform
```

### Command Channel (New)

#### 5. Write Command
```yaml
Topic: control/{site}/commands/write
Payload:
  {
    "command_id": "uuid",
    "timestamp": "2025-11-14T14:30:00Z",
    "issued_by": "remote" | "edge",
    "point_id": 123,
    "device_id": 221,
    "object_type": "analog-output",
    "object_instance": 104,
    "value": 50.0,
    "priority": 8,
    "user": "operator_name",
    "reason": "Setpoint adjustment"
  }
QoS: 2  # Critical: Must be delivered exactly once
Retain: false
Published by: Current controller (edge or remote)
```

#### 6. Command Response
```yaml
Topic: control/{site}/commands/response
Payload:
  {
    "command_id": "uuid",
    "status": "success" | "failed" | "unauthorized",
    "timestamp": "2025-11-14T14:30:05Z",
    "error": null | "Device unreachable",
    "executed_value": 50.0,
    "bacnet_response": "OK"
  }
QoS: 2
Retain: false
Published by: Edge BACnet worker
```

---

## Database Schema

### New Tables

#### control_authority
```sql
CREATE TABLE control_authority (
  id SERIAL PRIMARY KEY,
  controller TEXT NOT NULL CHECK (controller IN ('edge', 'remote')),
  granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  granted_by TEXT NOT NULL,  -- user or system
  expires_at TIMESTAMPTZ,  -- NULL = indefinite (edge only)
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Only one active authority at a time
CREATE UNIQUE INDEX idx_active_authority 
  ON control_authority ((1)) 
  WHERE expires_at IS NULL OR expires_at > NOW();
```

#### control_requests
```sql
CREATE TABLE control_requests (
  id SERIAL PRIMARY KEY,
  request_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  requested_by TEXT NOT NULL,  -- 'remote' or specific user
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  reason TEXT NOT NULL,
  duration INTEGER NOT NULL,  -- seconds
  status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'denied', 'expired')),
  responded_at TIMESTAMPTZ,
  responded_by TEXT,
  response_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_control_requests_status ON control_requests(status);
CREATE INDEX idx_control_requests_time ON control_requests(requested_at DESC);
```

#### command_log
```sql
CREATE TABLE command_log (
  id SERIAL PRIMARY KEY,
  command_id UUID NOT NULL UNIQUE,
  issued_by TEXT NOT NULL,  -- 'edge' or 'remote'
  issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  point_id INTEGER REFERENCES "Point"(id),
  device_id INTEGER,
  object_type TEXT NOT NULL,
  object_instance INTEGER NOT NULL,
  value TEXT NOT NULL,  -- Store as text for flexibility
  priority INTEGER NOT NULL,
  user_name TEXT,
  reason TEXT,
  status TEXT NOT NULL CHECK (status IN ('pending', 'success', 'failed', 'unauthorized')),
  executed_at TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_command_log_status ON command_log(status);
CREATE INDEX idx_command_log_time ON command_log(issued_at DESC);
CREATE INDEX idx_command_log_point ON command_log(point_id);
```

---

## GUI Components

### Edge GUI Additions

#### 1. Control Authority Card (Dashboard)
```typescript
interface ControlAuthorityCardProps {
  authority: 'edge' | 'remote'
  expiresAt?: Date
  pendingRequest?: {
    id: string
    reason: string
    duration: number
    requestedAt: Date
  }
}

// Displays current controller
// Shows approve/deny buttons for pending requests
// Shows revoke button when remote has control
// Countdown timer for expiration
```

#### 2. Control History Panel (Settings)
```typescript
// Shows recent control transfers
// Displays command audit log
// Filterable by date, user, action
```

### Remote GUI Additions

#### 1. Control Request Panel (Monitoring)
```typescript
interface ControlRequestPanelProps {
  siteId: string
  authority: 'edge' | 'remote'
  expiresAt?: Date
}

// Request control button
// Reason input field
// Duration selector (30min, 1h, 2h, 4h)
// Release control button
// Authority status display
```

#### 2. Site Selector (Dashboard)
```typescript
// Multi-site support
// Dropdown to switch between sites
// Each site has independent authority
```

---

## Implementation Phases

### Phase 1: Edge Control Authority (Week 1)
**Goal**: Add control lock to edge platform

**Tasks:**
- [ ] Create database migration for control tables
- [ ] Implement `ControlAuthorityManager` class
- [ ] Add MQTT control topics
- [ ] Create `ControlAuthorityCard` component
- [ ] Add control status API endpoints
- [ ] Test local control lock toggle

**Deliverables:**
- Edge GUI shows control authority status
- Can manually toggle control lock
- Database tracks control history

### Phase 2: Remote GUI Foundation (Week 2)
**Goal**: Deploy monitoring-only remote GUI

**Tasks:**
- [ ] Create BacPipes-Remote repository
- [ ] Copy frontend with environment flags
- [ ] Configure for remote database
- [ ] Hide discovery/points pages
- [ ] Add site selector
- [ ] Test monitoring dashboard

**Deliverables:**
- Remote GUI displays data from bacnet_central
- Dashboard shows aggregated site stats
- Monitoring page shows real-time data

### Phase 3: Control Request Flow (Week 3)
**Goal**: Implement request/grant/release mechanism

**Tasks:**
- [ ] Add control request UI to remote GUI
- [ ] Implement MQTT request/response
- [ ] Add approve/deny flow to edge GUI
- [ ] Implement timeout auto-revert
- [ ] Add emergency revoke

**Deliverables:**
- Remote can request control
- Edge receives notification
- Edge can approve/deny
- Control auto-reverts after timeout

### Phase 4: Command Execution (Week 4)
**Goal**: Remote can send write commands when authorized

**Tasks:**
- [ ] Implement command channel
- [ ] Add authority checking to worker
- [ ] Create write command UI
- [ ] Add command acknowledgment
- [ ] Implement audit logging

**Deliverables:**
- Remote can write when authorized
- Commands execute on edge
- Full audit trail
- Authorization enforced

---

## Security Considerations

### Authentication (Future)
```yaml
Current:
  - No authentication (private network only)
  - Trust-based authorization

Production Requirements:
  - MQTT username/password authentication
  - TLS encryption for MQTT
  - User authentication in GUI
  - Role-based access control (RBAC)
```

### Authorization Levels (Future)
```yaml
Roles:
  - site_operator: Full control on edge
  - remote_operator: Can request control
  - viewer: Monitoring only
  - admin: Override all restrictions
```

### Audit Trail
```yaml
Logged Events:
  - Control requests (who, when, why)
  - Control grants/denials (approved by)
  - Control releases/revokes
  - All write commands (who, what, when, result)
  - Authority timeouts
  - Failed authorization attempts
```

---

## Testing Strategy

### Unit Tests
```yaml
ControlAuthorityManager:
  - Grant control to remote
  - Deny control request
  - Auto-revert on timeout
  - Emergency revoke
  - Reject commands from wrong controller

CommandHandler:
  - Check authority before write
  - Reject unauthorized writes
  - Log all commands
  - Handle BACnet errors
```

### Integration Tests
```yaml
Edge-Remote Flow:
  1. Remote requests control
  2. Edge receives notification
  3. Edge approves request
  4. Remote sends write command
  5. Edge executes command
  6. Edge sends response
  7. Remote receives confirmation
  8. Timeout expires
  9. Edge regains control
```

### Failure Scenarios
```yaml
Test Cases:
  - Network failure during control transfer
  - MQTT broker restart
  - Edge platform restart
  - Remote platform restart
  - Simultaneous requests from edge and remote
  - Control request timeout
  - Command timeout
```

---

## Monitoring & Observability

### Metrics
```yaml
Control Authority:
  - Current controller (gauge)
  - Control transfers per day (counter)
  - Average control duration (histogram)
  - Denied requests (counter)
  - Emergency revokes (counter)

Commands:
  - Commands per minute (counter)
  - Command success rate (gauge)
  - Command latency (histogram)
  - Failed commands (counter)
```

### Alerts
```yaml
Critical:
  - Control stuck in remote > 4 hours
  - Failed commands > 10/minute
  - Authorization errors

Warning:
  - Control requests denied > 5/day
  - Command latency > 5 seconds
```

---

## Frequently Asked Questions

### Q: What happens if network fails during remote control?
**A:** Edge platform continues operating autonomously. Control automatically reverts to edge after timeout.

### Q: Can remote force control takeover?
**A:** No. Edge must explicitly approve all control requests.

### Q: Can edge revoke control at any time?
**A:** Yes. Edge has emergency revoke capability.

### Q: What if both edge and remote try to write simultaneously?
**A:** Impossible. Only one controller is active at a time, enforced by database constraint.

### Q: How long can remote keep control?
**A:** Configurable timeout (default: 2 hours). Can be extended with new request.

### Q: Can multiple remote instances control different sites?
**A:** Yes. Each site has independent control authority.

### Q: What if ML model fails during remote control?
**A:** Timeout ensures control reverts to edge automatically. No manual intervention required.

### Q: Can we disable remote control entirely?
**A:** Yes. Edge can disable control requests in settings.

---

## References

- [BRIDGE_DEPLOYMENT_LESSONS.md](../BRIDGE_DEPLOYMENT_LESSONS.md) - MQTT bridge setup
- [MQTT Topics Specification](./MQTT_TOPICS.md) - Complete topic reference
- [Database Schema](./DATABASE_SCHEMA.md) - Full schema documentation
- [API Reference](./API_REFERENCE.md) - REST API endpoints

---

**Document Control:**
- Version: 1.0
- Author: System Architect
- Approved by: Project Lead
- Next Review: 2025-12-14

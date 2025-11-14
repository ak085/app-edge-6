# Implementation Roadmap - Control Lock Pattern

**Version**: 1.0
**Date**: 2025-11-14
**Target Completion**: 2025-12-05 (3 weeks)

---

## Overview

This document provides the detailed implementation plan for adding Control Lock functionality to BacPipes edge/remote platforms.

**Goal**: Enable safe, coordinated control between edge and remote platforms with exclusive control authority.

**Reference**: See [CONTROL_LOCK_ARCHITECTURE.md](./CONTROL_LOCK_ARCHITECTURE.md) for full design specification.

---

## Development Phases

### ✅ Phase 0: Documentation & Planning (Week 0)
**Status**: COMPLETE
**Duration**: 1 day

**Deliverables:**
- [x] Architecture documentation
- [x] Implementation roadmap
- [x] Database schema design
- [x] MQTT topics specification

---

### 🎯 Phase 1: Edge Control Authority (Week 1)
**Status**: READY TO START
**Duration**: 5-7 days
**Branch**: `feature/control-authority`

#### Day 1-2: Database & Backend
**Tasks:**
1. Create database migration for control tables
2. Implement `ControlAuthorityManager` class
3. Add authority checking to worker
4. Unit tests for authority manager

**Files to Create:**
```
frontend/prisma/migrations/004_control_authority.sql
worker/control_authority.py
worker/tests/test_control_authority.py
```

**Acceptance Criteria:**
- [ ] control_authority table created
- [ ] control_requests table created
- [ ] command_log table created
- [ ] ControlAuthorityManager can grant/deny/revoke control
- [ ] Unit tests passing

#### Day 3-4: MQTT Integration
**Tasks:**
1. Add MQTT control topics
2. Implement request/response handlers
3. Add timeout auto-revert mechanism
4. Integration tests

**Files to Modify/Create:**
```
worker/mqtt_publisher.py
worker/mqtt_control_handler.py  # NEW
worker/tests/test_mqtt_control.py
```

**Acceptance Criteria:**
- [ ] Worker subscribes to control/* topics
- [ ] Can publish authority status
- [ ] Can receive and process requests
- [ ] Timeout auto-revert works
- [ ] Integration tests passing

#### Day 5-7: Frontend Components
**Tasks:**
1. Create ControlAuthorityCard component
2. Add control status API endpoints
3. Add approve/deny UI
4. Add control history panel
5. E2E tests

**Files to Create:**
```
frontend/src/components/ControlAuthorityCard.tsx
frontend/src/app/api/control/status/route.ts
frontend/src/app/api/control/grant/route.ts
frontend/src/app/api/control/deny/route.ts
frontend/src/app/api/control/revoke/route.ts
frontend/src/app/api/control/history/route.ts
```

**Acceptance Criteria:**
- [ ] Dashboard shows control authority status
- [ ] Can approve/deny control requests via UI
- [ ] Can revoke control via UI
- [ ] Control history visible
- [ ] E2E tests passing

**Phase 1 Complete When:**
- All tests passing
- Edge GUI shows control status
- Can manually toggle control lock
- Ready to merge to development

---

### 🚀 Phase 2: Remote GUI Foundation (Week 2)
**Status**: PENDING Phase 1
**Duration**: 3-5 days
**Branch**: `feature/remote-gui`

#### Day 1-2: Remote Repository Setup
**Tasks:**
1. Create BacPipes-Remote repository on Gitea
2. Copy frontend with environment configurations
3. Configure remote database connection
4. Remove edge-specific features

**Repository Structure:**
```
BacPipes-Remote/
├── frontend/
│   ├── .env.remote          # DEPLOYMENT_MODE=remote
│   └── ... (copied from BacPipes)
├── docker-compose.yml       # Remote-specific
├── README.md               # Remote setup guide
└── doc/
    └── REMOTE_DEPLOYMENT.md
```

**Environment Configuration:**
```bash
# .env.remote
DEPLOYMENT_MODE=remote
DATABASE_URL=postgresql://anatoli@timescaledb:5432/bacnet_central
READONLY_MODE=false  # Has control capability
SHOW_DISCOVERY=false
SHOW_POINTS=false    # Points managed on edge
MQTT_BROKER=localhost:1884
SITE_ID=edge-site-1
```

**Acceptance Criteria:**
- [ ] BacPipes-Remote repository created
- [ ] Frontend builds successfully
- [ ] Connects to bacnet_central database
- [ ] Discovery/Points pages hidden
- [ ] No build errors

#### Day 3-4: Remote Dashboard
**Tasks:**
1. Add site selector component
2. Modify dashboard for multi-site view
3. Update API routes for site filtering
4. Test monitoring page with remote data

**Files to Create/Modify:**
```
frontend/src/components/SiteSelector.tsx  # NEW
frontend/src/app/page.tsx                # MODIFY: Multi-site dashboard
frontend/src/app/api/dashboard/route.ts  # MODIFY: Site filtering
```

**Acceptance Criteria:**
- [ ] Dashboard shows aggregated stats from bacnet_central
- [ ] Site selector works
- [ ] Monitoring page shows real-time data
- [ ] Data refreshes correctly

#### Day 5: Testing & Documentation
**Tasks:**
1. Test remote GUI with real data
2. Write remote deployment guide
3. Create troubleshooting doc
4. Verify monitoring accuracy

**Acceptance Criteria:**
- [ ] Remote GUI functional with test data
- [ ] Documentation complete
- [ ] Ready for Phase 3

**Phase 2 Complete When:**
- Remote GUI displays monitoring data correctly
- Multi-site support working
- Documentation complete
- Ready for control integration

---

### 🔐 Phase 3: Control Request Flow (Week 3)
**Status**: PENDING Phase 2
**Duration**: 5-7 days
**Branch**: `feature/control-request-flow`

#### Day 1-2: Remote Control Client
**Tasks:**
1. Create ControlAuthorityClient class
2. Add MQTT connection management
3. Implement request/release logic
4. Add real-time status updates

**Files to Create:**
```
frontend/src/lib/control-authority-client.ts
frontend/src/hooks/useControlAuthority.ts
```

**Acceptance Criteria:**
- [ ] Can connect to MQTT from browser
- [ ] Can request control
- [ ] Can release control
- [ ] Real-time authority updates

#### Day 3-4: Control Request UI
**Tasks:**
1. Create ControlRequestPanel component
2. Add request form (reason, duration)
3. Add release button
4. Add status notifications
5. Disable write when unauthorized

**Files to Create:**
```
frontend/src/components/ControlRequestPanel.tsx
frontend/src/app/monitoring/components/WriteControls.tsx  # MODIFY
```

**Acceptance Criteria:**
- [ ] Request control form works
- [ ] Shows pending/approved/denied states
- [ ] Release button works
- [ ] Write commands disabled when edge has control

#### Day 5-6: Edge Approval Flow
**Tasks:**
1. Add request notifications to edge GUI
2. Create approve/deny modal
3. Add timer display for remote control
4. Test full request/approve cycle

**Files to Modify:**
```
frontend/src/components/ControlAuthorityCard.tsx  # Add notifications
frontend/src/components/ControlRequestModal.tsx  # NEW
```

**Acceptance Criteria:**
- [ ] Edge receives request notifications
- [ ] Can approve/deny via modal
- [ ] Timer shows when remote has control
- [ ] Full cycle works end-to-end

#### Day 7: Emergency Revoke & Timeout
**Tasks:**
1. Implement emergency revoke on edge
2. Test timeout auto-revert
3. Handle network failures
4. Edge-to-edge handoff testing

**Acceptance Criteria:**
- [ ] Emergency revoke works
- [ ] Timeout auto-reverts to edge
- [ ] Network failures handled gracefully
- [ ] Full test suite passing

**Phase 3 Complete When:**
- Remote can request control
- Edge can approve/deny
- Control reverts on timeout
- Emergency revoke works
- All tests passing

---

### 🎮 Phase 4: Command Execution (Week 4)
**Status**: PENDING Phase 3
**Duration**: 3-4 days
**Branch**: `feature/command-execution`

#### Day 1-2: Command Channel
**Tasks:**
1. Implement write command MQTT handler
2. Add authority validation
3. Add command acknowledgment
4. Add command queueing

**Files to Modify:**
```
worker/bacnet_command_handler.py  # MODIFY
worker/mqtt_command_subscriber.py  # NEW
```

**Acceptance Criteria:**
- [ ] Worker receives write commands
- [ ] Checks authority before execution
- [ ] Sends acknowledgment
- [ ] Queues commands correctly

#### Day 3-4: Remote Write UI
**Tasks:**
1. Enable write controls when authorized
2. Add command confirmation dialog
3. Show command status/result
4. Add command history

**Files to Modify:**
```
frontend/src/app/monitoring/components/WriteControls.tsx
frontend/src/components/CommandConfirmDialog.tsx  # NEW
frontend/src/app/api/commands/route.ts  # NEW
```

**Acceptance Criteria:**
- [ ] Write button enabled when remote has control
- [ ] Confirmation dialog works
- [ ] Command executes on edge
- [ ] Result displayed to user
- [ ] Command logged in database

#### Day 5: Audit & Testing
**Tasks:**
1. Verify audit logging
2. Test command failures
3. Test concurrent commands
4. Performance testing

**Acceptance Criteria:**
- [ ] All commands logged with user/reason
- [ ] Failed commands handled correctly
- [ ] Concurrent commands work
- [ ] Performance acceptable (< 2s latency)

**Phase 4 Complete When:**
- Remote can write when authorized
- Commands execute reliably
- Full audit trail
- Production ready

---

## Testing Strategy

### Unit Tests
```bash
# Backend tests
cd worker
pytest tests/test_control_authority.py
pytest tests/test_mqtt_control.py
pytest tests/test_command_handler.py

# Frontend tests
cd frontend
npm run test
```

### Integration Tests
```bash
# Full flow test
./tests/integration/test_control_flow.sh

Test Scenarios:
1. Remote requests control
2. Edge approves
3. Remote sends write command
4. Edge executes and responds
5. Control times out
6. Edge regains control
```

### E2E Tests
```bash
# Playwright/Cypress tests
npm run test:e2e

Scenarios:
- Control request/approve flow
- Write command execution
- Emergency revoke
- Timeout auto-revert
- Network failure recovery
```

---

## Risk Management

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MQTT message loss | Medium | High | Use QoS 2, add retry logic |
| Clock skew (edge/remote) | Low | Medium | Use NTP sync, relative timestamps |
| State desync | Medium | High | Heartbeat + reconciliation |
| Database migration fails | Low | High | Test migrations, add rollback |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Network partition | High | Medium | Auto-revert to edge |
| Operator confusion | Medium | Medium | Clear UI, good documentation |
| Control lock stuck | Low | High | Timeout + emergency revoke |
| Audit log too large | Low | Low | Implement log rotation |

---

## Success Criteria

### Phase 1 Success:
- [x] Documentation complete
- [ ] Edge GUI shows control authority
- [ ] Control can be granted/revoked locally
- [ ] Database tracks control history
- [ ] All unit tests passing

### Phase 2 Success:
- [ ] Remote GUI displays monitoring data
- [ ] Multi-site support working
- [ ] Connects to bacnet_central database
- [ ] No edge-specific features visible

### Phase 3 Success:
- [ ] Remote can request control
- [ ] Edge approves/denies requests
- [ ] Control times out correctly
- [ ] Emergency revoke works
- [ ] Full integration tests passing

### Phase 4 Success:
- [ ] Remote can write when authorized
- [ ] Commands execute reliably
- [ ] Audit trail complete
- [ ] Performance acceptable
- [ ] Production ready

### Project Complete When:
- [ ] All phases complete
- [ ] All tests passing (unit + integration + E2E)
- [ ] Documentation updated
- [ ] Deployed to development branch
- [ ] User acceptance testing passed
- [ ] Ready for production deployment

---

## Deployment Plan

### Development Branch Merges:
```bash
Week 1: feature/control-authority → development
Week 2: feature/remote-gui → development
Week 3: feature/control-request-flow → development
Week 4: feature/command-execution → development
```

### Release Strategy:
```yaml
v0.7.0: Phase 1 (Edge control authority)
v0.8.0: Phase 2 (Remote monitoring GUI)
v0.9.0: Phase 3 (Control request flow)
v1.0.0: Phase 4 (Full command execution) - PRODUCTION READY
```

---

## Next Steps

**Immediate Actions (Today):**
1. ✅ Review and approve architecture
2. ✅ Create documentation
3. [ ] Push documentation to development branch
4. [ ] Create Phase 1 branch: `feature/control-authority`
5. [ ] Begin Phase 1, Day 1 implementation

**Tomorrow:**
1. Create database migration
2. Implement ControlAuthorityManager
3. Write unit tests

---

## References

- [CONTROL_LOCK_ARCHITECTURE.md](./CONTROL_LOCK_ARCHITECTURE.md) - Full architecture spec
- [BRIDGE_DEPLOYMENT_LESSONS.md](../BRIDGE_DEPLOYMENT_LESSONS.md) - MQTT lessons learned
- [Database Schema](./DATABASE_SCHEMA.md) - Complete schema
- [API Reference](./API_REFERENCE.md) - REST API docs

---

**Document Control:**
- Version: 1.0
- Status: Approved
- Next Review: Weekly during implementation

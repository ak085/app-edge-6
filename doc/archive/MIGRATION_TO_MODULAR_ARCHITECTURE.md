# Migration to Modular LXC Architecture

**Date Started**: 2025-11-21
**Objective**: Migrate from all-in-one Docker Compose to modular 3-container architecture

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────┐
│ LXC Container 1: bacpipes-discovery (10.0.60.30)       │
│ Current Location: /home/ak101/BacPipes                 │
│ ─────────────────────────────────────────────────────── │
│ Docker Compose Services:                               │
│   - frontend (port 3001)     ← BACnet discovery UI     │
│   - postgres (port 5434)     ← Configuration DB        │
│   - bacnet-worker            ← Polls BACnet devices    │
│                                                         │
│ Publishes to: 10.0.60.3:1883 (external MQTT)           │
│ Status: PRIMARY - Must remain stable                   │
└─────────────────────────────────────────────────────────┘
                            ↓ MQTT publish
┌─────────────────────────────────────────────────────────┐
│ LXC Container 2: mqtt-broker (10.0.60.3)               │
│ ─────────────────────────────────────────────────────── │
│ Standalone Mosquitto (no Docker Compose)               │
│   - Port 1883 (local network)                          │
│   - Port 8883 (TLS for WAN - future)                   │
│                                                         │
│ Bridge to: Remote MQTT broker (future WAN encrypted)   │
│ Status: Infrastructure - already created by user       │
└─────────────────────────────────────────────────────────┘
                            ↓ MQTT subscribe
┌─────────────────────────────────────────────────────────┐
│ LXC Container 3: bacpipes-monitoring (10.0.60.31)      │
│ Future Location: TBD                                    │
│ ─────────────────────────────────────────────────────── │
│ Docker Compose Services:                               │
│   - timescaledb (port 5435)  ← Time-series storage     │
│   - telegraf                 ← MQTT → TimescaleDB      │
│   - monitoring-dashboard (port 3003) ← View/export CSV │
│                                                         │
│ Subscribes from: 10.0.60.3:1883                        │
│ Status: Future - not yet migrated                      │
└─────────────────────────────────────────────────────────┘
```

---

## Migration Phases

### **PHASE 1: Cleanup Local App** ✅ CURRENT
**Goal**: Remove accidentally added pages from port 3001

**Files to Delete** (created in wrong location):
- `/home/ak101/BacPipes/frontend/src/app/timescale-viewer/page.tsx`
- `/home/ak101/BacPipes/frontend/src/app/api/timescale/test/route.ts`
- `/home/ak101/BacPipes/frontend/src/app/api/timescale/health/route.ts`
- `/home/ak101/BacPipes/frontend/src/app/api/timescale/data/route.ts`

**Environment Variable to Remove**:
- Remove `TIMESCALE_URL` from `/home/ak101/BacPipes/frontend/.env`

**Verification**:
1. Access http://192.168.1.35:3001 - main dashboard should work
2. Check navigation menu - no TimescaleDB viewer link
3. Test BACnet discovery features still work
4. **USER TESTS AND CONFIRMS** before proceeding

---

### **PHASE 2: Switch to External MQTT Broker** 🎯 NEXT
**Goal**: Point bacnet-worker to 10.0.60.3:1883 instead of internal broker

**Changes Required**:

**File 1: `/home/ak101/BacPipes/.env`**
```bash
# Change from:
MQTT_BROKER=mqtt-broker  # Internal Docker service

# Change to:
MQTT_BROKER=10.0.60.3    # External LXC container
```

**File 2: `/home/ak101/BacPipes/worker/main.py`** (verify connection logic)
- Ensure it reads `MQTT_BROKER` from environment
- No hardcoded localhost/internal references

**Verification Steps**:
1. Restart bacnet-worker: `docker compose restart bacnet-worker`
2. Check logs: `docker compose logs -f bacnet-worker`
3. Verify connection to 10.0.60.3:1883 successful
4. Test MQTT publishing still works (check with `mosquitto_sub`)
5. Verify frontend still receives data
6. **USER TESTS AND CONFIRMS** before proceeding

---

### **PHASE 3: Remove Internal MQTT Broker** 🔜
**Goal**: Clean up docker-compose.yml after successful external connection

**Changes Required**:

**File: `/home/ak101/BacPipes/docker-compose.yml`**
- Remove `mqtt-broker` service definition
- Remove `mqtt-broker` from `depends_on` in other services
- Remove MQTT broker volume mounts

**Verification Steps**:
1. `docker compose down`
2. `docker compose up -d`
3. Verify no MQTT broker container running locally
4. Verify bacnet-worker still connects to 10.0.60.3:1883
5. Verify publishing still works
6. **USER TESTS AND CONFIRMS**

---

### **PHASE 4: Update Documentation** 📝
**Goal**: Reflect new architecture in CLAUDE.md

**Updates Required**:
- Update "Current Architecture" section
- Document MQTT broker as external infrastructure
- Update port allocation table
- Add reference to this migration document

---

### **PHASE 5: Prepare Monitoring Container** (Future)
**Goal**: Move TimescaleDB + Telegraf + monitoring-dashboard to new LXC

**Not started yet - waiting for Phase 1-4 completion**

---

## Current Status

**Last Updated**: 2025-11-21 23:45 MYT

- ✅ **Phase 1**: **COMPLETE** (user validated, tested)
- ✅ **Phase 2**: **COMPLETE** (external MQTT broker connected successfully)
- ✅ **Phase 3**: **COMPLETE** (internal MQTT broker removed from docker-compose)
- ⏳ **Phase 4**: Ready to execute (update documentation)
- 🔜 **Phase 5**: Future work

**Phase 1 Completion Summary**:
- Deleted: `/frontend/src/app/timescale-viewer/` directory
- Deleted: `/frontend/src/app/api/timescale/` directory
- Removed: `TIMESCALE_URL` from `/frontend/.env`
- Verified: Frontend accessible at http://192.168.1.35:3001 (HTTP 200)
- Status: Main application (port 3001) clean and stable

**Phase 2 Completion Summary**:
- Updated: `MQTT_BROKER=10.0.60.3` in `.env` file
- Updated: Database `MqttConfig` table: broker=10.0.60.3
- Restarted: bacnet-worker (connects to external broker)
- Restarted: Telegraf (subscribes from external broker)
- Verified: bacnet-worker log shows "✅ Connected to MQTT broker 10.0.60.3:1883"
- Status: Publishing to external LXC MQTT broker successful

**Phase 3 Completion Summary**:
- Removed: `mqtt-broker` service from docker-compose.yml (lines 27-47)
- Removed: `mqtt-remote` service from docker-compose.yml (lines 49-67)
- Removed: `mqtt-broker` dependency from bacnet-worker service
- Removed: MQTT broker volumes (mqtt_data, mqtt_log, mqtt_remote_data, mqtt_remote_log)
- Updated: Comments to reflect external MQTT architecture
- Updated: Default MQTT_BROKER in env to 10.0.60.3
- Verified: Services restart successfully without internal broker
- Verified: bacnet-worker connects to external broker at 10.0.60.3:1883
- Verified: Frontend still accessible at http://192.168.1.35:3001 (HTTP 200)
- Status: Internal MQTT broker successfully removed, system stable

---

## Rollback Plan (If Things Break)

### **Phase 1 Rollback** (Delete Pages)
- Pages are unused, no rollback needed
- If frontend breaks: `git restore frontend/src/app/`

### **Phase 2 Rollback** (External MQTT)
```bash
# Revert .env change
MQTT_BROKER=mqtt-broker

# Restart services
docker compose restart bacnet-worker
```

### **Phase 3 Rollback** (Remove Internal Broker)
```bash
# Restore docker-compose.yml from git
git restore docker-compose.yml

# Recreate internal broker
docker compose up -d mqtt-broker
```

---

## Notes

- **LXC Container 10.0.60.3** already created by user with Mosquitto installed
- Main application (port 3001) is **production-critical** - must remain stable
- Testing after each phase is mandatory
- User confirmation required before proceeding to next phase

---

## Questions Answered

**Q: Why separate migration document instead of CLAUDE.md?**
A: CLAUDE.md describes current state. This document tracks historical migration process. Keeps context clean.

**Q: Why not migrate everything at once?**
A: High risk of breaking working system. Incremental migration allows rollback at each step.

**Q: What if external MQTT broker fails?**
A: Can quickly revert to internal broker by changing .env and restarting worker.

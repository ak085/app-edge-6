# MVP Implementation - Remote Control

**Start Date**: 2025-11-14
**Target**: 2-3 days
**Approach**: Simplest thing that works

---

## Day 1: Edge Control Switch

### Morning (2 hours)

**Task 1: Database Migration**
```bash
cd frontend
npx prisma migrate dev --name add_remote_control_flag
```

**Task 2: Update Prisma Schema**
```prisma
// prisma/schema.prisma
model MqttConfig {
  // ... existing fields
  allowRemoteControl Boolean @default(false) @map("allow_remote_control")
}
```

**Task 3: Settings UI**
- Add toggle switch to settings page
- Connect to database
- Test: Toggle on/off, verify in database

**Acceptance:** Can toggle remote control in edge GUI

---

### Afternoon (2 hours)

**Task 4: Worker Flag Check**
- Modify `worker/mqtt_write_handler.py`
- Add database check before writes
- Add logging

**Task 5: Test Locally**
- Publish test MQTT message with `source: 'remote'`
- Verify rejected when flag OFF
- Verify accepted when flag ON

**Acceptance:** Worker respects remote control flag

---

## Day 2: Remote GUI Setup

### Morning (3 hours)

**Task 1: Create BacPipes-Remote Repo**
```bash
cd /home/ak101
mkdir BacPipes-Remote
cd BacPipes-Remote

# Copy frontend
cp -r ../BacPipes/frontend ./
cp ../BacPipes/docker-compose.yml ./docker-compose.remote.yml
```

**Task 2: Configure for Remote**
```bash
# Create .env
cat > frontend/.env << EOF
DATABASE_URL=postgresql://anatoli@timescaledb:5432/bacnet_central
MQTT_BROKER=localhost
MQTT_PORT=1884
NEXT_PUBLIC_DEPLOYMENT=remote
NEXT_PUBLIC_HIDE_DISCOVERY=true
NEXT_PUBLIC_HIDE_POINTS=true
EOF
```

**Task 3: Modify Navigation**
- Hide discovery/points pages when DEPLOYMENT=remote

**Acceptance:** Remote GUI builds and runs

---

### Afternoon (2 hours)

**Task 4: Test Remote Monitoring**
- Connect to bacnet_central database
- Verify dashboard shows data
- Verify monitoring page shows real-time data

**Task 5: Test Remote Writes**
- Enable remote control on edge
- Write value from remote GUI
- Verify BACnet device updates

**Acceptance:** Remote can monitor and control

---

## Day 3: Testing & Polish

### Morning (2 hours)

**Test Scenarios:**
1. ✅ Remote control OFF → writes rejected
2. ✅ Remote control ON → writes work
3. ✅ Toggle during operation → immediate effect
4. ✅ Simultaneous writes → observe behavior
5. ✅ Network failure → graceful handling

**Acceptance:** All tests pass

---

### Afternoon (2 hours)

**Polish:**
- Add better UI feedback
- Improve logging
- Update documentation
- Push to gitea

**Acceptance:** Production ready

---

## Minimal File Changes

```
Edge Platform (BacPipes):
  frontend/prisma/schema.prisma               (1 line)
  frontend/src/app/settings/page.tsx          (20 lines)
  worker/mqtt_write_handler.py                (10 lines)

Remote Platform (BacPipes-Remote):
  frontend/.env                               (new file)
  frontend/src/components/Navigation.tsx      (5 lines)
  docker-compose.remote.yml                   (new file)
```

**Total code changes: < 50 lines**

---

## What Happens After

### If It Works Well:
- Ship it
- Use in production
- Add features as needed

### If We Find Issues:
- Document them
- Decide if we need more complexity
- Iterate

**Don't solve problems we don't have.**

---

## Decision Points

After testing, decide:

**Need conflict detection?**
- YES → Add simple last-write-wins indicator
- NO → Ship as-is

**Need audit logging?**
- YES → Add write_history table
- NO → Use existing logs

**Need timeout?**
- YES → Add auto-disable after N hours
- NO → Manual toggle is fine

**Need request/approve?**
- YES → See CONTROL_LOCK_ARCHITECTURE_FUTURE.md
- NO → Toggle switch is sufficient

---

## Success Metrics

- ⏱️ **Time**: 2-3 days (not 3 weeks)
- 🐛 **Bugs**: Fix as found
- 📝 **Code**: < 100 lines changed
- ✅ **Works**: Remote can control when permitted
- 🚀 **Ship**: Push to production quickly

---

**Let's build it!**

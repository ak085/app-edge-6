# Remote Control - MVP Implementation

**Version**: 1.0 MVP
**Date**: 2025-11-14
**Approach**: Start simple, iterate based on learnings

---

## Goal

Enable remote GUI to control BACnet points when edge platform permits it.

**Start with the simplest thing that could possibly work.**

---

## MVP Architecture (This Week)

### Simple On/Off Switch

```
Edge Platform:
  - Settings page: Toggle "Allow Remote Control" (boolean)
  - Worker: Check flag before executing MQTT write commands
  - That's it.

Remote Platform:
  - Same frontend code, different environment config
  - Hide Discovery & Points pages
  - Connect to bacnet_central database
  - Use existing MQTT write functionality

No complex state machine. No request/approve flow. Just a switch.
```

---

## Implementation

### 1. Database Change (1 minute)

```sql
-- Add to existing MqttConfig table
ALTER TABLE "MqttConfig"
  ADD COLUMN IF NOT EXISTS allow_remote_control BOOLEAN DEFAULT false;
```

### 2. Edge GUI - Settings Page (30 minutes)

```typescript
// frontend/src/app/settings/page.tsx
// Add to MQTT configuration section

<div className="space-y-4">
  <h3>Remote Control</h3>
  <div className="flex items-center space-x-2">
    <Switch
      id="allow-remote"
      checked={mqttConfig.allow_remote_control}
      onCheckedChange={async (checked) => {
        await updateMqttConfig({ allow_remote_control: checked })
      }}
    />
    <label htmlFor="allow-remote">
      Allow remote platform to control this site
    </label>
  </div>

  {mqttConfig.allow_remote_control && (
    <Alert>
      ⚠️ Remote control enabled. Remote platform can write to BACnet points.
    </Alert>
  )}
</div>
```

### 3. Worker - Check Flag (15 minutes)

```python
# worker/mqtt_write_handler.py

def on_write_command(client, userdata, msg):
    """Handle write command from MQTT"""
    payload = json.loads(msg.payload)

    # Check if command is from remote
    is_remote = payload.get('source') == 'remote'

    if is_remote:
        # Check if remote control allowed
        config = db.query_one("SELECT allow_remote_control FROM MqttConfig WHERE id = 1")
        if not config or not config['allow_remote_control']:
            logger.warning(f"Rejected remote write command - remote control disabled")
            return

    # Execute write
    execute_bacnet_write(payload)
```

### 4. Remote GUI Setup (1 hour)

```bash
# In BacPipes-Remote directory
# Copy entire frontend
cp -r ../BacPipes/frontend ./

# Create .env.remote
cat > frontend/.env << EOF
# Remote Platform Configuration
DATABASE_URL=postgresql://anatoli@timescaledb:5432/bacnet_central
MQTT_BROKER=localhost
MQTT_PORT=1884

# Hide edge-specific features
NEXT_PUBLIC_HIDE_DISCOVERY=true
NEXT_PUBLIC_HIDE_POINTS=true
NEXT_PUBLIC_DEPLOYMENT=remote
EOF

# Modify write commands to include source
# frontend/src/lib/mqtt-client.ts
const writePayload = {
  ...payload,
  source: 'remote'  // Mark as remote
}
```

### 5. Hide Pages in Remote GUI (15 minutes)

```typescript
// frontend/src/components/Navigation.tsx
const isRemote = process.env.NEXT_PUBLIC_DEPLOYMENT === 'remote'

// Conditionally render nav items
{!isRemote && <Link href="/discovery">Discovery</Link>}
{!isRemote && <Link href="/points">Points</Link>}
```

---

## Testing Plan (1 day)

### Test 1: Remote Control Disabled (Default)
```
1. Edge: Switch is OFF
2. Remote: Try to write a value
3. Expected: Write rejected, edge logs warning
```

### Test 2: Remote Control Enabled
```
1. Edge: Turn switch ON
2. Remote: Write a value
3. Expected: Write succeeds, BACnet device updates
```

### Test 3: Simultaneous Writes
```
1. Edge: Switch ON
2. Edge: Write value A
3. Remote: Write value B (at same time)
4. Expected: See what happens (probably last write wins)
```

### Test 4: Toggle During Operation
```
1. Edge: Switch ON
2. Remote: Writing values successfully
3. Edge: Turn switch OFF
4. Remote: Try to write
5. Expected: Writes rejected immediately
```

---

## What We'll Learn

After testing, we'll know:
- ✅ Does simultaneous control cause problems?
- ✅ Is last-write-wins acceptable?
- ✅ Do we need conflict detection?
- ✅ Do we need audit logging?
- ✅ Do we need request/approve flow?

**Then we can decide what to build next.**

---

## Future Enhancements (Only If Needed)

Based on testing, we might add:

### If simultaneous writes are a problem:
- Add simple mutex lock
- Last write shows who's controlling

### If we need history:
- Log write commands to database
- Show recent control actions

### If we need finer control:
- Timeout (auto-disable after X hours)
- Request/approve flow
- Per-point permissions

### If we need security:
- MQTT username/password
- TLS encryption
- User authentication

**Build only what we actually need.**

---

## File Changes Summary

```
Modified:
  frontend/prisma/schema.prisma         (add column)
  frontend/src/app/settings/page.tsx    (add switch)
  worker/mqtt_write_handler.py          (add check)

New (Remote):
  BacPipes-Remote/frontend/.env         (config)
  BacPipes-Remote/docker-compose.yml    (deployment)
```

---

## Deployment

### Edge Platform
```bash
cd BacPipes
docker compose down
npx prisma migrate dev  # Apply schema change
docker compose up -d
# Toggle switch in settings page
```

### Remote Platform
```bash
cd BacPipes-Remote
docker compose up -d
# Start using monitoring page
```

---

## Success Criteria

- [x] Documentation simplified
- [ ] Switch visible in edge settings
- [ ] Remote writes fail when switch OFF
- [ ] Remote writes succeed when switch ON
- [ ] No crashes or errors
- [ ] Works reliably for 24 hours

**Total time: 2-3 days**

---

## Next Session

Based on what we learn, we can:
- Add more features if needed
- Or declare it done if it works well enough

**Ship it, test it, learn from it.**

---

**References:**
- [Full architecture doc](./CONTROL_LOCK_ARCHITECTURE.md) - For future if needed
- [MQTT bridge lessons](../BRIDGE_DEPLOYMENT_LESSONS.md) - MQTT best practices

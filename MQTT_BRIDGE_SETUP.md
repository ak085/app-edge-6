# MQTT Bridge Configuration Guide

**Purpose**: Configure Mosquitto MQTT bridge to forward BACnet data from local site to remote headquarters

**Last Updated**: 2025-11-22

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│ Local Site: BacPipes Discovery              │
│ IP: 192.168.1.35                            │
│ Publishes BACnet data to local MQTT         │
└─────────────────┬───────────────────────────┘
                  │ MQTT publish
                  ↓
┌─────────────────────────────────────────────┐
│ Mosquitto-Local (Bridge Source)             │
│ LXC: mqtt-broker                            │
│ IP: 10.0.60.3                               │
│ Port: 1883                                  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ ⚙️  MQTT BRIDGE CONFIGURED HERE              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
└─────────────────┬───────────────────────────┘
                  │ Bridge forwards
                  ↓
┌─────────────────────────────────────────────┐
│ Mosquitto-Remote (Bridge Destination)       │
│ LXC: remote-mqtt-broker                     │
│ IP: 10.0.80.3                               │
│ Port: 1883                                  │
│ Aggregates data from all sites              │
└─────────────────┬───────────────────────────┘
                  │ MQTT subscribe
                  ↓
┌─────────────────────────────────────────────┐
│ Remote Monitoring Dashboard                 │
│ IP: 10.0.80.2                               │
│ Consumes aggregated data                    │
└─────────────────────────────────────────────┘
```

---

## Prerequisites

Before starting, verify:

1. **Network Connectivity**:
   ```bash
   # From Mosquitto-Local (10.0.60.3), test remote broker connectivity
   ping -c 3 10.0.80.3
   nc -zv 10.0.80.3 1883
   ```

2. **SSH Access**:
   - User: `ak101`
   - Password: `ubnt.101`
   - Access to both:
     - Mosquitto-Local: `ssh ak101@10.0.60.3`
     - Mosquitto-Remote: `ssh ak101@10.0.80.3`

3. **Mosquitto Installed**:
   ```bash
   # Check Mosquitto version
   mosquitto -h | head -n 1

   # Verify Mosquitto is running
   systemctl status mosquitto
   ```

4. **File Permissions**:
   - User `ak101` can run `sudo` commands without password

---

## Part 1: Configure Mosquitto-Local (Bridge Source)

**Server**: 10.0.60.3 (LXC: mqtt-broker)

This broker will bridge topics to the remote broker.

### Step 1: SSH to Mosquitto-Local

```bash
ssh ak101@10.0.60.3
```

### Step 2: Create Bridge Configuration File

**CRITICAL**: Do NOT add leading spaces or tabs. Configuration must start at column 0.

```bash
sudo tee /etc/mosquitto/conf.d/bridge.conf > /dev/null << 'EOF'
# MQTT Bridge Configuration
# Local Broker (10.0.60.3) → Remote Broker (10.0.80.3)
#
# This configuration forwards BACnet topics from local site to remote HQ

# Bridge connection name
connection remote-bridge

# Remote broker address
address 10.0.80.3:1883

# Topics to bridge
# Format: topic <pattern> <direction> <qos> <local prefix> <remote prefix>
# Direction: out = local → remote, in = remote → local, both = bidirectional

# Forward all BACnet sensor data to remote (outbound only)
topic bacnet/# out 1 "" ""

# Allow write commands from remote to local (inbound only)
topic bacnet/write/# in 1 "" ""

# Bridge settings
cleansession false         # Maintain session across restarts
try_private true          # Use private bridge implementation
notifications false        # Don't send notifications
bridge_attempt_unsubscribe true  # Clean unsubscribe on shutdown

# Optional: Authentication (uncomment if remote broker requires it)
# remote_username mqtt_bridge
# remote_password your_password_here

# Optional: Keep-alive settings
# keepalive_interval 60
# bridge_max_packet_size 0  # 0 = no limit

EOF
```

### Step 3: Set Correct File Permissions

```bash
sudo chown mosquitto:mosquitto /etc/mosquitto/conf.d/bridge.conf
sudo chmod 644 /etc/mosquitto/conf.d/bridge.conf
```

### Step 4: Verify Configuration Syntax

```bash
# Test Mosquitto configuration without starting
sudo mosquitto -c /etc/mosquitto/mosquitto.conf -t

# Expected output:
# (nothing) = configuration is valid
# Any error messages indicate syntax problems
```

**Common Errors**:
- `Error: Unknown configuration variable "#"` → Leading spaces in bridge.conf (see Step 2)
- `Error: Bridge connection name already in use` → Duplicate connection name in config files

### Step 5: Restart Mosquitto

```bash
sudo systemctl restart mosquitto
```

### Step 6: Verify Mosquitto Started Successfully

```bash
# Check service status
sudo systemctl status mosquitto

# Expected output:
# ● mosquitto.service - Mosquitto MQTT Broker
#    Loaded: loaded
#    Active: active (running)

# Check logs for bridge connection
sudo journalctl -u mosquitto -n 50 --no-pager | grep -i bridge

# Expected log entries:
# "Connecting bridge remote-bridge (10.0.80.3:1883)"
# "Bridge remote-bridge sending CONNECT"
# "Received CONNACK on connection remote-bridge"
```

### Step 7: Check Bridge Connection Status

```bash
# View last 30 Mosquitto log entries
sudo journalctl -u mosquitto -n 30 --no-pager

# Look for these positive indicators:
# ✅ "Connecting bridge remote-bridge"
# ✅ "Received CONNACK on connection remote-bridge"

# Look for these error indicators:
# ❌ "Connection Refused"
# ❌ "Network unreachable"
# ❌ "Unknown configuration variable"
```

---

## Part 2: Configure Mosquitto-Remote (Bridge Destination)

**Server**: 10.0.80.3 (LXC: remote-mqtt-broker)

The remote broker typically requires **no special configuration** to accept bridged connections. It acts as a standard MQTT broker receiving messages from the local bridge.

### Verification Only (No Configuration Changes Needed)

```bash
# SSH to remote broker
ssh ak101@10.0.80.3

# Verify Mosquitto is running
sudo systemctl status mosquitto

# Check if broker is listening on port 1883
sudo netstat -tlnp | grep 1883

# Expected output:
# tcp  0  0 0.0.0.0:1883  0.0.0.0:*  LISTEN  <PID>/mosquitto
```

### Optional: Enable Anonymous Connections (If Bridge Fails)

If bridge cannot connect due to authentication errors, you may need to allow anonymous connections:

```bash
# SSH to Mosquitto-Remote (10.0.80.3)
ssh ak101@10.0.80.3

# Edit main Mosquitto config
sudo nano /etc/mosquitto/mosquitto.conf

# Add this line if not present:
allow_anonymous true

# Save and exit (Ctrl+X, Y, Enter)

# Restart Mosquitto
sudo systemctl restart mosquitto
```

**Security Note**: `allow_anonymous true` is acceptable for internal networks. For production, configure proper authentication using username/password or certificates.

---

## Part 3: Testing the Bridge

### Test 1: Subscribe on Remote Broker

On **Mosquitto-Remote** (10.0.80.3):

```bash
# Subscribe to all BACnet topics
mosquitto_sub -h localhost -t 'bacnet/#' -v

# This will block and wait for messages
# You should see BACnet data appearing from the local site
```

### Test 2: Publish Test Message on Local Broker

On **Mosquitto-Local** (10.0.60.3):

```bash
# Open a new terminal/SSH session
ssh ak101@10.0.60.3

# Publish a test message
mosquitto_pub -h localhost -t 'bacnet/test/message' -m 'Hello from local site'

# Expected result:
# The message should appear on the remote subscriber (Test 1)
```

### Test 3: Verify Write Command Path (Remote → Local)

On **Mosquitto-Local** (10.0.60.3):

```bash
# Subscribe to write commands (inbound from remote)
mosquitto_sub -h localhost -t 'bacnet/write/#' -v
```

On **Mosquitto-Remote** (10.0.80.3):

```bash
# Publish a write command
mosquitto_pub -h localhost -t 'bacnet/write/test' -m 'Command from remote'

# Expected result:
# The message should appear on the local subscriber
```

### Test 4: Check Bridge Statistics

On **Mosquitto-Local** (10.0.60.3):

```bash
# View detailed bridge status
sudo journalctl -u mosquitto -n 100 --no-pager | grep -E "(bridge|CONNECT|PUBLISH)"

# Look for:
# - "Received CONNACK" (successful connection)
# - "Sending PUBLISH" (messages being forwarded)
# - "Received PUBLISH" (messages from remote)
```

---

## Troubleshooting Guide

### Problem 1: Bridge Won't Start - "Unknown configuration variable"

**Symptoms**:
```
Error: Unknown configuration variable "#"
Error found at /etc/mosquitto/conf.d/bridge.conf:1
```

**Cause**: Leading spaces/tabs in bridge.conf

**Solution**:
```bash
# Recreate bridge.conf WITHOUT leading spaces
sudo tee /etc/mosquitto/conf.d/bridge.conf > /dev/null << 'EOF'
connection remote-bridge
address 10.0.80.3:1883
topic bacnet/# out 1 "" ""
topic bacnet/write/# in 1 "" ""
cleansession false
try_private true
notifications false
bridge_attempt_unsubscribe true
EOF

sudo systemctl restart mosquitto
```

---

### Problem 2: Bridge Shows "Connection Refused"

**Symptoms**:
```
Error: Connection refused
Bridge remote-bridge connection failed
```

**Diagnosis**:
```bash
# Check if remote broker is reachable
ping -c 3 10.0.80.3

# Check if port 1883 is open
nc -zv 10.0.80.3 1883

# Check remote Mosquitto status
ssh ak101@10.0.80.3 "sudo systemctl status mosquitto"
```

**Solutions**:
1. Verify remote broker is running: `sudo systemctl start mosquitto`
2. Check firewall rules on remote broker: `sudo ufw status`
3. Ensure Mosquitto listens on all interfaces (not just localhost)

---

### Problem 3: Bridge Connects But No Messages Flow

**Symptoms**:
- Bridge shows "Connected" in logs
- Subscriber on remote broker receives nothing

**Diagnosis**:
```bash
# On local broker, publish test message
mosquitto_pub -h localhost -t 'bacnet/test' -m 'test123'

# On remote broker, check if message arrives
mosquitto_sub -h localhost -t 'bacnet/#' -v -C 1

# Check bridge logs for PUBLISH activity
sudo journalctl -u mosquitto -n 50 | grep PUBLISH
```

**Solutions**:
1. Verify topic patterns match:
   - Bridge config: `topic bacnet/# out 1 "" ""`
   - Published topic: `bacnet/test` (must start with "bacnet/")
2. Check QoS level (1 = at least once delivery)
3. Verify no topic prefix/suffix transformations

---

### Problem 4: Authentication Errors

**Symptoms**:
```
Connection Refused: not authorised
```

**Solution 1**: Enable anonymous connections on remote broker (see Part 2)

**Solution 2**: Configure bridge authentication:
```bash
# On local broker, edit bridge.conf
sudo nano /etc/mosquitto/conf.d/bridge.conf

# Add authentication lines:
remote_username mqtt_bridge
remote_password your_secure_password

# Restart
sudo systemctl restart mosquitto
```

---

### Problem 5: Bridge Disconnects Randomly

**Symptoms**:
- Bridge connects initially but disconnects after minutes/hours
- Logs show "Socket error on client remote-bridge"

**Solutions**:
```bash
# Edit bridge.conf and add keep-alive settings
sudo nano /etc/mosquitto/conf.d/bridge.conf

# Add these lines:
keepalive_interval 60
restart_timeout 30

# Restart
sudo systemctl restart mosquitto
```

---

## Verification Checklist

After configuration, verify all items:

- [ ] **Local Broker**: Mosquitto running (`systemctl status mosquitto`)
- [ ] **Remote Broker**: Mosquitto running
- [ ] **Bridge Config**: File exists at `/etc/mosquitto/conf.d/bridge.conf` on local broker
- [ ] **File Permissions**: `mosquitto:mosquitto` ownership, `644` permissions
- [ ] **Syntax Valid**: `mosquitto -c /etc/mosquitto/mosquitto.conf -t` succeeds
- [ ] **Bridge Connected**: Logs show "Received CONNACK on connection remote-bridge"
- [ ] **Outbound Flow**: Test message published locally appears on remote subscriber
- [ ] **Inbound Flow**: Test message published remotely appears on local subscriber
- [ ] **BACnet Data**: Real BACnet data from 192.168.1.35 flows to remote broker
- [ ] **No Errors**: `journalctl -u mosquitto` shows no errors

---

## Bridge Configuration Reference

### Topic Pattern Syntax

```
topic <pattern> <direction> <qos> <local prefix> <remote prefix>
```

**Examples**:

```conf
# Forward all topics under "bacnet/" from local → remote
topic bacnet/# out 1 "" ""

# Bidirectional sync of "sensor/" topics
topic sensor/# both 1 "" ""

# Add prefix when bridging (local "data/" → remote "site1/data/")
topic data/# out 1 "" "site1/"

# Remove prefix (local "site1/sensor/" → remote "sensor/")
topic site1/sensor/# out 1 "site1/" ""
```

### Direction Options

- `out` - Local → Remote only
- `in` - Remote → Local only
- `both` - Bidirectional sync

### QoS Levels

- `0` - At most once (fire and forget)
- `1` - At least once (default for bridge)
- `2` - Exactly once (highest overhead)

---

## Next Steps

Once bridge is confirmed working:

1. **Monitor Bridge Stability**: Check logs daily for first week
2. **Configure Retention**: Set up message retention on remote broker if needed
3. **Add More Sites**: Repeat configuration for additional local sites
4. **Security Hardening**: Configure TLS/SSL certificates for encrypted communication
5. **Monitoring Dashboard**: Verify remote dashboard (10.0.80.2) receives data

---

## References

- **Mosquitto Bridge Documentation**: https://mosquitto.org/man/mosquitto-conf-5.html
- **ROADMAP.md**: BacPipes architecture overview
- **MIGRATION_TO_MODULAR_ARCHITECTURE.md**: Historical context
- **Gitea Repository**: http://10.0.10.2:30008/ak101/dev-bacnet-discovery-docker

---

## Support

For issues or questions:
- Check logs: `sudo journalctl -u mosquitto -n 100`
- Review this guide's troubleshooting section
- Verify network connectivity: `ping`, `nc -zv`
- Test with `mosquitto_pub` and `mosquitto_sub` tools

**Configuration completed by**: ak101
**Date**: 2025-11-22

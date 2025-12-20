# MQTT Connection Status Fix

## Problem

The dashboard displayed inconsistent MQTT broker connection status. Even when data was flowing correctly to TimescaleDB, the status would flip between "connected" and "disconnected" randomly on page refresh.

Additionally, when changing the MQTT broker IP address in settings, the dashboard continued to show "connected" even for invalid/non-existent broker addresses.

## Root Cause

1. **Rapid callback cycles**: The paho-mqtt library fires rapid connect/disconnect callbacks during reconnection attempts. These callbacks were updating the database status faster than the dashboard could display a consistent state.

2. **Stale data after config change**: When the broker configuration changed, the `last_write_time` timestamp from the previous broker was still recent, causing the status to incorrectly show "connected".

3. **Prisma caching**: The frontend API used Prisma's `findFirst()` which could return cached/stale data from connection pooling.

## Solution

### 1. Data Flow Based Status (telegraf/mqtt_to_timescaledb.py)

Removed all status updates from MQTT callbacks and connection functions. Status is now determined solely by actual data flow:

```python
# In main loop (runs every 5 seconds):
if mqtt_config['enabled'] and mqtt_config['broker']:
    data_age = current_time - stats['last_write_time']
    if stats['messages_written'] > 0 and data_age < 120:
        # Data flowing - ensure status shows connected
        update_connection_status('connected', last_connected=True)
    elif data_age > 120:
        # No data for 2+ minutes - mark as disconnected
        update_connection_status('disconnected')
```

### 2. Reset on Config Change

When MQTT configuration changes (broker IP, port, TLS, etc.), reset the tracking counters:

```python
# Reset data flow tracking - new config means we need fresh data
stats['last_write_time'] = current_time  # Start timeout from now
stats['messages_written'] = 0  # Reset counter to detect new data
update_connection_status('connecting')
```

### 3. Raw SQL Query for Fresh Data (frontend API)

Changed the dashboard API to use raw SQL query instead of Prisma ORM to bypass connection pooling cache:

```typescript
const mqttConfigResult = await prisma.$queryRaw<Array<{...}>>`
  SELECT broker, port, "connectionStatus", "lastConnected",
         "tlsEnabled", enabled, "topicPatterns"
  FROM "MqttConfig" WHERE id = 1 LIMIT 1
`
```

### 4. Three-State UI Display

Updated dashboard to show three states with appropriate colors:

| Status | Color | Icon |
|--------|-------|------|
| connected | Green | Wifi (solid) |
| connecting | Amber | Wifi (pulsing) |
| disconnected | Red | WifiOff |

## Status Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Config Changed                            │
│                         │                                    │
│                         ▼                                    │
│                   ┌───────────┐                              │
│                   │connecting │ (amber, pulsing)             │
│                   └─────┬─────┘                              │
│                         │                                    │
│          ┌──────────────┴──────────────┐                     │
│          │                             │                     │
│     Data flows                    No data for                │
│     (messages_written > 0)        2+ minutes                 │
│          │                             │                     │
│          ▼                             ▼                     │
│    ┌───────────┐                ┌──────────────┐             │
│    │ connected │ (green)        │ disconnected │ (red)       │
│    └───────────┘                └──────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

## Files Modified

| File | Changes |
|------|---------|
| `telegraf/mqtt_to_timescaledb.py` | Data flow based status, config change reset |
| `frontend/src/app/api/dashboard/summary/route.ts` | Raw SQL query |
| `frontend/src/app/page.tsx` | Three-state UI with colors |

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Status check interval | 5 seconds | Main loop sleep time |
| Connected timeout | 120 seconds | Max age of last data write to show "connected" |
| Config check interval | 30 seconds | How often to poll for config changes |

## Testing

1. **Normal operation**: Status should consistently show "connected" when data flows
2. **Change to invalid broker**: Status should show "connecting" then "disconnected" after 2 min
3. **Change to valid broker**: Status should show "connecting" then "connected" when data flows
4. **Page refresh**: Status should remain stable, not flip randomly

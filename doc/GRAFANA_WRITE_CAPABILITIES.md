# Grafana Write Capabilities and BacPipes Integration

## Executive Summary

**Short answer**: Grafana is **read-only** by default and cannot directly write to BACnet devices.

**However**: Grafana can be integrated with BacPipes to trigger write commands through custom panels and external API calls.

---

## Grafana's Core Design

### Read-Only Monitoring Tool

Grafana is fundamentally designed as a **data visualization and monitoring platform**, not a control system:

- ✅ **Designed for**: Reading time-series data, creating dashboards, alerting
- ❌ **Not designed for**: Writing values to devices, controlling equipment, sending commands
- 🎯 **Philosophy**: Monitoring and control should be separate for safety and reliability

**Why read-only?**
1. **Safety**: Prevents accidental equipment control from dashboards
2. **Audit trail**: Control commands should go through proper authorization
3. **Reliability**: SCADA/BMS systems handle real-time control better
4. **Separation of concerns**: Dashboards for viewing, APIs/SCADA for control

---

## BacPipes Write Architecture (Current)

### How BacPipes Handles Writes

Currently, BacPipes has a **dedicated write command system** separate from Grafana:

```
┌─────────────────────────────────────────────────────────┐
│  BacPipes Frontend (Next.js)                             │
│  http://localhost:3001/monitoring                        │
│                                                          │
│  [Write Button] → Modal → Priority Select → Submit      │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP POST /api/bacnet/write
                         ↓
┌─────────────────────────────────────────────────────────┐
│  BacPipes API                                            │
│  /api/bacnet/write                                       │
│                                                          │
│  Validates request → Publishes to MQTT                  │
└────────────────────────┬────────────────────────────────┘
                         │ MQTT: bacnet/write/command
                         ↓
┌─────────────────────────────────────────────────────────┐
│  BACnet Worker (Python)                                  │
│  Subscribes to MQTT: bacnet/write/command                │
│                                                          │
│  Receives command → Executes BACnet write → Result      │
└────────────────────────┬────────────────────────────────┘
                         │ MQTT: bacnet/write/result
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Frontend receives result → Shows success/error          │
└─────────────────────────────────────────────────────────┘
```

**Current Write Features**:
- ✅ Write modal in `/monitoring` page
- ✅ Priority level selection (1-16)
- ✅ Priority release (relinquish)
- ✅ Real-time feedback (success/error)
- ✅ Works for all writable BACnet points

**Grafana cannot directly access this** because it's in a separate application.

---

## Integration Options

### Option 1: External Links (Simple, Recommended)

**Concept**: Add links in Grafana panels that open BacPipes monitoring page

**Implementation**:

Add data link to Grafana panel:
```json
{
  "fieldConfig": {
    "defaults": {
      "links": [
        {
          "title": "Control in BacPipes",
          "url": "http://localhost:3001/monitoring?filter=${__field.name}"
        }
      ]
    }
  }
}
```

**User workflow**:
1. User views point in Grafana dashboard
2. Clicks "Control in BacPipes" link
3. Opens BacPipes monitoring page
4. Uses existing write modal to control point

**Advantages**:
- ✅ No Grafana modifications needed
- ✅ Uses existing BacPipes write system
- ✅ Full audit trail maintained
- ✅ Safe (requires conscious navigation)

**Disadvantages**:
- ❌ Requires leaving Grafana
- ❌ Two separate UIs

---

### Option 2: Grafana Button Panel Plugin

**Concept**: Install a plugin that allows buttons in Grafana to trigger HTTP API calls

**Plugin**: [Button Panel](https://grafana.com/grafana/plugins/cloudspout-button-panel/)

**Installation**:
```bash
# Install plugin
docker exec -it bacpipes-grafana grafana-cli plugins install cloudspout-button-panel

# Restart Grafana
docker compose restart grafana
```

**Configuration**:

Add button panel to dashboard:
```json
{
  "type": "cloudspout-button-panel",
  "title": "Equipment Controls",
  "options": {
    "buttons": [
      {
        "text": "Enable AHU",
        "type": "POST",
        "url": "http://frontend:3000/api/bacnet/write",
        "payload": {
          "deviceId": 221,
          "objectType": "binary-output",
          "objectInstance": 105,
          "value": true,
          "priority": 8
        }
      },
      {
        "text": "Disable AHU",
        "type": "POST",
        "url": "http://frontend:3000/api/bacnet/write",
        "payload": {
          "deviceId": 221,
          "objectType": "binary-output",
          "objectInstance": 105,
          "value": false,
          "priority": 8
        }
      }
    ]
  }
}
```

**Advantages**:
- ✅ Control directly from Grafana
- ✅ Clean, button-based interface
- ✅ Can include multiple preset commands
- ✅ Uses existing BacPipes API

**Disadvantages**:
- ⚠️ Requires plugin installation
- ⚠️ Less flexible than full BacPipes UI
- ⚠️ Need to configure each button manually

---

### Option 3: Custom Grafana Panel Plugin (Advanced)

**Concept**: Develop a custom panel that embeds BacPipes write functionality

**Development**:
```bash
# Create custom panel plugin
cd grafana/plugins
npx @grafana/create-plugin
# Name: bacpipes-write-panel
# Type: Panel

# Develop React component that:
# 1. Shows current point value
# 2. Has "Write" button
# 3. Calls BacPipes API on click
# 4. Shows success/error feedback
```

**Example panel code**:
```typescript
// plugins/bacpipes-write-panel/src/components/WritePanel.tsx
import React, { useState } from 'react';

export const WritePanel: React.FC<Props> = ({ data }) => {
  const [value, setValue] = useState('');
  const [loading, setLoading] = useState(false);

  const handleWrite = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://frontend:3000/api/bacnet/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deviceId: data.deviceId,
          objectType: data.objectType,
          objectInstance: data.objectInstance,
          value: parseFloat(value),
          priority: 8
        })
      });
      const result = await response.json();
      alert(result.success ? 'Write successful' : 'Write failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="number"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="New value"
      />
      <button onClick={handleWrite} disabled={loading}>
        {loading ? 'Writing...' : 'Write Value'}
      </button>
    </div>
  );
};
```

**Advantages**:
- ✅ Full integration with Grafana
- ✅ Custom UI tailored to your needs
- ✅ Can include validation, confirmations
- ✅ Professional appearance

**Disadvantages**:
- ❌ Significant development effort
- ❌ Requires React/TypeScript knowledge
- ❌ Must maintain custom plugin

---

### Option 4: Grafana Alerting → Webhook → BacPipes (Automated)

**Concept**: Use Grafana alerts to automatically trigger BacPipes writes

**Use case**: "If temperature > 30°C, open cooling valve to 100%"

**Setup**:

1. **Create alert rule** in Grafana:
   ```
   Alert: High Temperature
   Condition: temp > 30
   For: 5 minutes
   ```

2. **Create contact point** (webhook):
   ```
   Type: Webhook
   URL: http://frontend:3000/api/bacnet/write
   Method: POST
   Body:
   {
     "deviceId": 221,
     "objectType": "analog-output",
     "objectInstance": 104,
     "value": 100,
     "priority": 8
   }
   ```

3. **Attach to alert**

**Advantages**:
- ✅ Fully automated control
- ✅ Rule-based logic
- ✅ No manual intervention
- ✅ Perfect for safety shutdowns

**Disadvantages**:
- ⚠️ Requires careful testing
- ⚠️ Risk of automation errors
- ⚠️ Should have manual override

---

## Recommended Approach

### For Your Use Case

**Recommendation**: Use **Option 1 (External Links)** for now, consider **Option 2 (Button Panel)** later

**Reasoning**:
1. **You already have a working write system** in BacPipes monitoring page
2. **Grafana is for monitoring**, BacPipes is for control (separation of concerns)
3. **External links** maintain clear distinction between viewing and controlling
4. **Button panel** can be added later if clients request direct control

---

## Implementation: External Links in Existing Dashboards

### Update Executive Overview Dashboard

Edit `/home/ak101/BacPipes/grafana/provisioning/dashboards/json/executive_overview.json`:

```json
{
  "panels": [
    {
      "id": 2,
      "title": "Temperature Trends (Last 24 Hours)",
      "type": "timeseries",
      "fieldConfig": {
        "defaults": {
          "links": [
            {
              "title": "Control ${__field.name}",
              "url": "http://localhost:3001/monitoring?filter=${__field.name}",
              "targetBlank": true
            }
          ]
        }
      }
    }
  ]
}
```

**Result**: Clicking on any temperature series opens BacPipes monitoring page filtered to that point

---

### Update Equipment Detail Dashboard

Edit `/home/ak101/BacPipes/grafana/provisioning/dashboards/json/equipment_detail.json`:

Add control link to table panel:

```json
{
  "id": 6,
  "title": "All Point Values - $device_name",
  "type": "table",
  "fieldConfig": {
    "overrides": [
      {
        "matcher": {"id": "byName", "options": "haystack_name"},
        "properties": [
          {
            "id": "links",
            "value": [
              {
                "title": "Control Point",
                "url": "http://localhost:3001/monitoring?filter=${__value.text}",
                "targetBlank": true
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**Result**: Each point name in table becomes a clickable link to BacPipes control interface

---

## Security Considerations

### Why Separation is Important

**Grafana (Read-Only)**:
- Can be shared with clients, management, non-technical users
- Kiosk mode prevents accidental changes
- Dashboards can be public or embedded

**BacPipes (Read-Write)**:
- Should be restricted to authorized operators
- Requires understanding of BACnet priority arrays
- Write commands should be audited

**If you integrate writes into Grafana**:
- ⚠️ Anyone with Grafana access can control equipment
- ⚠️ Kiosk mode users might accidentally trigger writes
- ⚠️ Audit trail becomes more complex

---

## Comparison Table

| Integration Method | Complexity | Safety | Client-Friendly | Recommended For |
|-------------------|-----------|--------|-----------------|-----------------|
| External Links | ⭐ Low | ✅ High | ⭐⭐⭐ Medium | Current setup |
| Button Panel Plugin | ⭐⭐ Medium | ⚠️ Medium | ⭐⭐⭐⭐ High | Future enhancement |
| Custom Panel Plugin | ⭐⭐⭐⭐ High | ⚠️ Medium | ⭐⭐⭐⭐⭐ Very High | Large deployments |
| Alert Webhooks | ⭐⭐⭐ Medium | ⚠️ Low | ⭐⭐⭐⭐ High | Automation |
| No Integration | ⭐ Low | ✅ Very High | ⭐⭐ Low | Monitoring only |

---

## Next Steps

### Immediate Actions (Recommended)

1. **Add external links** to existing dashboards
2. **Document** in user guide: "Click point name to control"
3. **Test** link workflow with clients

### Future Enhancements

1. **Install Button Panel plugin** if clients request direct control
2. **Create dedicated control dashboard** with preset commands
3. **Implement alert-based automation** for critical scenarios

### Advanced (Optional)

1. **Develop custom panel plugin** for full BacPipes integration
2. **Create mobile app** for on-site control
3. **Implement role-based access** (viewers vs operators)

---

## Example: Complete Integration Workflow

**Scenario**: Client views executive dashboard, wants to adjust setpoint

**Current workflow** (with external links):
```
1. Client opens: http://localhost:3002/d/executive-overview?kiosk
2. Sees temperature trend is high
3. Clicks on "Supply Air Temp" series → "Control Supply Air Temp" link
4. Opens: http://localhost:3001/monitoring?filter=Supply%20Air%20Temp
5. Clicks "Write" button on point
6. Enters new value, selects priority
7. Confirms write
8. Returns to Grafana to see effect
```

**Future workflow** (with button panel):
```
1. Client opens: http://localhost:3002/d/executive-overview?kiosk
2. Sees temperature trend is high
3. Clicks "Decrease Setpoint" button in Grafana
4. Sees confirmation message
5. Dashboard updates automatically
```

---

## Conclusion

**For BacPipes:**

1. **Grafana is purely for monitoring** (read-only)
2. **BacPipes frontend handles writes** (existing system works well)
3. **Integration is possible** via external links or plugins
4. **Recommended approach**: Add external links for now, evaluate button panel later

**Philosophy**: Keep monitoring (Grafana) and control (BacPipes) separate for safety and clarity. Integrate only where it improves workflow without compromising safety.

**Questions?** Let me know if you want to implement any of these integration options!

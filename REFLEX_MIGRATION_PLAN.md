# BacPipes Reflex Migration - Complete Feature Checklist

## Missing Features Analysis

### 1. POINTS PAGE - Missing Features

#### A. Bulk Configuration Card
- [ ] Site ID input (applies to ALL points)
- [ ] Device-to-Equipment Mapping Table:
  - Device ID, Name, IP, Points Count (read-only)
  - Equipment Type dropdown (ahu, vav, fcu, chiller, chwp, cwp, ct, boiler, custom)
  - Equipment ID input
- [ ] "Apply to All Points" button

#### B. MQTT Topic Export
- [ ] Export TXT button (downloads topic list)
- [ ] Export JSON button (downloads subscriber guide)

#### C. Filters (4-column layout)
- [ ] Device filter dropdown (All Devices + device names)
- [ ] Object Type filter dropdown (All Types + object types)
- [ ] MQTT Status filter (All, MQTT Enabled, MQTT Disabled)
- [ ] Search input (text search on point names)
- [ ] Clear Filters button

#### D. Bulk Operations Bar
- [ ] Select All checkbox in table header
- [ ] Individual point checkboxes
- [ ] "X points selected" counter
- [ ] Enable MQTT button (bulk)
- [ ] Disable MQTT button (bulk)
- [ ] Clear Selection button

#### E. Points Table Enhancements
- [ ] Checkbox column
- [ ] Point Name with subtitle (type:instance • device)
- [ ] Current Value column with units
- [ ] MQTT Topic column with copy button
- [ ] Status badge (Enabled/Disabled)

### 2. POINT EDITOR MODAL - Missing Features

#### A. Point Information Section (read-only)
- [ ] Object Type display
- [ ] Instance Number display
- [ ] Units display
- [ ] Device Name display

#### B. Haystack Decision Tree Guide
- [ ] Info box explaining 5-step process

#### C. Bulk Configuration Display (read-only)
- [ ] Site ID (from bulk config)
- [ ] Equipment Type (from bulk config)
- [ ] Equipment ID (from bulk config)

#### D. Haystack Field Dropdowns (CRITICAL)
- [ ] Point Function: sensor, sp, cmd, synthetic
- [ ] Quantity: temp, humidity, co2, flow, pressure, speed, percent, power, run, pos, level, occupancy, enthalpy, dewpoint, schedule, calendar, datetime, date
- [ ] Subject: air, water, chilled-water, hot-water, steam, refrig, gas
- [ ] Location: zone, supply, return, outside, mixed, exhaust, entering, leaving, coil, filter, economizer
- [ ] Qualifier: actual, effective, min, max, nominal, alarm, enable, reset, manual, auto
- [ ] Display Name input

#### E. Common Patterns Reference
- [ ] Collapsible section with pattern examples

#### F. MQTT Configuration Section
- [ ] "Publish to MQTT Broker" checkbox
- [ ] "Point is Writable" checkbox
- [ ] Write Validation section (when writable):
  - Min Value input
  - Max Value input
  - Validation preview
- [ ] Polling Interval input
- [ ] QoS Level dropdown (0, 1, 2)
- [ ] MQTT Topic Preview box

### 3. SETTINGS PAGE - Missing Features

#### A. MQTT Subscription Section
- [ ] "Enable Subscription" toggle
- [ ] Subscribe Topic Pattern input
- [ ] Subscribe QoS dropdown

#### B. System Configuration
- [ ] Default Poll Interval input
- [ ] "Apply to All MQTT Points" button
- [ ] Full Timezone dropdown (UTC, Asia, Europe, Americas, Australia, Middle East)
- [ ] Current Time display (live)

#### C. TLS Certificate Management
- [ ] CA Certificate upload button
- [ ] CA Certificate delete button
- [ ] Status display (configured/not configured)

### 4. DASHBOARD PAGE - Missing Features

#### A. Header Controls
- [ ] Auto-refresh checkbox toggle
- [ ] Refresh interval display

#### B. Status Cards Enhancement
- [ ] Network Configuration card
- [ ] MQTT Connection Status with animated indicator
- [ ] System Settings card (timezone, poll intervals)

#### C. Statistics
- [ ] Total Points
- [ ] Enabled Points
- [ ] Publishing Points
- [ ] Device Count

### 5. DISCOVERY PAGE - Missing Features

#### A. Network Interface Selection
- [ ] Dropdown with auto-detected interfaces
- [ ] Fallback to text input

#### B. Scanner Device ID
- [ ] Input field (default: 3001234)

---

## Implementation Priority

### Phase 1: Fix Broken Features (URGENT)
1. Fix MQTT toggle in point_table.py
2. Fix point editor opening
3. Fix logout redirect

### Phase 2: Point Editor Complete Overhaul
1. Add all Haystack dropdowns with proper options
2. Add MQTT configuration section
3. Add write validation fields
4. Add read-only point info section

### Phase 3: Points Page Features
1. Add all filters
2. Add bulk operations (select all, bulk enable/disable)
3. Add bulk configuration card
4. Add export buttons

### Phase 4: Settings Page Complete
1. Add MQTT subscription section
2. Add poll interval with apply all
3. Add full timezone dropdown
4. Add TLS certificate management

### Phase 5: Dashboard & Discovery
1. Enhance dashboard status cards
2. Add auto-refresh toggle
3. Add network interface dropdown to discovery

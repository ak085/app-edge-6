# Grafana Client Viewing Guide

## Overview

This guide explains how to share Grafana dashboards with clients, management, or non-technical users in a professional, read-only manner without exposing the development/configuration interface.

## Dashboard Viewing Modes

### 1. Kiosk Mode (Recommended for Client Presentations)

**Purpose**: Hides all Grafana navigation, menus, and controls. Shows only the dashboard.

**URL Format**:
```
http://localhost:3002/d/<dashboard-uid>?kiosk
```

**Examples**:
```bash
# Executive Overview in kiosk mode
http://localhost:3002/d/executive-overview?kiosk

# Equipment Detail in kiosk mode
http://localhost:3002/d/equipment-detail?kiosk

# Alarms Monitoring in kiosk mode
http://localhost:3002/d/alarms-monitoring?kiosk
```

**Features**:
- ✅ Clean, professional appearance
- ✅ No edit buttons or menus
- ✅ Still shows time picker and refresh controls
- ✅ Ideal for wall-mounted displays
- ✅ Perfect for client meetings (projector/screenshare)

**Keyboard Shortcut**: Press `d` + `v` to cycle through view modes

---

### 2. TV Mode (Best for Wall Displays)

**Purpose**: Full-screen mode with auto-rotating playlists. Hides even more UI elements.

**URL Format**:
```
http://localhost:3002/d/<dashboard-uid>?kiosk=tv
```

**Examples**:
```bash
# Executive Overview in TV mode
http://localhost:3002/d/executive-overview?kiosk=tv
```

**Features**:
- ✅ Hides time picker and refresh controls
- ✅ Maximum screen real estate
- ✅ Auto-refresh works silently
- ✅ Ideal for lobby displays or NOC walls
- ❌ Cannot change time range (use URL parameters)

---

### 3. Viewer Role (Read-Only Access)

**Purpose**: Give clients login access but prevent editing.

**Setup**:

1. **Create viewer user** (if needed):
```bash
# Access Grafana container
docker exec -it bacpipes-grafana grafana-cli admin reset-admin-password newpassword

# Or create user via UI:
# Configuration → Users → New User
# Role: Viewer
```

2. **Set dashboard permissions**:
   - Open dashboard → Settings (gear icon) → Permissions
   - Add "Viewer" role with "View" permission
   - Remove "Editor" and "Admin" if needed

**Features**:
- ✅ Clients have their own login
- ✅ Cannot edit or delete dashboards
- ✅ Can change time ranges and refresh
- ✅ Can use all panel features (zoom, drill-down)
- ❌ Still shows some Grafana UI (less clean than kiosk)

---

### 4. Anonymous Access (Public Dashboards)

**Purpose**: Share dashboards without requiring login.

**Setup**:

Edit Grafana configuration:

```bash
# Edit grafana/config/grafana.ini
docker exec -it bacpipes-grafana vi /etc/grafana/grafana.ini

# Add these lines:
[auth.anonymous]
enabled = true
org_name = Main Org.
org_role = Viewer

# Restart Grafana
docker compose restart grafana
```

**Security Considerations**:
- ⚠️ Anyone with the URL can view dashboards
- ⚠️ Suitable only for internal networks (not internet-facing)
- ✅ Good for trusted environments (office, factory floor)
- ✅ No password management needed

**URL for clients**:
```
http://localhost:3002/d/executive-overview?kiosk
```

---

### 5. Snapshot Sharing (Time-Frozen View)

**Purpose**: Share a static snapshot of dashboard at a specific time.

**How to Create**:
1. Open dashboard
2. Click "Share" icon (top right)
3. Select "Snapshot" tab
4. Set expiration time (1 hour, 1 day, 1 week, never)
5. Click "Publish to snapshots.raintank.io" or "Local Snapshot"
6. Copy the snapshot URL

**Features**:
- ✅ Data is frozen at snapshot time (no live updates)
- ✅ Can share externally (if using raintank.io)
- ✅ Auto-expires after set duration
- ❌ Not suitable for live monitoring
- ✅ Perfect for reports or incident postmortems

---

### 6. Playlist Mode (Auto-Rotating Dashboards)

**Purpose**: Automatically cycle through multiple dashboards.

**Setup**:
1. Go to Dashboards → Playlists → New Playlist
2. Add dashboards to playlist:
   - Executive Overview (30 seconds)
   - Equipment Detail (45 seconds)
   - Alarms Monitoring (30 seconds)
3. Save playlist

**URL**:
```
http://localhost:3002/playlists/play/<playlist-id>?kiosk
```

**Features**:
- ✅ Perfect for NOC/control room displays
- ✅ Shows multiple perspectives automatically
- ✅ Combines with kiosk mode
- ✅ Configurable rotation intervals

---

## Best Practices for Client Presentations

### Option 1: Kiosk Mode (Recommended)

**When to use**: Client meetings, presentations, screensharing

**Setup**:
```bash
# 1. Open dashboard in kiosk mode
http://localhost:3002/d/executive-overview?kiosk

# 2. Optional: Add time range parameters
http://localhost:3002/d/executive-overview?kiosk&from=now-24h&to=now

# 3. Optional: Set refresh interval
http://localhost:3002/d/executive-overview?kiosk&refresh=30s
```

**Advantages**:
- Clean, professional appearance
- No accidental clicks on edit buttons
- Client sees only relevant data
- Easy to bookmark and share

---

### Option 2: Anonymous Access + Kiosk Mode

**When to use**: Internal stakeholders, factory floor, office displays

**Setup**:
```bash
# Enable anonymous access (see section 4 above)
# Then share URLs in kiosk mode
http://10.0.10.2:3002/d/executive-overview?kiosk
```

**Advantages**:
- No login required
- Works on any device on network
- Can be embedded in internal websites
- QR code can be generated for mobile access

---

### Option 3: Dedicated "Client" Organization

**When to use**: Multiple clients, need strict isolation

**Setup**:
1. Create new organization: Configuration → Organizations → New Organization
2. Create dashboards in client org (or copy existing)
3. Create viewer users for client org
4. Share login credentials

**Advantages**:
- Complete data isolation
- Different branding per client
- Separate user management
- Client cannot see other clients' data

---

## URL Parameters Reference

### Common Parameters

| Parameter | Values | Example | Purpose |
|-----------|--------|---------|---------|
| `kiosk` | (empty), `tv` | `?kiosk` | Hide UI elements |
| `from` | Time expression | `&from=now-24h` | Set start time |
| `to` | Time expression | `&to=now` | Set end time |
| `refresh` | Duration | `&refresh=30s` | Auto-refresh interval |
| `theme` | `light`, `dark` | `&theme=light` | Color theme |
| `var-<variable>` | Variable value | `&var-equipment_type=AHU` | Set template variable |

### Example URLs

**Executive overview, last 7 days, dark theme, 1-minute refresh**:
```
http://localhost:3002/d/executive-overview?kiosk&from=now-7d&to=now&refresh=1m&theme=dark
```

**Equipment detail for specific AHU**:
```
http://localhost:3002/d/equipment-detail?kiosk&var-equipment_type=AHU&var-device_name=Excelsior
```

**Alarms dashboard, last hour, TV mode**:
```
http://localhost:3002/d/alarms-monitoring?kiosk=tv&from=now-1h&to=now
```

---

## Embedding Dashboards

### In Internal Websites

**HTML iframe example**:
```html
<iframe
  src="http://localhost:3002/d/executive-overview?kiosk&theme=light"
  width="100%"
  height="600"
  frameborder="0">
</iframe>
```

### In Microsoft Teams/Slack

Use the snapshot feature or anonymous kiosk URLs:
```
http://10.0.10.2:3002/d/executive-overview?kiosk
```

---

## Mobile Access

### Grafana Mobile App

**Setup**:
1. Install "Grafana" app (iOS/Android)
2. Add server: http://10.0.10.2:3002
3. Login (or use anonymous if enabled)

**Features**:
- Native mobile interface
- Push notifications (with Grafana Cloud)
- Offline snapshots
- Touch-optimized controls

### Mobile Browser

Use kiosk URLs with responsive dashboards:
```
http://10.0.10.2:3002/d/executive-overview?kiosk
```

---

## Access Control Matrix

| Mode | Login Required | Can Edit | Can View All | Best For |
|------|---------------|----------|--------------|----------|
| Kiosk Mode | Yes (default) | Depends on user role | Yes | Client meetings |
| TV Mode | Yes (default) | No | Yes | Wall displays |
| Viewer Role | Yes | No | Depends on permissions | Client logins |
| Anonymous | No | No | Yes | Internal sharing |
| Snapshot | No | No | Only snapshot data | Reports |
| Playlist | Depends | No | Playlist dashboards | NOC displays |

---

## Security Recommendations

### For Internal Networks (Current Setup)

✅ **Current configuration is secure** for:
- Office networks
- Factory floor displays
- Internal stakeholder access

⚠️ **Recommendations**:
- Keep Grafana on internal network only (not internet-facing)
- Use anonymous access for convenience
- Use kiosk mode to prevent accidental edits
- Regularly audit user list

### For External Client Access

❌ **Do NOT expose directly to internet**

✅ **Instead, use**:
1. **VPN**: Clients connect via VPN, then access Grafana
2. **Reverse Proxy**: Nginx/Caddy with TLS + authentication
3. **Snapshots**: Email time-frozen snapshots
4. **PDF Reports**: Use Grafana reporting feature (Enterprise) or screenshots

---

## Quick Reference: Client Sharing Checklist

### For Executive Presentation
- [ ] Open dashboard in kiosk mode (`?kiosk`)
- [ ] Set appropriate time range in URL
- [ ] Test on presentation screen before meeting
- [ ] Have backup: screenshot or PDF export

### For Wall Display (NOC/Lobby)
- [ ] Create playlist with multiple dashboards
- [ ] Use TV mode (`?kiosk=tv`)
- [ ] Set auto-refresh to 30-60 seconds
- [ ] Test on display hardware (resolution, color)

### For Client Login Access
- [ ] Create user with "Viewer" role
- [ ] Set dashboard permissions
- [ ] Provide URL + credentials
- [ ] Confirm client can view but not edit

### For QR Code/Mobile
- [ ] Enable anonymous access (if internal)
- [ ] Generate kiosk URL
- [ ] Create QR code (use qr-code generator)
- [ ] Test on mobile devices

---

## Troubleshooting

### Dashboard Shows "Permission Denied"
**Solution**: Check user role and dashboard permissions

### Kiosk Mode Still Shows Menus
**Solution**: Ensure URL has `?kiosk` (not `&kiosk`)

### Anonymous Access Not Working
**Solution**: Verify `grafana.ini` has `enabled = true` under `[auth.anonymous]`

### Dashboard Not Auto-Refreshing
**Solution**: Add `&refresh=30s` to URL, or check dashboard settings

### Mobile View is Cramped
**Solution**: Use responsive panels, test dashboard on mobile before sharing

---

## External Access (Production Setup)

**For production deployments with internet access**, use:

### Reverse Proxy with TLS (Nginx Example)

```nginx
server {
    listen 443 ssl;
    server_name grafana.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Basic Authentication Layer

```nginx
location / {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:3002;
}
```

---

## Summary

**For your use case (showing clients dashboards)**:

1. **Best approach**: Use **kiosk mode** with **anonymous access**
   ```
   http://localhost:3002/d/executive-overview?kiosk
   ```

2. **Setup steps**:
   - Enable anonymous access in Grafana (see section 4)
   - Share kiosk URLs with clients
   - Optionally create playlists for auto-rotation

3. **Security**: Since you're on internal network (10.0.x.x), this is safe

4. **Professional appearance**: Kiosk mode removes all technical UI, shows only data

**Need help implementing any of these options? Let me know which approach fits your use case best!**

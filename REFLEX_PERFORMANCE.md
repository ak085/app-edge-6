# Reflex Performance Guide: Fixing Slow Multi-User Page Loading

This document explains a common performance issue in Reflex applications and how to fix it. Use this as a reference when building Reflex-based admin GUIs for MQTT brokers, databases, and other backend tools.

---

## Table of Contents

1. [Problem Description](#problem-description)
2. [Root Causes](#root-causes)
3. [How to Identify the Problem](#how-to-identify-the-problem)
4. [Solution Overview](#solution-overview)
5. [Fix #1: Background Tasks](#fix-1-background-tasks)
6. [Fix #2: Eliminate N+1 Queries](#fix-2-eliminate-n1-queries)
7. [Fix #3: Add Pagination](#fix-3-add-pagination)
8. [Checklist for Other Projects](#checklist-for-other-projects)
9. [When Reflex is NOT the Right Choice](#when-reflex-is-not-the-right-choice)

---

## Problem Description

### Symptoms

- UI loads slowly or freezes when multiple users access it simultaneously
- Browser shows loading spinner for extended periods
- Second browser tab/window takes much longer to load than the first
- Page becomes unresponsive during data operations
- WebSocket disconnections under load

### What We Observed

With BacPipes (BACnet-to-MQTT gateway admin UI):
- Single user: Page loads in ~1 second
- Two users simultaneously: Page loads in ~5-10 seconds
- Three+ users: Page fails to load, timeouts occur

---

## Root Causes

### 1. Blocking Database Operations in Event Handlers

Reflex uses a **single event queue** per state class. When an event handler performs synchronous database operations, it blocks the queue for ALL users.

```python
# BAD: Blocks the event queue
async def load_data(self):
    with rx.session() as session:  # ← Synchronous, blocks event loop
        results = session.exec(select(MyModel)).all()
    self.data = results
```

### 2. N+1 Query Pattern

Loading a list of items, then querying related data for each item individually:

```python
# BAD: N+1 queries (1 query + N queries for each device)
devices = session.exec(select(Device)).all()
for device in devices:
    point_count = session.exec(
        select(func.count(Point.id)).where(Point.deviceId == device.id)
    ).one()  # ← Executes N times!
```

With 100 devices, this runs **101 queries** instead of 1.

### 3. Loading All Data Into Memory

No pagination means loading thousands of records:

```python
# BAD: Loads everything
results = session.exec(select(Point)).all()  # Could be 10,000+ rows
self.points = [serialize(p) for p in results]
```

### 4. Filter Changes Trigger Full Reloads

Every filter change reloads all data from scratch:

```python
# BAD: Full reload on every keystroke
async def set_search_query(self, query: str):
    self.search_query = query
    async for _ in self.load_points():  # ← Reloads everything
        pass
```

---

## How to Identify the Problem

### 1. Check for Synchronous Database Calls

Search your state files for these patterns:

```bash
grep -n "with rx.session" bacpipes/state/*.py
grep -n "session.exec" bacpipes/state/*.py
```

If these appear inside `async def` methods WITHOUT `run_in_executor`, they block.

### 2. Look for Loops with Database Queries

```bash
grep -B5 -A5 "for.*in.*:" bacpipes/state/*.py | grep -A3 "session"
```

Any `session.exec()` inside a `for` loop is an N+1 problem.

### 3. Check for Missing Pagination

Look for `.all()` calls without `.limit()`:

```bash
grep -n "\.all()" bacpipes/state/*.py
```

### 4. Test with Multiple Browsers

1. Open the app in Browser 1 → Note load time
2. Open in Browser 2 simultaneously → Compare load time
3. If Browser 2 is significantly slower, you have blocking operations

---

## Solution Overview

| Problem | Solution |
|---------|----------|
| Blocking DB operations | Background tasks + thread pool |
| N+1 queries | JOIN queries with GROUP BY |
| Loading all data | Pagination (100 items/page) |
| Filter reloads | Background tasks for filters |

---

## Fix #1: Background Tasks

### Before (Blocking)

```python
async def load_dashboard(self):
    self.is_loading = True
    yield

    with rx.session() as session:
        # These block the event loop!
        self.total_devices = session.exec(
            select(func.count(Device.id))
        ).one()
        # ... more queries

    self.is_loading = False
```

### After (Non-Blocking)

```python
def _load_dashboard_sync(self) -> dict:
    """Synchronous database operations run in thread pool."""
    result = {
        "total_devices": 0,
        "devices": [],
    }

    with rx.session() as session:
        result["total_devices"] = session.exec(
            select(func.count(Device.id))
        ).one()
        # ... more queries

    return result

@rx.event(background=True)
async def load_dashboard(self):
    """Load dashboard data (non-blocking)."""
    async with self:
        self.is_loading = True

    # Run blocking DB operations in thread pool
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, self._load_dashboard_sync)

    async with self:
        self.total_devices = result["total_devices"]
        self.devices = result["devices"]
        self.is_loading = False
```

### Key Points

1. **`@rx.event(background=True)`** - Marks the event handler as a background task
2. **`async with self:`** - Required to modify state in background tasks
3. **`run_in_executor(None, sync_func)`** - Runs blocking code in thread pool
4. **Separate sync helper** - `_load_dashboard_sync()` contains all DB operations

---

## Fix #2: Eliminate N+1 Queries

### Before (N+1 Pattern)

```python
# 1 query to get devices
devices = session.exec(select(Device).order_by(Device.deviceName)).all()

# N queries to get point counts
for device in devices:
    point_count = session.exec(
        select(func.count(Point.id)).where(Point.deviceId == device.id)
    ).one()
    result.append({
        "id": device.id,
        "deviceName": device.deviceName,
        "pointCount": point_count,  # ← N+1 problem
    })
```

### After (Single JOIN Query)

```python
from sqlmodel import func

# Single query with JOIN and GROUP BY
device_query = (
    select(
        Device.id,
        Device.deviceName,
        Device.ipAddress,
        Device.enabled,
        func.count(Point.id).label("point_count")
    )
    .outerjoin(Point, Device.id == Point.deviceId)
    .group_by(Device.id)
    .order_by(Device.deviceName)
)
devices_result = session.exec(device_query).all()

# Results already include point counts
result = [
    {
        "id": row[0],
        "deviceName": row[1],
        "ipAddress": row[2],
        "enabled": row[3],
        "pointCount": row[4],  # ← From GROUP BY, no extra query
    }
    for row in devices_result
]
```

### Common JOIN Patterns

**Get items with related count:**
```python
select(
    Parent.id,
    Parent.name,
    func.count(Child.id).label("child_count")
).outerjoin(Child, Parent.id == Child.parent_id).group_by(Parent.id)
```

**Get items with related data:**
```python
select(Point, Device).join(Device, Point.deviceId == Device.id)

# Access both in results:
for point, device in session.exec(query).all():
    print(point.pointName, device.deviceName)
```

---

## Fix #3: Add Pagination

### State Variables

```python
class PointsState(rx.State):
    # Pagination
    page: int = 0
    page_size: int = 100
    total_count: int = 0

    @rx.var
    def total_pages(self) -> int:
        if self.total_count == 0:
            return 1
        return (self.total_count + self.page_size - 1) // self.page_size

    @rx.var
    def has_next_page(self) -> bool:
        return (self.page + 1) < self.total_pages

    @rx.var
    def has_prev_page(self) -> bool:
        return self.page > 0

    @rx.var
    def page_display(self) -> str:
        if self.total_count == 0:
            return "No items"
        start = self.page * self.page_size + 1
        end = min((self.page + 1) * self.page_size, self.total_count)
        return f"{start}-{end} of {self.total_count}"
```

### Paginated Query

```python
def _load_points_sync(self) -> dict:
    with rx.session() as session:
        # Build base query
        query = select(Point, Device).join(Device, Point.deviceId == Device.id)

        # Apply filters...
        if self.filter_device_name != "All Devices":
            query = query.where(Device.deviceName == self.filter_device_name)

        # Get total count BEFORE pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_count = session.exec(count_query).one()

        # Apply pagination
        query = query.order_by(Point.pointName)
        query = query.offset(self.page * self.page_size).limit(self.page_size)

        results = session.exec(query).all()

    return {"points": [...], "total_count": total_count}
```

### Pagination Methods

```python
@rx.event(background=True)
async def next_page(self):
    async with self:
        if (self.page + 1) * self.page_size < self.total_count:
            self.page += 1
    await self._reload_points()

@rx.event(background=True)
async def prev_page(self):
    async with self:
        if self.page > 0:
            self.page -= 1
    await self._reload_points()

@rx.event(background=True)
async def first_page(self):
    async with self:
        self.page = 0
    await self._reload_points()
```

### Pagination UI Component

```python
def pagination_controls() -> rx.Component:
    return rx.hstack(
        rx.button(
            rx.icon("chevrons-left", size=14),
            variant="outline",
            size="1",
            on_click=MyState.first_page,
            disabled=~MyState.has_prev_page,
        ),
        rx.button(
            rx.icon("chevron-left", size=14),
            variant="outline",
            size="1",
            on_click=MyState.prev_page,
            disabled=~MyState.has_prev_page,
        ),
        rx.text(MyState.page_display, size="2", color="gray"),
        rx.button(
            rx.icon("chevron-right", size=14),
            variant="outline",
            size="1",
            on_click=MyState.next_page,
            disabled=~MyState.has_next_page,
        ),
        spacing="3",
        align="center",
        justify="center",
    )
```

---

## Checklist for Other Projects

Use this checklist when fixing performance in other Reflex GUIs:

### Step 1: Audit State Files

- [ ] List all `async def` methods that use `rx.session()`
- [ ] Identify methods called on page load (`on_mount`)
- [ ] Identify methods called on user actions (filters, searches)

### Step 2: Convert to Background Tasks

For each method identified:

- [ ] Create `_method_name_sync(self) -> dict` helper with DB operations
- [ ] Add `@rx.event(background=True)` decorator to async method
- [ ] Use `async with self:` for state modifications
- [ ] Use `await loop.run_in_executor(None, self._method_name_sync)`

### Step 3: Fix N+1 Queries

- [ ] Search for `for` loops containing `session.exec()`
- [ ] Replace with JOIN + GROUP BY queries
- [ ] Use `outerjoin()` when child records may not exist

### Step 4: Add Pagination

For tables with potentially many rows:

- [ ] Add `page`, `page_size`, `total_count` state variables
- [ ] Add computed vars: `total_pages`, `has_next_page`, `has_prev_page`
- [ ] Modify query to use `.offset()` and `.limit()`
- [ ] Add pagination UI controls
- [ ] Reset `page = 0` when filters change

### Step 5: Test

- [ ] Open app in 2-3 browsers simultaneously
- [ ] Verify all load quickly
- [ ] Click Refresh in multiple browsers at once
- [ ] Verify no timeouts or freezes

---

## When Reflex is NOT the Right Choice

Reflex is ideal for:
- Admin/configuration interfaces
- Backend tool GUIs
- Internal dashboards (< 50 concurrent users)
- Python-native integrations

Reflex is NOT ideal for:
- Live monitoring dashboards with real-time updates
- High-concurrency public applications (100+ users)
- Sub-second update frequencies to many clients

For live dashboards showing hundreds of AHUs with real-time values, use:
- React/Vue + WebSocket API
- Grafana
- Purpose-built SCADA software

---

## Files Modified in BacPipes Fix

| File | Changes |
|------|---------|
| `state/dashboard_state.py` | Background tasks, JOIN queries |
| `state/points_state.py` | Background tasks, JOINs, pagination |
| `state/discovery_state.py` | Background tasks, aggregate queries |
| `state/settings_state.py` | Background tasks |
| `state/worker_state.py` | Background tasks |
| `components/point_table.py` | Pagination UI |

---

## Quick Reference: Import Statements

```python
import asyncio
from sqlmodel import select, func
import reflex as rx

# For background task with DB operations:
@rx.event(background=True)
async def my_method(self):
    async with self:
        self.is_loading = True

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, self._my_method_sync)

    async with self:
        self.data = result
        self.is_loading = False
```

---

**Last Updated:** 2026-02-01

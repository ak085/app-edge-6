"""Points state for BacPipes."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import reflex as rx
from sqlmodel import select, func

from ..models.device import Device
from ..models.point import Point


# Dropdown option mappings
POINT_FUNCTION_MAP = {
    "sensor": "sensor - Measures/reads values",
    "sp": "sp - Sets target/desired values",
    "cmd": "cmd - Commands/controls equipment",
    "synthetic": "synthetic - Computed/calculated data",
}

QUANTITY_MAP = {
    "temp": "temp - Temperature",
    "humidity": "humidity - Humidity",
    "co2": "co2 - CO2 level",
    "flow": "flow - Flow rate",
    "pressure": "pressure - Pressure",
    "speed": "speed - Speed",
    "percent": "percent - Percentage",
    "power": "power - Power",
    "run": "run - Run status",
    "pos": "pos - Position",
    "level": "level - Level",
    "occupancy": "occupancy - Occupancy",
    "enthalpy": "enthalpy - Enthalpy",
    "dewpoint": "dewpoint - Dew point",
    "schedule": "schedule - Schedule (meta-data)",
    "calendar": "calendar - Calendar (meta-data)",
    "datetime": "datetime - Date/Time (meta-data)",
    "date": "date - Date (meta-data)",
}

SUBJECT_MAP = {
    "": "-- Select --",
    "air": "air - Air",
    "water": "water - Water",
    "chilled-water": "chilled-water - Chilled water",
    "hot-water": "hot-water - Hot water",
    "steam": "steam - Steam",
    "refrig": "refrig - Refrigerant",
    "gas": "gas - Gas",
}

LOCATION_MAP = {
    "": "-- Select --",
    "zone": "zone - Zone",
    "supply": "supply - Supply",
    "return": "return - Return",
    "outside": "outside - Outside",
    "mixed": "mixed - Mixed",
    "exhaust": "exhaust - Exhaust",
    "entering": "entering - Entering",
    "leaving": "leaving - Leaving",
    "coil": "coil - Coil",
    "filter": "filter - Filter",
    "economizer": "economizer - Economizer",
}

QUALIFIER_MAP = {
    "actual": "actual - Current/measured value",
    "effective": "effective - Effective value",
    "min": "min - Minimum",
    "max": "max - Maximum",
    "nominal": "nominal - Nominal/design value",
    "alarm": "alarm - Alarm state",
    "enable": "enable - Enable state",
    "reset": "reset - Reset command",
    "manual": "manual - Manual mode",
    "auto": "auto - Auto mode",
}

QOS_MAP = {
    "0": "0 - At most once",
    "1": "1 - At least once (recommended)",
    "2": "2 - Exactly once",
}


def get_key_from_display(display_value: str, mapping: dict) -> str:
    """Get the key from a display value."""
    for key, value in mapping.items():
        if value == display_value:
            return key
    return ""


class PointsState(rx.State):
    """Points management state."""

    # Points list
    points: List[Dict[str, Any]] = []
    total_count: int = 0

    # Pagination
    page: int = 0
    page_size: int = 100

    # Filters
    filter_device_id: Optional[int] = None
    filter_device_name: str = "All Devices"
    filter_object_type: str = "All Types"
    filter_mqtt_status: str = "All"
    search_query: str = ""

    # Available filter options
    device_options: List[str] = ["All Devices"]
    object_type_options: List[str] = ["All Types"]

    # Bulk selection
    selected_point_ids: List[int] = []

    # Bulk configuration
    bulk_site_id: str = ""
    bulk_devices: List[Dict[str, Any]] = []
    bulk_save_message: str = ""

    # Selected point for editing
    selected_point_id: Optional[str] = None
    selected_point: Dict[str, Any] = {}

    # Haystack editor fields (stored values)
    edit_site_id: str = ""
    edit_equipment_type: str = ""
    edit_equipment_id: str = ""
    edit_point_function: str = ""
    edit_quantity: str = ""
    edit_subject: str = ""
    edit_location: str = ""
    edit_qualifier: str = ""
    edit_dis: str = ""

    # MQTT configuration fields
    edit_mqtt_publish: bool = False
    edit_is_writable: bool = False
    edit_min_value: str = ""
    edit_max_value: str = ""
    edit_poll_interval: str = "60"
    edit_qos: str = "1"

    # Modal state
    show_editor: bool = False

    # Loading
    is_loading: bool = False
    save_message: str = ""

    # Computed properties for dropdown display values
    @rx.var
    def edit_point_function_display(self) -> str:
        """Get display value for point function."""
        return POINT_FUNCTION_MAP.get(self.edit_point_function, "")

    @rx.var
    def edit_quantity_display(self) -> str:
        """Get display value for quantity."""
        return QUANTITY_MAP.get(self.edit_quantity, "")

    @rx.var
    def edit_subject_display(self) -> str:
        """Get display value for subject."""
        return SUBJECT_MAP.get(self.edit_subject, "-- Select --")

    @rx.var
    def edit_location_display(self) -> str:
        """Get display value for location."""
        return LOCATION_MAP.get(self.edit_location, "-- Select --")

    @rx.var
    def edit_qualifier_display(self) -> str:
        """Get display value for qualifier."""
        return QUALIFIER_MAP.get(self.edit_qualifier, "")

    @rx.var
    def edit_qos_display(self) -> str:
        """Get display value for QoS."""
        return QOS_MAP.get(self.edit_qos, "1 - At least once (recommended)")

    @rx.var
    def haystack_preview(self) -> str:
        """Generate preview of Haystack name."""
        if not self.edit_site_id:
            return "Complete tags to see preview"
        parts = [
            self.edit_site_id,
            self.edit_equipment_type or "_",
            self.edit_equipment_id or "_",
            self.edit_point_function or "_",
            self.edit_quantity or "_",
            self.edit_subject or "_",
            self.edit_location or "_",
            self.edit_qualifier or "_",
        ]
        return ".".join(parts)

    @rx.var
    def mqtt_topic_preview(self) -> str:
        """Generate preview of MQTT topic with objectInstance for uniqueness."""
        if not all([self.edit_site_id, self.edit_point_function, self.edit_quantity]):
            return ""
        parts = [self.edit_site_id]
        if self.edit_equipment_type:
            parts.append(self.edit_equipment_type)
        if self.edit_equipment_id:
            parts.append(self.edit_equipment_id)
        if self.edit_point_function:
            parts.append(self.edit_point_function)
        if self.edit_quantity:
            parts.append(self.edit_quantity)
        if self.edit_subject:
            parts.append(self.edit_subject)
        if self.edit_location:
            parts.append(self.edit_location)
        if self.edit_qualifier:
            parts.append(self.edit_qualifier)
        # Add objectInstance for unique identification
        obj_instance = self.selected_point.get("objectInstance", "")
        if obj_instance:
            parts.append(str(obj_instance))
        return "/".join(parts)

    @rx.var
    def selected_count(self) -> int:
        """Count of selected points."""
        return len(self.selected_point_ids)

    @rx.var
    def filter_mqtt_only(self) -> bool:
        """Check if MQTT only filter is active."""
        return self.filter_mqtt_status == "MQTT Enabled"

    @rx.var
    def total_pages(self) -> int:
        """Calculate total pages."""
        if self.total_count == 0:
            return 1
        return (self.total_count + self.page_size - 1) // self.page_size

    @rx.var
    def has_next_page(self) -> bool:
        """Check if there is a next page."""
        return (self.page + 1) < self.total_pages

    @rx.var
    def has_prev_page(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 0

    @rx.var
    def page_display(self) -> str:
        """Display current page info."""
        if self.total_count == 0:
            return "No points"
        start = self.page * self.page_size + 1
        end = min((self.page + 1) * self.page_size, self.total_count)
        return f"{start}-{end} of {self.total_count}"

    # Setters for dropdown display values
    def set_point_function_from_display(self, display: str):
        """Set point function from display value."""
        self.edit_point_function = get_key_from_display(display, POINT_FUNCTION_MAP)

    def set_quantity_from_display(self, display: str):
        """Set quantity from display value."""
        self.edit_quantity = get_key_from_display(display, QUANTITY_MAP)

    def set_subject_from_display(self, display: str):
        """Set subject from display value."""
        self.edit_subject = get_key_from_display(display, SUBJECT_MAP)

    def set_location_from_display(self, display: str):
        """Set location from display value."""
        self.edit_location = get_key_from_display(display, LOCATION_MAP)

    def set_qualifier_from_display(self, display: str):
        """Set qualifier from display value."""
        self.edit_qualifier = get_key_from_display(display, QUALIFIER_MAP)

    def set_qos_from_display(self, display: str):
        """Set QoS from display value."""
        self.edit_qos = get_key_from_display(display, QOS_MAP)

    # Basic setters
    def set_edit_site_id(self, value: str):
        self.edit_site_id = value

    def set_edit_equipment_type(self, value: str):
        self.edit_equipment_type = value

    def set_edit_equipment_id(self, value: str):
        self.edit_equipment_id = value

    def set_edit_point_function(self, value: str):
        self.edit_point_function = value

    def set_edit_quantity(self, value: str):
        self.edit_quantity = value

    def set_edit_subject(self, value: str):
        self.edit_subject = value

    def set_edit_location(self, value: str):
        self.edit_location = value

    def set_edit_qualifier(self, value: str):
        self.edit_qualifier = value

    def set_edit_dis(self, value: str):
        self.edit_dis = value

    def set_edit_mqtt_publish(self, value: bool):
        self.edit_mqtt_publish = value

    def set_edit_is_writable(self, value: bool):
        self.edit_is_writable = value

    def set_edit_min_value(self, value: str):
        self.edit_min_value = value

    def set_edit_max_value(self, value: str):
        self.edit_max_value = value

    def set_edit_poll_interval(self, value: str):
        self.edit_poll_interval = value

    def set_bulk_site_id(self, value: str):
        self.bulk_site_id = value

    def _load_points_sync(self) -> Dict[str, Any]:
        """Synchronous database operations run in thread pool."""
        result = {
            "points": [],
            "total_count": 0,
            "device_options": ["All Devices"],
            "object_type_options": ["All Types"],
            "bulk_devices": [],
        }

        with rx.session() as session:
            # Build base query with JOIN to get device info (eliminates N+1)
            query = (
                select(Point, Device)
                .join(Device, Point.deviceId == Device.id)
            )

            # Apply filters
            if self.filter_device_name != "All Devices":
                query = query.where(Device.deviceName == self.filter_device_name)

            if self.filter_object_type != "All Types":
                query = query.where(Point.objectType == self.filter_object_type)

            if self.filter_mqtt_status == "MQTT Enabled":
                query = query.where(Point.mqttPublish == True)
            elif self.filter_mqtt_status == "MQTT Disabled":
                query = query.where(Point.mqttPublish == False)

            if self.search_query:
                search = f"%{self.search_query}%"
                query = query.where(
                    (Point.pointName.ilike(search)) |
                    (Point.haystackPointName.ilike(search)) |
                    (Point.dis.ilike(search))
                )

            # Get total count for pagination
            count_query = select(func.count()).select_from(
                query.order_by(None).subquery()
            )
            result["total_count"] = session.exec(count_query).one()

            # Apply ordering and pagination
            query = query.order_by(Point.pointName)
            query = query.offset(self.page * self.page_size).limit(self.page_size)

            results = session.exec(query).all()

            # Build points list (device info already joined)
            for point, device in results:
                result["points"].append({
                    "id": point.id,
                    "bacnetName": point.bacnetName or point.pointName,
                    "pointName": point.pointName,
                    "objectType": point.objectType,
                    "objectInstance": point.objectInstance,
                    "description": point.description,
                    "units": point.units or "",
                    "haystackPointName": point.haystackPointName or "",
                    "dis": point.dis or "",
                    "mqttPublish": point.mqttPublish,
                    "mqttTopic": point.mqttTopic or "",
                    "pollInterval": point.pollInterval,
                    "qos": point.qos,
                    "lastValue": point.lastValue or "",
                    "lastPollTime": point.lastPollTime.isoformat() if point.lastPollTime else None,
                    "deviceId": point.deviceId,
                    "deviceName": device.deviceName,
                    "deviceBacnetId": device.deviceId,
                    "siteId": point.siteId or "",
                    "equipmentType": point.equipmentType or "",
                    "equipmentId": point.equipmentId or "",
                    "pointFunction": point.pointFunction or "",
                    "quantity": point.quantity or "",
                    "subject": point.subject or "",
                    "location": point.location or "",
                    "qualifier": point.qualifier or "",
                    "isWritable": point.isWritable,
                    "minPresValue": str(point.minPresValue) if point.minPresValue is not None else "",
                    "maxPresValue": str(point.maxPresValue) if point.maxPresValue is not None else "",
                })

            # Load filter options
            all_devices = session.exec(select(Device).order_by(Device.deviceName)).all()
            result["device_options"] = ["All Devices"] + [d.deviceName for d in all_devices]

            all_types = session.exec(select(Point.objectType).distinct()).all()
            result["object_type_options"] = ["All Types"] + sorted([t for t in all_types if t])

            # Load bulk device info with point counts using aggregate query
            device_counts = session.exec(
                select(Device.id, func.count(Point.id).label("point_count"))
                .outerjoin(Point, Device.id == Point.deviceId)
                .group_by(Device.id)
            ).all()
            count_map = {row[0]: row[1] for row in device_counts}

            for device in all_devices:
                result["bulk_devices"].append({
                    "id": device.id,
                    "deviceId": device.deviceId,
                    "deviceName": device.deviceName,
                    "ipAddress": device.ipAddress,
                    "pointCount": count_map.get(device.id, 0),
                    "equipmentType": "",
                    "equipmentId": "",
                })

        return result

    @rx.event(background=True)
    async def load_points(self):
        """Load points from database with filters (non-blocking)."""
        async with self:
            self.is_loading = True

        # Run blocking DB operations in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._load_points_sync)

        async with self:
            self.points = result["points"]
            self.total_count = result["total_count"]
            self.device_options = result["device_options"]
            self.object_type_options = result["object_type_options"]
            self.bulk_devices = result["bulk_devices"]
            self.is_loading = False

    # Pagination methods
    @rx.event(background=True)
    async def next_page(self):
        """Go to next page."""
        async with self:
            if (self.page + 1) * self.page_size < self.total_count:
                self.page += 1

        # Reload points with new page
        await self._reload_points()

    @rx.event(background=True)
    async def prev_page(self):
        """Go to previous page."""
        async with self:
            if self.page > 0:
                self.page -= 1

        # Reload points with new page
        await self._reload_points()

    @rx.event(background=True)
    async def first_page(self):
        """Go to first page."""
        async with self:
            self.page = 0

        await self._reload_points()

    async def _reload_points(self):
        """Helper to reload points after page/filter change."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._load_points_sync)

        async with self:
            self.points = result["points"]
            self.total_count = result["total_count"]
            self.is_loading = False

    # Filter setters - auto-apply filters
    @rx.event(background=True)
    async def set_filter_device(self, device_name: str):
        """Set device filter and reload points."""
        async with self:
            self.filter_device_name = device_name
            self.page = 0  # Reset to first page on filter change

        await self._reload_points()

    @rx.event(background=True)
    async def set_filter_object_type(self, object_type: str):
        """Set object type filter and reload points."""
        async with self:
            self.filter_object_type = object_type
            self.page = 0

        await self._reload_points()

    @rx.event(background=True)
    async def set_filter_mqtt_status(self, status: str):
        """Set MQTT status filter and reload points."""
        async with self:
            self.filter_mqtt_status = status
            self.page = 0

        await self._reload_points()

    @rx.event(background=True)
    async def set_search_query(self, query: str):
        """Set search query and reload points."""
        async with self:
            self.search_query = query
            self.page = 0

        await self._reload_points()

    @rx.event(background=True)
    async def clear_filters(self):
        """Clear all filters and reload points."""
        async with self:
            self.filter_device_name = "All Devices"
            self.filter_object_type = "All Types"
            self.filter_mqtt_status = "All"
            self.search_query = ""
            self.page = 0

        await self._reload_points()

    # Selection methods
    def toggle_point_selection(self, point_id: str, checked: bool):
        """Toggle selection of a single point."""
        pid = int(point_id) if point_id else 0
        if checked:
            if pid not in self.selected_point_ids:
                self.selected_point_ids = self.selected_point_ids + [pid]
        else:
            self.selected_point_ids = [p for p in self.selected_point_ids if p != pid]

    def select_all_points(self):
        """Select all visible points."""
        self.selected_point_ids = [p["id"] for p in self.points]

    def clear_selection(self):
        """Clear all selections."""
        self.selected_point_ids = []

    def toggle_select_all(self, checked: bool):
        """Toggle select all based on checkbox state."""
        if checked:
            self.select_all_points()
        else:
            self.clear_selection()

    # Point editor methods
    def open_editor(self, point_id: str):
        """Open point editor modal."""
        pid = int(point_id) if point_id else 0
        for point in self.points:
            if point["id"] == pid:
                self.selected_point_id = point_id
                self.selected_point = point

                # Load all fields into editor
                self.edit_site_id = point.get("siteId") or ""
                self.edit_equipment_type = point.get("equipmentType") or ""
                self.edit_equipment_id = point.get("equipmentId") or ""
                self.edit_point_function = point.get("pointFunction") or ""
                self.edit_quantity = point.get("quantity") or ""
                self.edit_subject = point.get("subject") or ""
                self.edit_location = point.get("location") or ""
                self.edit_qualifier = point.get("qualifier") or ""
                self.edit_dis = point.get("dis") or ""
                self.edit_mqtt_publish = point.get("mqttPublish", False)
                self.edit_is_writable = point.get("isWritable", False)
                self.edit_min_value = point.get("minPresValue") or ""
                self.edit_max_value = point.get("maxPresValue") or ""
                self.edit_poll_interval = str(point.get("pollInterval", 60))
                self.edit_qos = str(point.get("qos", 1))

                self.show_editor = True
                self.save_message = ""
                break

    def close_editor(self):
        """Close point editor modal."""
        self.show_editor = False
        self.selected_point_id = None
        self.selected_point = {}
        self.save_message = ""

    def _save_point_sync(self) -> str:
        """Synchronous save point operation."""
        if not self.selected_point_id:
            return "No point selected"

        with rx.session() as session:
            pid = int(self.selected_point_id) if self.selected_point_id else 0
            point = session.get(Point, pid)
            if not point:
                return "Point not found"

            # Update Haystack fields
            point.siteId = self.edit_site_id or None
            point.equipmentType = self.edit_equipment_type or None
            point.equipmentId = self.edit_equipment_id or None
            point.pointFunction = self.edit_point_function or None
            point.quantity = self.edit_quantity or None
            point.subject = self.edit_subject or None
            point.location = self.edit_location or None
            point.qualifier = self.edit_qualifier or None
            point.dis = self.edit_dis or None

            # Update MQTT configuration
            point.mqttPublish = self.edit_mqtt_publish
            point.isWritable = self.edit_is_writable
            point.pollInterval = int(self.edit_poll_interval) if self.edit_poll_interval else 60
            point.qos = int(self.edit_qos) if self.edit_qos else 1

            # Update write validation
            point.minPresValue = float(self.edit_min_value) if self.edit_min_value else None
            point.maxPresValue = float(self.edit_max_value) if self.edit_max_value else None

            # Generate Haystack name and MQTT topic
            point.haystackPointName = point.generate_haystack_name()
            point.mqttTopic = point.generate_mqtt_topic()

            point.updatedAt = datetime.now()
            session.add(point)
            session.commit()

        return "Saved successfully"

    @rx.event(background=True)
    async def save_point(self):
        """Save point configuration."""
        if not self.selected_point_id:
            return

        async with self:
            self.save_message = ""

        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(None, self._save_point_sync)

        async with self:
            self.save_message = message

        # Reload points
        await self._reload_points()

        async with self:
            self.close_editor()

    # Bulk operations
    def _toggle_mqtt_sync(self, point_id: int, enabled: bool):
        """Synchronous toggle MQTT operation."""
        with rx.session() as session:
            point = session.get(Point, point_id)
            if point:
                point.mqttPublish = enabled
                point.updatedAt = datetime.now()
                session.add(point)
                session.commit()

    @rx.event(background=True)
    async def toggle_mqtt_publish(self, point_id: str, enabled: bool):
        """Toggle MQTT publish for a single point."""
        pid = int(point_id) if point_id else 0

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._toggle_mqtt_sync, pid, enabled)

        await self._reload_points()

    def _bulk_enable_mqtt_sync(self, point_ids: List[int]):
        """Synchronous bulk enable MQTT operation."""
        with rx.session() as session:
            for point_id in point_ids:
                point = session.get(Point, point_id)
                if point:
                    point.mqttPublish = True
                    point.updatedAt = datetime.now()
                    session.add(point)
            session.commit()

    @rx.event(background=True)
    async def bulk_enable_mqtt(self):
        """Enable MQTT publish for selected points."""
        async with self:
            if not self.selected_point_ids:
                return
            point_ids = list(self.selected_point_ids)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._bulk_enable_mqtt_sync, point_ids)

        async with self:
            self.selected_point_ids = []

        await self._reload_points()

    def _bulk_disable_mqtt_sync(self, point_ids: List[int]):
        """Synchronous bulk disable MQTT operation."""
        with rx.session() as session:
            for point_id in point_ids:
                point = session.get(Point, point_id)
                if point:
                    point.mqttPublish = False
                    point.updatedAt = datetime.now()
                    session.add(point)
            session.commit()

    @rx.event(background=True)
    async def bulk_disable_mqtt(self):
        """Disable MQTT publish for selected points."""
        async with self:
            if not self.selected_point_ids:
                return
            point_ids = list(self.selected_point_ids)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._bulk_disable_mqtt_sync, point_ids)

        async with self:
            self.selected_point_ids = []

        await self._reload_points()

    def _apply_bulk_config_sync(self, bulk_site_id: str, bulk_devices: List[Dict]) -> str:
        """Synchronous bulk config operation - optimized with batch update."""
        if not bulk_site_id:
            return "Site ID is required"

        # Build device config lookup
        device_config = {dev["id"]: dev for dev in bulk_devices}

        with rx.session() as session:
            # Get all points in a single query
            points = session.exec(select(Point)).all()

            for point in points:
                point.siteId = bulk_site_id

                # Apply device-specific equipment mapping
                dev_conf = device_config.get(point.deviceId)
                if dev_conf:
                    if dev_conf.get("equipmentType"):
                        point.equipmentType = dev_conf["equipmentType"]
                    if dev_conf.get("equipmentId"):
                        point.equipmentId = dev_conf["equipmentId"]

                # Regenerate Haystack name and topic
                point.haystackPointName = point.generate_haystack_name()
                point.mqttTopic = point.generate_mqtt_topic()
                point.updatedAt = datetime.now()
                session.add(point)

            session.commit()

        return f"Configuration applied to {len(points)} points"

    @rx.event(background=True)
    async def apply_bulk_config(self):
        """Apply bulk configuration to all points."""
        async with self:
            if not self.bulk_site_id:
                self.bulk_save_message = "Site ID is required"
                return
            bulk_site_id = self.bulk_site_id
            bulk_devices = list(self.bulk_devices)
            self.bulk_save_message = ""

        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(
            None, self._apply_bulk_config_sync, bulk_site_id, bulk_devices
        )

        async with self:
            self.bulk_save_message = message

        await self._reload_points()

    def set_device_equipment_type(self, device_id: str, equipment_type: str):
        """Set equipment type for a device in bulk config."""
        # Convert device_id to int for comparison
        dev_id = int(device_id) if device_id else 0
        # Create a new list to trigger reactivity
        new_devices = []
        for dev in self.bulk_devices:
            if dev["id"] == dev_id:
                new_dev = dict(dev)
                new_dev["equipmentType"] = equipment_type
                new_devices.append(new_dev)
            else:
                new_devices.append(dev)
        self.bulk_devices = new_devices

    def set_device_custom_equipment_type(self, device_id: str, custom_type: str):
        """Set custom equipment type for a device when 'other' is selected."""
        # Convert device_id to int for comparison
        dev_id = int(device_id) if device_id else 0
        # Create a new list to trigger reactivity
        new_devices = []
        for dev in self.bulk_devices:
            if dev["id"] == dev_id:
                new_dev = dict(dev)
                new_dev["equipmentType"] = custom_type
                new_devices.append(new_dev)
            else:
                new_devices.append(dev)
        self.bulk_devices = new_devices

    def set_device_equipment_id(self, device_id: str, equipment_id: str):
        """Set equipment ID for a device in bulk config."""
        # Convert device_id to int for comparison
        dev_id = int(device_id) if device_id else 0
        # Create a new list to trigger reactivity
        new_devices = []
        for dev in self.bulk_devices:
            if dev["id"] == dev_id:
                new_dev = dict(dev)
                new_dev["equipmentId"] = equipment_id
                new_devices.append(new_dev)
            else:
                new_devices.append(dev)
        self.bulk_devices = new_devices

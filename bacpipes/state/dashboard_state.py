"""Dashboard state for BacPipes."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any
import reflex as rx
from sqlmodel import select, func

from ..models.device import Device
from ..models.point import Point
from ..models.mqtt_config import MqttConfig
from ..models.system_settings import SystemSettings


class DashboardState(rx.State):
    """Dashboard state management."""

    # Statistics
    total_devices: int = 0
    total_points: int = 0
    enabled_points: int = 0
    publishing_points: int = 0

    # Status
    mqtt_status: str = "disconnected"
    mqtt_broker: str = ""
    bacnet_ip: str = ""
    last_refresh: str = ""

    # Recent points with values
    recent_points: List[Dict[str, Any]] = []

    # Devices list
    devices: List[Dict[str, Any]] = []

    # Loading state
    is_loading: bool = False

    # Auto-refresh
    auto_refresh_enabled: bool = True

    def _load_dashboard_sync(self) -> Dict[str, Any]:
        """Synchronous database operations run in thread pool."""
        result = {
            "total_devices": 0,
            "total_points": 0,
            "enabled_points": 0,
            "publishing_points": 0,
            "mqtt_status": "disconnected",
            "mqtt_broker": "Not configured",
            "bacnet_ip": "Not configured",
            "devices": [],
            "recent_points": [],
        }

        with rx.session() as session:
            # Count devices
            result["total_devices"] = session.exec(
                select(func.count(Device.id))
            ).one()

            # Count points
            result["total_points"] = session.exec(
                select(func.count(Point.id))
            ).one()

            # Count enabled points
            result["enabled_points"] = session.exec(
                select(func.count(Point.id)).where(Point.enabled == True)
            ).one()

            # Count actually publishing points (device enabled AND point mqttPublish)
            result["publishing_points"] = session.exec(
                select(func.count(Point.id))
                .join(Device, Point.deviceId == Device.id)
                .where(Point.mqttPublish == True)
                .where(Point.enabled == True)
                .where(Device.enabled == True)
            ).one()

            # Get MQTT status
            mqtt_config = session.exec(select(MqttConfig)).first()
            if mqtt_config:
                result["mqtt_status"] = mqtt_config.connectionStatus or "disconnected"
                result["mqtt_broker"] = f"{mqtt_config.broker}:{mqtt_config.port}" if mqtt_config.broker else "Not configured"

            # Get BACnet IP
            settings = session.exec(select(SystemSettings)).first()
            if settings and settings.bacnetIp:
                result["bacnet_ip"] = settings.bacnetIp

            # Get devices with point counts using JOIN and GROUP BY (eliminates N+1)
            device_query = (
                select(
                    Device.id,
                    Device.deviceId,
                    Device.deviceName,
                    Device.ipAddress,
                    Device.enabled,
                    Device.lastSeenAt,
                    func.count(Point.id).label("point_count")
                )
                .outerjoin(Point, Device.id == Point.deviceId)
                .group_by(Device.id)
                .order_by(Device.deviceName)
            )
            devices_result = session.exec(device_query).all()

            result["devices"] = [
                {
                    "id": row[0],
                    "deviceId": row[1],
                    "deviceName": row[2],
                    "ipAddress": row[3],
                    "enabled": row[4],
                    "pointCount": row[6],
                    "lastSeenAt": row[5].isoformat() if row[5] else None,
                }
                for row in devices_result
            ]

            # Get recent points with values using JOIN (eliminates N+1)
            recent_query = (
                select(Point, Device)
                .join(Device, Point.deviceId == Device.id)
                .where(Point.lastPollTime.isnot(None))
                .order_by(Point.lastPollTime.desc())
                .limit(10)
            )
            recent_result = session.exec(recent_query).all()

            result["recent_points"] = [
                {
                    "id": point.id,
                    "pointName": point.pointName,
                    "haystackPointName": point.haystackPointName,
                    "dis": point.dis,
                    "lastValue": point.lastValue,
                    "units": point.units,
                    "lastPollTime": point.lastPollTime.isoformat() if point.lastPollTime else None,
                    "deviceName": device.deviceName if device else "Unknown",
                }
                for point, device in recent_result
            ]

        return result

    @rx.event(background=True)
    async def load_dashboard(self):
        """Load all dashboard data from database (non-blocking)."""
        async with self:
            self.is_loading = True

        # Run blocking DB operations in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._load_dashboard_sync)

        async with self:
            self.total_devices = result["total_devices"]
            self.total_points = result["total_points"]
            self.enabled_points = result["enabled_points"]
            self.publishing_points = result["publishing_points"]
            self.mqtt_status = result["mqtt_status"]
            self.mqtt_broker = result["mqtt_broker"]
            self.bacnet_ip = result["bacnet_ip"]
            self.devices = result["devices"]
            self.recent_points = result["recent_points"]
            self.last_refresh = datetime.now().strftime("%H:%M:%S")
            self.is_loading = False

        yield rx.toast.success("Dashboard refreshed")

    def toggle_auto_refresh(self, enabled: bool):
        """Toggle auto-refresh setting."""
        self.auto_refresh_enabled = enabled

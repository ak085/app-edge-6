"""Dashboard state for BacPipes."""

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

    async def load_dashboard(self):
        """Load all dashboard data from database."""
        self.is_loading = True
        yield

        with rx.session() as session:
            # Count devices
            self.total_devices = session.exec(
                select(func.count(Device.id))
            ).one()

            # Count points
            self.total_points = session.exec(
                select(func.count(Point.id))
            ).one()

            # Count enabled points
            self.enabled_points = session.exec(
                select(func.count(Point.id)).where(Point.enabled == True)
            ).one()

            # Count actually publishing points (device enabled AND point mqttPublish)
            self.publishing_points = session.exec(
                select(func.count(Point.id))
                .join(Device, Point.deviceId == Device.id)
                .where(Point.mqttPublish == True)
                .where(Point.enabled == True)
                .where(Device.enabled == True)
            ).one()

            # Get MQTT status
            mqtt_config = session.exec(select(MqttConfig)).first()
            if mqtt_config:
                self.mqtt_status = mqtt_config.connectionStatus or "disconnected"
                self.mqtt_broker = f"{mqtt_config.broker}:{mqtt_config.port}" if mqtt_config.broker else "Not configured"
            else:
                self.mqtt_status = "disconnected"
                self.mqtt_broker = "Not configured"

            # Get BACnet IP
            settings = session.exec(select(SystemSettings)).first()
            if settings and settings.bacnetIp:
                self.bacnet_ip = settings.bacnetIp
            else:
                self.bacnet_ip = "Not configured"

            # Get devices with point counts
            devices_result = session.exec(select(Device).order_by(Device.deviceName)).all()
            self.devices = []
            for device in devices_result:
                point_count = session.exec(
                    select(func.count(Point.id)).where(Point.deviceId == device.id)
                ).one()
                self.devices.append({
                    "id": device.id,
                    "deviceId": device.deviceId,
                    "deviceName": device.deviceName,
                    "ipAddress": device.ipAddress,
                    "enabled": device.enabled,
                    "pointCount": point_count,
                    "lastSeenAt": device.lastSeenAt.isoformat() if device.lastSeenAt else None,
                })

            # Get recent points with values (last 10 polled)
            recent_result = session.exec(
                select(Point)
                .where(Point.lastPollTime.isnot(None))
                .order_by(Point.lastPollTime.desc())
                .limit(10)
            ).all()

            self.recent_points = []
            for point in recent_result:
                # Get device info
                device = session.get(Device, point.deviceId)
                self.recent_points.append({
                    "id": point.id,
                    "pointName": point.pointName,
                    "haystackPointName": point.haystackPointName,
                    "dis": point.dis,
                    "lastValue": point.lastValue,
                    "units": point.units,
                    "lastPollTime": point.lastPollTime.isoformat() if point.lastPollTime else None,
                    "deviceName": device.deviceName if device else "Unknown",
                })

        self.last_refresh = datetime.now().strftime("%H:%M:%S")
        self.is_loading = False

    def toggle_auto_refresh(self, enabled: bool):
        """Toggle auto-refresh setting."""
        self.auto_refresh_enabled = enabled

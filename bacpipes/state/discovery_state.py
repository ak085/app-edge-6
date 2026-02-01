"""Discovery state for BacPipes."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import reflex as rx
from sqlmodel import select, func

from ..models.device import Device
from ..models.point import Point
from ..models.discovery_job import DiscoveryJob
from ..models.system_settings import SystemSettings


class DiscoveryState(rx.State):
    """BACnet discovery state management."""

    # Scan status
    is_scanning: bool = False
    scan_progress: str = ""
    current_job_id: Optional[str] = None

    # Results
    discovered_devices: List[Dict[str, Any]] = []
    last_scan_time: str = ""
    last_scan_result: str = ""

    # Job history
    recent_jobs: List[Dict[str, Any]] = []

    # Form state
    scan_ip: str = ""
    scan_timeout: int = 15

    # Loading state
    is_loading: bool = False

    def _load_discovery_data_sync(self) -> Dict[str, Any]:
        """Synchronous database operations run in thread pool."""
        result = {
            "scan_ip": "",
            "discovered_devices": [],
            "recent_jobs": [],
        }

        with rx.session() as session:
            # Get system settings for default IP
            settings = session.exec(select(SystemSettings)).first()
            if settings and settings.bacnetIp:
                result["scan_ip"] = settings.bacnetIp

            # Get devices with point counts using JOIN and GROUP BY (eliminates N+1)
            device_query = (
                select(
                    Device.id,
                    Device.deviceId,
                    Device.deviceName,
                    Device.ipAddress,
                    Device.vendorName,
                    Device.enabled,
                    Device.lastSeenAt,
                    func.count(Point.id).label("point_count")
                )
                .outerjoin(Point, Device.id == Point.deviceId)
                .group_by(Device.id)
                .order_by(Device.deviceName)
            )
            devices_result = session.exec(device_query).all()

            result["discovered_devices"] = [
                {
                    "id": row[0],
                    "deviceId": row[1],
                    "deviceName": row[2],
                    "ipAddress": row[3],
                    "vendorName": row[4],
                    "enabled": row[5],
                    "lastSeenAt": row[6].isoformat() if row[6] else None,
                    "pointCount": row[7],
                }
                for row in devices_result
            ]

            # Get recent jobs
            jobs = session.exec(
                select(DiscoveryJob)
                .order_by(DiscoveryJob.startedAt.desc())
                .limit(5)
            ).all()

            result["recent_jobs"] = [
                {
                    "id": job.id,
                    "status": job.status,
                    "ipAddress": job.ipAddress,
                    "devicesFound": job.devicesFound,
                    "pointsFound": job.pointsFound,
                    "startedAt": job.startedAt.isoformat() if job.startedAt else None,
                    "completedAt": job.completedAt.isoformat() if job.completedAt else None,
                    "errorMessage": job.errorMessage,
                }
                for job in jobs
            ]

        return result

    @rx.event(background=True)
    async def load_discovery_data(self):
        """Load discovery data from database (non-blocking)."""
        async with self:
            self.is_loading = True

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._load_discovery_data_sync)

        async with self:
            if result["scan_ip"] and not self.scan_ip:
                self.scan_ip = result["scan_ip"]
            self.discovered_devices = result["discovered_devices"]
            self.recent_jobs = result["recent_jobs"]
            self.is_loading = False

    async def start_discovery(self, form_data: dict):
        """Start a BACnet discovery scan."""
        if self.is_scanning:
            return

        ip_address = form_data.get("ip_address", self.scan_ip).strip()
        timeout = int(form_data.get("timeout", self.scan_timeout))

        if not ip_address:
            self.scan_progress = "Error: IP address is required"
            yield
            return

        self.is_scanning = True
        self.scan_progress = "Creating discovery job..."
        yield

        # Create discovery job in database
        with rx.session() as session:
            # Get device ID from settings
            settings = session.exec(select(SystemSettings)).first()
            device_id = settings.bacnetDeviceId if settings else 3001234

            job = DiscoveryJob(
                ipAddress=ip_address,
                port=47808,
                timeout=timeout,
                deviceId=device_id,
                status="running",
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            self.current_job_id = job.id

        self.scan_progress = f"Starting BACnet scan on {ip_address}..."
        yield

        # Run discovery in background
        try:
            # Import and run discovery
            from ..worker.discovery import run_discovery_async

            self.scan_progress = "Scanning for BACnet devices..."
            yield

            # Run the async discovery
            await run_discovery_async(self.current_job_id)

            # Reload data after discovery
            self.scan_progress = "Discovery complete! Reloading data..."
            yield

            # Use background reload
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._load_discovery_data_sync)
            self.discovered_devices = result["discovered_devices"]
            self.recent_jobs = result["recent_jobs"]

            # Get job result
            with rx.session() as session:
                job = session.get(DiscoveryJob, self.current_job_id)
                if job:
                    if job.status == "complete":
                        self.last_scan_result = f"Found {job.devicesFound} devices and {job.pointsFound} points"
                    else:
                        self.last_scan_result = f"Error: {job.errorMessage}"

        except Exception as e:
            self.scan_progress = f"Error: {str(e)}"
            self.last_scan_result = f"Discovery failed: {str(e)}"

            # Update job status
            with rx.session() as session:
                job = session.get(DiscoveryJob, self.current_job_id)
                if job:
                    job.status = "error"
                    job.errorMessage = str(e)
                    job.completedAt = datetime.now()
                    session.add(job)
                    session.commit()

        finally:
            self.is_scanning = False
            self.current_job_id = None
            self.last_scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.scan_progress = ""

    def cancel_discovery(self):
        """Cancel the current discovery scan."""
        if not self.is_scanning:
            return

        if self.current_job_id:
            with rx.session() as session:
                job = session.get(DiscoveryJob, self.current_job_id)
                if job:
                    job.status = "cancelled"
                    job.completedAt = datetime.now()
                    session.add(job)
                    session.commit()

        self.is_scanning = False
        self.current_job_id = None
        self.scan_progress = "Discovery cancelled"

    def _toggle_device_sync(self, device_id: int, enabled: bool):
        """Synchronous toggle device operation."""
        with rx.session() as session:
            device = session.get(Device, device_id)
            if device:
                device.enabled = enabled
                device.lastSeenAt = datetime.now()
                session.add(device)
                session.commit()

    @rx.event(background=True)
    async def toggle_device_enabled(self, device_id: str, enabled: bool):
        """Toggle device enabled status (non-blocking)."""
        dev_id = int(device_id) if device_id else 0

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._toggle_device_sync, dev_id, enabled)

        # Reload data
        result = await loop.run_in_executor(None, self._load_discovery_data_sync)

        async with self:
            self.discovered_devices = result["discovered_devices"]

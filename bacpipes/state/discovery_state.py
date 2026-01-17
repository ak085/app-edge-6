"""Discovery state for BacPipes."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import reflex as rx
from sqlmodel import select

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

    async def load_discovery_data(self):
        """Load discovery data from database."""
        with rx.session() as session:
            # Get system settings for default IP
            settings = session.exec(select(SystemSettings)).first()
            if settings and settings.bacnetIp:
                self.scan_ip = settings.bacnetIp

            # Get discovered devices
            devices = session.exec(
                select(Device).order_by(Device.deviceName)
            ).all()

            self.discovered_devices = []
            for device in devices:
                point_count = session.exec(
                    select(Point).where(Point.deviceId == device.id)
                ).all()
                self.discovered_devices.append({
                    "id": device.id,
                    "deviceId": device.deviceId,
                    "deviceName": device.deviceName,
                    "ipAddress": device.ipAddress,
                    "vendorName": device.vendorName,
                    "enabled": device.enabled,
                    "pointCount": len(point_count),
                    "lastSeenAt": device.lastSeenAt.isoformat() if device.lastSeenAt else None,
                })

            # Get recent jobs
            jobs = session.exec(
                select(DiscoveryJob)
                .order_by(DiscoveryJob.startedAt.desc())
                .limit(5)
            ).all()

            self.recent_jobs = []
            for job in jobs:
                self.recent_jobs.append({
                    "id": job.id,
                    "status": job.status,
                    "ipAddress": job.ipAddress,
                    "devicesFound": job.devicesFound,
                    "pointsFound": job.pointsFound,
                    "startedAt": job.startedAt.isoformat() if job.startedAt else None,
                    "completedAt": job.completedAt.isoformat() if job.completedAt else None,
                    "errorMessage": job.errorMessage,
                })

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

            await self.load_discovery_data()

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

    async def toggle_device_enabled(self, device_id: str, enabled: bool):
        """Toggle device enabled status.

        When using handler(bound_arg) pattern in Reflex with rx.foreach,
        the bound argument comes FIRST, then the event value.
        """
        dev_id = int(device_id) if device_id else 0
        with rx.session() as session:
            device = session.get(Device, dev_id)
            if device:
                device.enabled = enabled
                device.lastSeenAt = datetime.now()
                session.add(device)
                session.commit()

        await self.load_discovery_data()

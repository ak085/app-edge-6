"""BACnet discovery module for BacPipes."""

import asyncio
import os
import time
import socket
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from sqlmodel import Session, select, create_engine

from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.basetypes import PropertyIdentifier
from bacpypes3.apdu import ErrorRejectAbortNack, WhoIsRequest, IAmRequest
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.local.device import DeviceObject

from ..models.device import Device
from ..models.point import Point
from ..models.discovery_job import DiscoveryJob

logger = logging.getLogger(__name__)

# Lock file for coordination with polling worker
DISCOVERY_LOCK_FILE = Path("/tmp/bacnet_discovery_active")


class DiscoveryApp(NormalApplication):
    """BACpypes3 application for BACnet device discovery."""

    def __init__(self, local_address: Address, device_id: int = 3001234, timeout: int = 15):
        # Create device object
        device = DeviceObject(
            objectIdentifier=ObjectIdentifier(f"device,{device_id}"),
            objectName="BacPipes Discovery",
            vendorIdentifier=999,
            maxApduLengthAccepted=1024,
            segmentationSupported="segmentedBoth",
        )

        super().__init__(device, local_address)

        self.timeout = timeout
        self.found_devices: List[Tuple[str, int]] = []
        self.all_points: List[Dict] = []

    async def do_IAmRequest(self, apdu: IAmRequest) -> None:
        """Handle I-Am responses from devices."""
        device_id = apdu.iAmDeviceIdentifier[1]
        device_address = str(apdu.pduSource)

        logger.info(f"Found device {device_id} at {device_address}")
        self.found_devices.append((device_address, device_id))

        # Read device objects
        await self.read_device_objects(device_address, device_id)

    async def read_property_value(self, address: str, object_id: ObjectIdentifier, property_name: str):
        """Read a single property from a BACnet object."""
        try:
            value = await self.read_property(
                Address(address),
                object_id,
                PropertyIdentifier(property_name)
            )
            return value
        except ErrorRejectAbortNack as e:
            logger.debug(f"Error reading {property_name} from {object_id}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Exception reading {property_name} from {object_id}: {e}")
            return None

    async def read_device_objects(self, device_address: str, device_id: int):
        """Read all objects from a device."""
        try:
            # Read device name
            device_obj_id = ObjectIdentifier(f"device,{device_id}")
            device_name = await self.read_property_value(device_address, device_obj_id, "objectName")
            if device_name is None:
                device_name = f"Device_{device_id}"
            else:
                device_name = str(device_name)

            # Read object list
            object_list = await self.read_property_value(device_address, device_obj_id, "objectList")
            if not object_list:
                logger.warning(f"Could not read object list from device {device_id}")
                return

            logger.info(f"Device '{device_name}' has {len(object_list)} objects")

            # Read properties for each object
            for obj_id in object_list:
                obj_type = str(obj_id[0])
                if obj_type in ("device", "network-port"):
                    continue  # Skip device and network-port objects

                await self.read_object_properties(device_address, device_id, device_name, obj_id)

        except Exception as e:
            logger.error(f"Error reading device {device_id}: {e}")

    async def read_object_properties(self, device_address: str, device_id: int, device_name: str, obj_id):
        """Read properties from a single object."""
        try:
            object_type = str(obj_id[0])
            object_instance = obj_id[1]

            obj_identifier = ObjectIdentifier(f"{object_type},{object_instance}")

            point_data = {
                'device_id': device_id,
                'device_name': device_name,
                'device_ip': device_address.split(':')[0] if ':' in device_address else device_address,
                'object_type': object_type,
                'object_instance': object_instance,
            }

            # Read properties
            properties = [
                "objectName", "description", "presentValue", "units",
                "priorityArray", "minPresValue", "maxPresValue"
            ]

            for prop in properties:
                value = await self.read_property_value(device_address, obj_identifier, prop)
                if value is not None:
                    point_data[prop] = str(value)

            self.all_points.append(point_data)

        except Exception as e:
            logger.error(f"Error reading object {obj_id}: {e}")


def is_port_in_use(port: int) -> bool:
    """Check if a UDP port is in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', port))
            return False
    except OSError:
        return True


async def run_discovery_async(job_id: str):
    """Run BACnet discovery asynchronously."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://bacpipes@localhost:5432/bacpipes"
    )
    engine = create_engine(db_url)

    # Load job from database
    with Session(engine) as session:
        job = session.get(DiscoveryJob, job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        ip_address = job.ipAddress
        port = job.port
        timeout = job.timeout
        device_id = job.deviceId

    logger.info(f"=== Discovery Started ===")
    logger.info(f"IP: {ip_address}, Port: {port}, Timeout: {timeout}s")

    try:
        # Create lock file to signal worker to pause
        DISCOVERY_LOCK_FILE.touch()
        logger.info("Discovery lock created")

        # Wait for port to be released
        max_wait = 20
        for i in range(max_wait):
            if not is_port_in_use(port):
                logger.info(f"Port {port} available after {i}s")
                break
            await asyncio.sleep(1)
        else:
            raise Exception(f"Port {port} not released in {max_wait}s")

        # Create discovery application
        local_addr = Address(f"{ip_address}/24:{port}")
        app = DiscoveryApp(local_addr, device_id, timeout)

        logger.info(f"Starting discovery on {local_addr}")

        # Calculate broadcast address
        ip_parts = ip_address.split('.')
        broadcast_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"

        # Send Who-Is
        who_is = WhoIsRequest(destination=Address(f"{broadcast_ip}/24"))
        await app.request(who_is)

        # Wait for responses
        logger.info(f"Waiting {timeout}s for responses...")
        await asyncio.sleep(timeout)

        logger.info(f"=== Discovery Complete ===")
        logger.info(f"Found {len(app.found_devices)} devices, {len(app.all_points)} points")

        # Save to database
        await save_results(engine, job_id, app.found_devices, app.all_points)

        app.close()

    except Exception as e:
        logger.error(f"Discovery error: {e}")

        # Update job as error
        with Session(engine) as session:
            job = session.get(DiscoveryJob, job_id)
            if job:
                job.status = "error"
                job.errorMessage = str(e)
                job.completedAt = datetime.now()
                session.add(job)
                session.commit()

    finally:
        # Remove lock file
        if DISCOVERY_LOCK_FILE.exists():
            DISCOVERY_LOCK_FILE.unlink()
            logger.info("Discovery lock removed")


async def save_results(engine, job_id: str, devices: List[Tuple[str, int]], points: List[Dict]):
    """Save discovery results to database."""
    with Session(engine) as session:
        devices_saved = 0
        points_saved = 0

        # Clear ALL existing devices before saving new results
        # (cascade_delete=True on Device.points will delete associated Points and WriteHistory)
        logger.info("Clearing all existing devices and points before saving new discovery data")
        all_devices = session.exec(select(Device)).all()
        for device in all_devices:
            session.delete(device)
        session.commit()
        logger.info(f"Deleted {len(all_devices)} existing devices")

        # Group points by device
        device_points = {}
        for point in points:
            dev_id = point['device_id']
            if dev_id not in device_points:
                device_points[dev_id] = []
            device_points[dev_id].append(point)

        # Save devices and points
        for device_address, device_id in devices:
            device_name = next(
                (p['device_name'] for p in points if p['device_id'] == device_id),
                f"Device_{device_id}"
            )

            ip = device_address.split(':')[0] if ':' in device_address else device_address

            # Check if device exists
            existing_device = session.exec(
                select(Device).where(Device.deviceId == device_id)
            ).first()

            if existing_device:
                existing_device.deviceName = device_name
                existing_device.ipAddress = ip
                existing_device.lastSeenAt = datetime.now()
                session.add(existing_device)
                db_device_id = existing_device.id
            else:
                new_device = Device(
                    deviceId=device_id,
                    deviceName=device_name,
                    ipAddress=ip,
                    port=47808,
                    enabled=True,
                )
                session.add(new_device)
                session.commit()
                session.refresh(new_device)
                db_device_id = new_device.id

            devices_saved += 1

            # Save points for this device
            if device_id in device_points:
                for point_data in device_points[device_id]:
                    # Check if point exists
                    existing_point = session.exec(
                        select(Point).where(
                            Point.deviceId == db_device_id,
                            Point.objectType == point_data.get('object_type', ''),
                            Point.objectInstance == point_data.get('object_instance', 0),
                        )
                    ).first()

                    if existing_point:
                        object_name = point_data.get('objectName', 'Unknown')
                        # Set bacnetName if not already set (first discovery after field was added)
                        if not existing_point.bacnetName:
                            existing_point.bacnetName = object_name
                        # Always update pointName to current BACnet name
                        existing_point.pointName = object_name
                        existing_point.description = point_data.get('description')
                        existing_point.units = point_data.get('units')
                        existing_point.lastValue = point_data.get('presentValue')
                        existing_point.lastPollTime = datetime.now()
                        existing_point.updatedAt = datetime.now()
                        session.add(existing_point)
                    else:
                        object_name = point_data.get('objectName', 'Unknown')
                        new_point = Point(
                            deviceId=db_device_id,
                            objectType=point_data.get('object_type', ''),
                            objectInstance=point_data.get('object_instance', 0),
                            bacnetName=object_name,  # Set original (immutable)
                            pointName=object_name,   # Set current
                            description=point_data.get('description'),
                            units=point_data.get('units'),
                            enabled=True,
                            isWritable='priorityArray' in point_data,
                            lastValue=point_data.get('presentValue'),
                            lastPollTime=datetime.now(),
                        )
                        session.add(new_point)

                    points_saved += 1

        session.commit()

        # Update job
        job = session.get(DiscoveryJob, job_id)
        if job:
            job.status = "complete"
            job.devicesFound = devices_saved
            job.pointsFound = points_saved
            job.completedAt = datetime.now()
            session.add(job)
            session.commit()

        logger.info(f"Saved {devices_saved} devices and {points_saved} points")

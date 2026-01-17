"""
BACnet Discovery Module for BacPipes Worker

Discovers BACnet devices and points on the network, saves results to PostgreSQL database.
Based on scripts/01_discovery_production.py but database-driven.
"""

import asyncio
import sys
import socket
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.basetypes import PropertyIdentifier, ReadAccessSpecification, PropertyReference
from bacpypes3.apdu import ErrorRejectAbortNack, WhoIsRequest, IAmRequest, ReadPropertyRequest, ReadPropertyMultipleRequest
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.local.device import DeviceObject


class DiscoveryApp(NormalApplication):
    """BACpypes3 application for BACnet device discovery"""

    def __init__(self, local_address: Address, device_id: int = 3001234, timeout: int = 15):
        # Create device object
        device = DeviceObject(
            objectIdentifier=ObjectIdentifier(f"device,{device_id}"),
            objectName="BacPipes Discovery",
            vendorIdentifier=999,
            maxApduLengthAccepted=1024,
            segmentationSupported="segmentedBoth",
        )

        # Initialize application
        super().__init__(device, local_address)

        self.timeout = timeout
        self.found_devices: List[Tuple[str, int]] = []
        self.all_points: List[Dict] = []

    async def do_IAmRequest(self, apdu: IAmRequest) -> None:
        """Handle I-Am responses from devices"""
        device_id = apdu.iAmDeviceIdentifier[1]
        device_address = str(apdu.pduSource)

        print(f"  Found device {device_id} at {device_address}")
        self.found_devices.append((device_address, device_id))

        # Start reading device properties
        await self.read_device_objects(device_address, device_id)

    async def read_property_value(self, address: str, object_id: ObjectIdentifier, property_name: str):
        """Read a single property from a BACnet object using the built-in read_property method"""
        try:
            # Use NormalApplication's built-in read_property - it handles decoding automatically
            value = await self.read_property(
                Address(address),
                object_id,
                PropertyIdentifier(property_name)
            )
            return value
        except ErrorRejectAbortNack as e:
            print(f"      Error reading {property_name} from {object_id}: {e}")
            return None
        except Exception as e:
            print(f"      Exception reading {property_name} from {object_id}: {e}")
            return None

    async def read_device_objects(self, device_address: str, device_id: int):
        """Read all objects from a device and collect properties"""
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
                print(f"    Warning: Could not read object list from device {device_id}")
                return

            print(f"    Device '{device_name}' has {len(object_list)} objects")

            # Read properties for each object
            for obj_id in object_list:
                # obj_id is a tuple like (ObjectType, instance_number)
                if str(obj_id[0]) == "device":
                    continue  # Skip device object itself

                await self.read_object_properties(device_address, device_id, device_name, obj_id)

        except Exception as e:
            print(f"    Error reading device {device_id}: {e}")

    async def read_object_properties(self, device_address: str, device_id: int, device_name: str, obj_id):
        """Read all properties from a single object"""
        try:
            # obj_id is a tuple: (ObjectType, instance_number)
            object_type = str(obj_id[0])  # Convert ObjectType enum to string
            object_instance = obj_id[1]

            # Create ObjectIdentifier for property reads
            obj_identifier = ObjectIdentifier(f"{object_type},{object_instance}")

            # Read common properties
            point_data = {
                'device_id': device_id,
                'device_name': device_name,
                'device_ip': device_address.split(':')[0] if ':' in device_address else device_address,
                'object_type': object_type,
                'object_instance': object_instance,
            }

            # Property list to read
            properties = [
                "objectName", "description", "presentValue", "units",
                "statusFlags", "reliability", "outOfService", "eventState",
                "priorityArray", "covIncrement", "timeDelay",
                "activeText", "inactiveText", "stateText", "numberOfStates",
                "minPresValue", "maxPresValue", "resolution"
            ]

            for prop in properties:
                value = await self.read_property_value(device_address, obj_identifier, prop)
                if value is not None:
                    point_data[prop] = str(value)

            self.all_points.append(point_data)

        except Exception as e:
            print(f"      Error reading object {obj_id}: {e}")


def is_port_in_use(port: int, ip_address: str = '') -> bool:
    """Check if a UDP port is currently in use

    Note: Binds to wildcard (0.0.0.0) instead of specific IP to work from inside Docker container.
    Even with network_mode: host, container cannot bind to specific host IP addresses.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Use SO_REUSEADDR to detect if port is truly available
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to wildcard to check port availability from inside container
            s.bind(('0.0.0.0', port))
            return False  # Port is available
    except OSError:
        return True  # Port is in use


def run_discovery(job_id: str):
    """
    Main discovery function - called by API endpoint

    Args:
        job_id: UUID of DiscoveryJob in database
    """

    print(f"\n=== BACnet Discovery Started ===")
    print(f"Job ID: {job_id}")

    # Connect to database
    import os
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5434')),
            database=os.getenv('DB_NAME', 'bacpipes'),
            user=os.getenv('DB_USER', 'anatoli'),
            password=""
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Read job configuration
        cursor.execute(
            'SELECT * FROM "DiscoveryJob" WHERE id = %s',
            (job_id,)
        )
        job = cursor.fetchone()

        if not job:
            print(f"ERROR: Job {job_id} not found in database")
            return

        ip_address = job['ipAddress']
        port = job['port']
        timeout = job['timeout']
        device_id = job['deviceId']

        print(f"Configuration:")
        print(f"  IP Address: {ip_address}")
        print(f"  Port: {port}")
        print(f"  Timeout: {timeout}s")
        print(f"  Device ID: {device_id}")

    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        return

    # Run discovery with asyncio
    try:
        asyncio.run(discovery_main(job_id, ip_address, port, timeout, device_id, conn))
    except Exception as e:
        print(f"ERROR: Discovery failed: {e}")

        # Update job as error
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''UPDATE "DiscoveryJob"
                   SET status = 'error',
                       "errorMessage" = %s,
                       "completedAt" = %s
                   WHERE id = %s''',
                (str(e), datetime.now(), job_id)
            )
            conn.commit()
        except:
            pass
    finally:
        conn.close()


async def discovery_main(job_id: str, ip_address: str, port: int, timeout: int, device_id: int, conn):
    """Async discovery main loop"""

    # Discovery coordination lock file
    lock_file = Path("/tmp/bacnet_discovery_active")

    try:
        # Create lock file to signal mqtt_publisher to shutdown
        lock_file.touch()
        print(f"🔒 Discovery lock created - signaling mqtt_publisher to release port {port}...")

        # Wait for port to be released (check with socket on specific IP)
        max_wait = 20  # seconds (increased for reliability with database query delays)
        print(f"⏳ Waiting for port {port} on {ip_address} to be released (max {max_wait}s)...")
        wait_start = time.time()
        for i in range(max_wait):
            if not is_port_in_use(port, ip_address):
                elapsed = time.time() - wait_start
                print(f"✅ Port {port} on {ip_address} available after {elapsed:.2f}s")
                break
            await asyncio.sleep(1)
            if (i + 1) % 3 == 0:  # Progress update every 3 seconds
                print(f"   Still waiting... ({i + 1}s elapsed)")
        else:
            error_msg = f"Timeout: mqtt_publisher did not release port {port} on {ip_address} in {max_wait}s"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)

        # Create BACpypes3 application
        local_addr = Address(f"{ip_address}/24:{port}")
        app = DiscoveryApp(local_addr, device_id, timeout)

        print(f"\nStarting discovery on {local_addr}...")
        print("Sending Who-Is request...")

        # Calculate broadcast address (assumes /24 subnet)
        ip_parts = ip_address.split('.')
        broadcast_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"

        # Send Who-Is request
        who_is = WhoIsRequest(destination=Address(f"{broadcast_ip}/24"))
        await app.request(who_is)

        # Wait for responses
        print(f"Waiting {timeout}s for device responses...")
        await asyncio.sleep(timeout)

        # Process results
        print(f"\n=== Discovery Complete ===")
        print(f"Found {len(app.found_devices)} devices")
        print(f"Collected {len(app.all_points)} points")

        # Save to database
        save_to_database(job_id, app.found_devices, app.all_points, conn)

        # Close application
        app.close()

    finally:
        # Always remove lock file, even on error
        if lock_file.exists():
            lock_file.unlink()
            print("🔓 Discovery lock removed - mqtt_publisher will restart")


def save_to_database(job_id: str, devices: List[Tuple[str, int]], points: List[Dict], conn):
    """Save discovered devices and points to PostgreSQL"""

    print("\nSaving to database...")
    cursor = conn.cursor()

    try:
        devices_saved = 0
        points_saved = 0
        devices_deleted = 0

        # Get list of device IDs found in this discovery
        found_device_ids = [device_id for _, device_id in devices]

        # Delete devices that were NOT found in this discovery
        # (Points are deleted automatically via CASCADE)
        if found_device_ids:
            # Delete devices not in the found list
            cursor.execute(
                '''DELETE FROM "Device" WHERE "deviceId" NOT IN %s RETURNING "deviceId"''',
                (tuple(found_device_ids),)
            )
        else:
            # No devices found - delete all existing devices
            cursor.execute('''DELETE FROM "Device" RETURNING "deviceId"''')

        deleted_rows = cursor.fetchall()
        devices_deleted = len(deleted_rows)
        if devices_deleted > 0:
            deleted_ids = [row[0] for row in deleted_rows]
            print(f"🗑️  Removed {devices_deleted} offline device(s): {deleted_ids}")

        # Group points by device
        device_points = {}
        for point in points:
            dev_id = point['device_id']
            if dev_id not in device_points:
                device_points[dev_id] = []
            device_points[dev_id].append(point)

        # Save devices
        for device_address, device_id in devices:
            device_name = next(
                (p['device_name'] for p in points if p['device_id'] == device_id),
                f"Device_{device_id}"
            )

            # Extract IP from address
            ip = device_address.split(':')[0] if ':' in device_address else device_address

            # Upsert device
            cursor.execute(
                '''INSERT INTO "Device"
                   ("deviceId", "deviceName", "ipAddress", "port", "enabled", "discoveredAt", "lastSeenAt")
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT ("deviceId")
                   DO UPDATE SET
                       "deviceName" = EXCLUDED."deviceName",
                       "ipAddress" = EXCLUDED."ipAddress",
                       "lastSeenAt" = EXCLUDED."lastSeenAt"
                   RETURNING id''',
                (device_id, device_name, ip, 47808, True, datetime.now(), datetime.now())
            )
            db_device_id = cursor.fetchone()[0]
            devices_saved += 1

            # Save points for this device
            if device_id in device_points:
                for point in device_points[device_id]:
                    # Upsert point
                    cursor.execute(
                        '''INSERT INTO "Point"
                           ("deviceId", "objectType", "objectInstance", "pointName",
                            "description", "units", "enabled", "isReadable", "isWritable",
                            "lastValue", "lastPollTime", "createdAt", "updatedAt")
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT ("deviceId", "objectType", "objectInstance")
                           DO UPDATE SET
                               "pointName" = EXCLUDED."pointName",
                               "description" = EXCLUDED."description",
                               "units" = EXCLUDED."units",
                               "lastValue" = EXCLUDED."lastValue",
                               "lastPollTime" = EXCLUDED."lastPollTime",
                               "updatedAt" = EXCLUDED."updatedAt"''',
                        (
                            db_device_id,
                            point.get('object_type', ''),
                            point.get('object_instance', 0),
                            point.get('objectName', 'Unknown'),
                            point.get('description'),
                            point.get('units'),
                            True,
                            True,
                            'priorityArray' in point,  # Has priority array = writable
                            point.get('presentValue'),  # Save presentValue to lastValue
                            datetime.now(),             # lastPollTime
                            datetime.now(),
                            datetime.now()
                        )
                    )
                    points_saved += 1

        # Update job status
        cursor.execute(
            '''UPDATE "DiscoveryJob"
               SET status = 'complete',
                   "devicesFound" = %s,
                   "pointsFound" = %s,
                   "completedAt" = %s
               WHERE id = %s''',
            (devices_saved, points_saved, datetime.now(), job_id)
        )

        conn.commit()

        print(f"✅ Saved {devices_saved} devices and {points_saved} points")
        print(f"✅ Job {job_id} marked as complete")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: Failed to save to database: {e}")

        # Update job as error
        cursor.execute(
            '''UPDATE "DiscoveryJob"
               SET status = 'error',
                   "errorMessage" = %s,
                   "completedAt" = %s
               WHERE id = %s''',
            (f"Database save error: {str(e)}", datetime.now(), job_id)
        )
        conn.commit()
        raise


if __name__ == "__main__":
    # For testing: python discovery.py <job_id>
    if len(sys.argv) > 1:
        run_discovery(sys.argv[1])
    else:
        print("Usage: python discovery.py <job_id>")

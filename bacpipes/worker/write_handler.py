"""BACnet write command handler."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlmodel import Session, select, create_engine

from ..models.point import Point
from ..models.device import Device
from ..models.write_history import WriteHistory
from .bacnet_client import BACnetClient

logger = logging.getLogger(__name__)


class WriteHandler:
    """Handler for BACnet write commands received via MQTT."""

    def __init__(self, db_url: str, bacnet_client: BACnetClient):
        self.engine = create_engine(db_url)
        self.bacnet_client = bacnet_client
        self.pending_commands: List[Dict] = []

    def queue_command(self, payload: bytes):
        """Queue a write command from MQTT."""
        try:
            command = json.loads(payload.decode())
            logger.info(f"Received write command: {command.get('jobId')}")
            self.pending_commands.append(command)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in write command: {e}")
        except Exception as e:
            logger.error(f"Error processing write command: {e}")

    async def process_pending(self) -> List[Dict]:
        """Process pending write commands.

        Returns list of results for MQTT publishing.
        """
        results = []

        while self.pending_commands:
            command = self.pending_commands.pop(0)
            result = await self.execute_command(command)
            results.append(result)

        return results

    async def execute_command(self, command: Dict) -> Dict:
        """Execute a single write command with validation.

        Returns result dict for MQTT publishing.
        """
        job_id = command.get('jobId', 'unknown')
        device_id = command.get('deviceId')
        object_type = command.get('objectType')
        object_instance = command.get('objectInstance')
        value = command.get('value')
        priority = command.get('priority', 8)
        release = command.get('release', False)

        logger.info(f"Executing write command {job_id}")

        validation_errors = []

        # Validate required fields
        if not device_id or not object_type or object_instance is None:
            validation_errors.append({
                "field": "required",
                "code": "MISSING_FIELDS",
                "message": "deviceId, objectType, and objectInstance are required",
            })
            return self._create_error_result(job_id, validation_errors)

        # Look up point in database
        with Session(self.engine) as session:
            query = (
                select(Point, Device)
                .join(Device, Point.deviceId == Device.id)
                .where(Device.deviceId == device_id)
                .where(Point.objectType == object_type)
                .where(Point.objectInstance == object_instance)
            )
            result = session.exec(query).first()

            if not result:
                validation_errors.append({
                    "field": "point",
                    "code": "POINT_NOT_FOUND",
                    "message": f"Point not found: device={device_id}, {object_type}:{object_instance}",
                })
                return self._create_error_result(job_id, validation_errors)

            point, device = result

            # Validate haystack name position-4 is "sp"
            if point.haystackPointName:
                parts = point.haystackPointName.split('.')
                if len(parts) >= 4 and parts[3] != 'sp':
                    validation_errors.append({
                        "field": "haystackName",
                        "code": "INVALID_POINT_FUNCTION",
                        "message": f"Write not allowed: position-4 must be 'sp', found '{parts[3]}'",
                    })

            # Validate isWritable
            if not point.isWritable:
                validation_errors.append({
                    "field": "isWritable",
                    "code": "POINT_NOT_WRITABLE",
                    "message": f"Point '{point.pointName}' is not writable",
                })

            # Validate priority
            if not (1 <= priority <= 16):
                validation_errors.append({
                    "field": "priority",
                    "code": "INVALID_PRIORITY",
                    "message": f"Priority must be 1-16, got {priority}",
                })

            # Validate value range
            if not release and value is not None:
                try:
                    value_float = float(value)
                    if point.minPresValue is not None and value_float < point.minPresValue:
                        validation_errors.append({
                            "field": "value",
                            "code": "VALUE_BELOW_MINIMUM",
                            "message": f"Value {value_float} below minimum {point.minPresValue}",
                        })
                    if point.maxPresValue is not None and value_float > point.maxPresValue:
                        validation_errors.append({
                            "field": "value",
                            "code": "VALUE_ABOVE_MAXIMUM",
                            "message": f"Value {value_float} above maximum {point.maxPresValue}",
                        })
                except (ValueError, TypeError):
                    validation_errors.append({
                        "field": "value",
                        "code": "INVALID_VALUE_TYPE",
                        "message": f"Value must be numeric, got: {value}",
                    })

            # Return validation errors if any
            if validation_errors:
                return self._create_error_result(
                    job_id,
                    validation_errors,
                    device_id=device_id,
                    point_name=point.pointName,
                )

            # Execute BACnet write
            success, error_msg = await self.bacnet_client.write_property(
                device_ip=device.ipAddress,
                device_port=device.port,
                object_type=object_type,
                object_instance=object_instance,
                value=value,
                priority=priority,
            )

            # Record in history
            history = WriteHistory(
                pointId=point.id,
                value=str(value) if value is not None else None,
                priority=priority,
                release=release,
                success=success,
                errorMessage=error_msg,
            )
            session.add(history)
            session.commit()

            # Return result
            return {
                "jobId": job_id,
                "success": success,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": error_msg,
                "deviceId": device_id,
                "pointName": point.pointName,
                "haystackName": point.haystackPointName,
                "value": value,
                "priority": priority,
                "release": release,
                "validationErrors": [],
            }

    def _create_error_result(
        self,
        job_id: str,
        validation_errors: List[Dict],
        device_id: Optional[int] = None,
        point_name: Optional[str] = None,
    ) -> Dict:
        """Create standardized error result."""
        return {
            "jobId": job_id,
            "success": False,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": "Validation failed",
            "deviceId": device_id,
            "pointName": point_name,
            "validationErrors": validation_errors,
        }

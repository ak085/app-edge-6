"""BACpypes3 BACnet client wrapper."""

import asyncio
import struct
import logging
from typing import Any, Optional

from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.local.device import DeviceObject
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.apdu import ReadPropertyRequest, WritePropertyRequest, AbortPDU, RejectPDU, ErrorPDU
from bacpypes3.basetypes import PropertyIdentifier

logger = logging.getLogger(__name__)


# Object type mapping
OBJ_TYPE_MAP = {
    'analog-input': 'analogInput',
    'analog-output': 'analogOutput',
    'analog-value': 'analogValue',
    'binary-input': 'binaryInput',
    'binary-output': 'binaryOutput',
    'binary-value': 'binaryValue',
    'multi-state-input': 'multiStateInput',
    'multi-state-output': 'multiStateOutput',
    'multi-state-value': 'multiStateValue',
    'date-value': 'dateValue',
}


class BACnetClient:
    """BACpypes3 client wrapper for BACnet operations."""

    def __init__(self, local_ip: str, port: int = 47808, device_id: int = 3001234):
        self.local_ip = local_ip
        self.port = port
        self.device_id = device_id
        self.app: Optional[NormalApplication] = None

        # Retry configuration
        self.max_retries = 3
        self.base_timeout = 6000  # 6 seconds

    def initialize(self) -> bool:
        """Initialize BACpypes3 application."""
        try:
            # Create BACnet device
            device = DeviceObject(
                objectIdentifier=ObjectIdentifier(f"device,{self.device_id}"),
                objectName="BacPipes",
                vendorIdentifier=842,  # Servisys
                maxApduLengthAccepted=1024,
                segmentationSupported="segmentedBoth",
            )

            # Create address for BACnet interface
            local_address = Address(f"{self.local_ip}:{self.port}")

            # Create NormalApplication
            self.app = NormalApplication(device, local_address)

            logger.info(f"BACpypes3 initialized on {local_address}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize BACnet: {e}")
            return False

    def close(self):
        """Close the BACnet application."""
        if self.app:
            try:
                self.app.close()
            except Exception as e:
                logger.warning(f"Error closing BACnet app: {e}")
            self.app = None

    async def read_property(
        self,
        device_ip: str,
        device_port: int,
        object_type: str,
        object_instance: int,
        property_name: str = "presentValue",
    ) -> Optional[Any]:
        """Read a property from a BACnet object with retry logic."""
        if not self.app:
            logger.error("BACnet app not initialized")
            return None

        obj_type_bacnet = OBJ_TYPE_MAP.get(object_type, object_type)
        device_address = Address(f"{device_ip}:{device_port}")
        object_id = ObjectIdentifier(f"{obj_type_bacnet},{object_instance}")

        for attempt in range(self.max_retries + 1):
            try:
                # Calculate timeout with exponential backoff
                timeout = self.base_timeout * (2 ** attempt) if attempt > 0 else self.base_timeout

                # Create read request
                request = ReadPropertyRequest(
                    objectIdentifier=object_id,
                    propertyIdentifier=PropertyIdentifier(property_name),
                    destination=device_address,
                )

                # Send request with timeout
                response = await asyncio.wait_for(
                    self.app.request(request),
                    timeout=timeout / 1000.0,
                )

                if response and hasattr(response, 'propertyValue'):
                    return self._extract_value(response.propertyValue)

            except asyncio.TimeoutError:
                logger.debug(f"Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5)

            except (AbortPDU, RejectPDU, ErrorPDU) as e:
                logger.debug(f"BACnet error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.debug(f"Error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5)

        logger.error(f"Failed to read {object_type}:{object_instance} after {self.max_retries + 1} attempts")
        return None

    async def write_property(
        self,
        device_ip: str,
        device_port: int,
        object_type: str,
        object_instance: int,
        value: Any,
        priority: int = 8,
    ) -> tuple[bool, Optional[str]]:
        """Write a value to a BACnet object.

        Returns: (success, error_message)
        """
        if not self.app:
            return False, "BACnet app not initialized"

        try:
            from bacpypes3.primitivedata import Real, Unsigned

            obj_type_bacnet = OBJ_TYPE_MAP.get(object_type, object_type)
            device_address = Address(f"{device_ip}:{device_port}")
            object_id = ObjectIdentifier(f"{obj_type_bacnet},{object_instance}")

            # Convert value to appropriate BACnet type
            if 'multi-state' in object_type:
                write_value = Unsigned(int(value))
            elif 'binary' in object_type:
                write_value = Unsigned(1 if value else 0)
            else:
                write_value = Real(float(value))

            # Create write request
            request = WritePropertyRequest(
                objectIdentifier=object_id,
                propertyIdentifier=PropertyIdentifier('presentValue'),
                destination=device_address,
            )
            request.propertyValue = write_value

            # Send request
            await asyncio.wait_for(
                self.app.request(request),
                timeout=10.0,
            )

            return True, None

        except asyncio.TimeoutError:
            return False, "BACnet write request timeout"

        except Exception as e:
            return False, f"BACnet write failed: {str(e)}"

    def _extract_value(self, bacnet_value) -> Optional[Any]:
        """Extract readable value from BACnet property value."""
        try:
            # Direct numeric/boolean types
            if isinstance(bacnet_value, (int, float, bool)):
                return bacnet_value

            # Try .value attribute
            if hasattr(bacnet_value, 'value'):
                extracted = bacnet_value.value
                if isinstance(extracted, (int, float, bool, str)):
                    return extracted

            # Check string representation
            value_str = str(bacnet_value)

            # Handle object representations
            if "bacpypes3" in value_str and "object at" in value_str:
                if hasattr(bacnet_value, 'tagList') and bacnet_value.tagList:
                    return self._extract_from_taglist(bacnet_value.tagList)
            else:
                # Try to parse as number
                value_clean = value_str.strip()
                try:
                    if '.' in value_clean:
                        return float(value_clean)
                    else:
                        return int(value_clean)
                except ValueError:
                    if len(value_clean) < 100:
                        return value_clean

            return None

        except Exception as e:
            logger.error(f"Value extraction error: {e}")
            return None

    def _extract_from_taglist(self, tag_list) -> Optional[Any]:
        """Extract value from BACpypes3 tag list."""
        tag_list = list(tag_list)

        # Find tag with data
        data_tag = None
        for tag in tag_list:
            if hasattr(tag, 'tag_data') and tag.tag_data and len(tag.tag_data) > 0:
                data_tag = tag
                break

        if not data_tag and tag_list:
            data_tag = tag_list[0]

        if data_tag and hasattr(data_tag, 'tag_data') and hasattr(data_tag, 'tag_number'):
            tag_number = data_tag.tag_number
            tag_data = data_tag.tag_data

            if not tag_data or len(tag_data) == 0:
                return None

            # Decode based on tag type
            if tag_number == 1:  # Boolean
                return bool(tag_data[0])
            elif tag_number == 2:  # Unsigned
                if len(tag_data) == 1:
                    return tag_data[0]
                elif len(tag_data) == 2:
                    return struct.unpack('>H', tag_data)[0]
                elif len(tag_data) == 4:
                    return struct.unpack('>I', tag_data)[0]
                else:
                    return int.from_bytes(tag_data, byteorder='big')
            elif tag_number == 3:  # Integer
                if len(tag_data) == 1:
                    return struct.unpack('>b', tag_data)[0]
                elif len(tag_data) == 2:
                    return struct.unpack('>h', tag_data)[0]
                elif len(tag_data) == 4:
                    return struct.unpack('>i', tag_data)[0]
                else:
                    return int.from_bytes(tag_data, byteorder='big', signed=True)
            elif tag_number == 4:  # Real (float)
                return struct.unpack('>f', tag_data)[0]
            elif tag_number == 5:  # Double
                return struct.unpack('>d', tag_data)[0]
            elif tag_number == 7:  # CharacterString
                return tag_data.decode('utf-8')
            elif tag_number == 9:  # Enumerated
                return int.from_bytes(tag_data, byteorder='big')

        return None

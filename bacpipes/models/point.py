"""Point model - BACnet objects (points) with Haystack tagging."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint

if TYPE_CHECKING:
    from .device import Device
    from .write_history import WriteHistory


class Point(SQLModel, table=True):
    """BACnet object (point) with Haystack tagging support."""

    __tablename__ = "Point"
    __table_args__ = (
        UniqueConstraint("deviceId", "objectType", "objectInstance"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # BACnet identification
    deviceId: int = Field(foreign_key="Device.id", index=True)
    objectType: str  # e.g., "analog-input", "analog-output", "binary-input"
    objectInstance: int  # BACnet object instance number
    pointName: str  # BACnet object name
    description: Optional[str] = None
    units: Optional[str] = None  # Engineering units (e.g., "degreesCelsius")

    # Haystack tagging (8-field semantic naming)
    siteId: Optional[str] = None  # e.g., "klcc", "menara"
    equipmentType: Optional[str] = None  # e.g., "ahu", "vav", "chiller"
    equipmentId: Optional[str] = None  # e.g., "12", "north_wing_01"
    pointFunction: Optional[str] = None  # e.g., "sp", "cmd", "sensor"
    quantity: Optional[str] = None  # e.g., "temp", "speed", "pos", "pressure"
    subject: Optional[str] = None  # e.g., "air", "water", "chilled-water"
    location: Optional[str] = None  # e.g., "supply", "return", "coil"
    qualifier: Optional[str] = None  # e.g., "effective", "min", "max", "enable"
    haystackPointName: Optional[str] = None  # Auto-generated from above fields
    dis: Optional[str] = None  # Human-readable display name

    # MQTT configuration
    enabled: bool = Field(default=True, index=True)  # Point enabled for display
    mqttPublish: bool = Field(default=False, index=True)  # Publish to MQTT
    mqttTopic: Optional[str] = None  # Auto-generated from Haystack tags
    pollInterval: int = Field(default=60)  # Polling interval in seconds
    qos: int = Field(default=1)  # MQTT QoS (0, 1, 2)

    # Access control
    isReadable: bool = Field(default=True)
    isWritable: bool = Field(default=False)
    priorityArray: bool = Field(default=False)  # Has priority array (16 levels)
    priorityLevel: Optional[int] = None  # Default priority for writes (1-16)

    # Value range validation
    minPresValue: Optional[float] = None
    maxPresValue: Optional[float] = None

    # Operational metadata
    lastValue: Optional[str] = None  # Last polled value
    lastPollTime: Optional[datetime] = None
    errorCount: int = Field(default=0)
    lastError: Optional[str] = None

    # Timestamps
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

    # Relationships
    device: Optional["Device"] = Relationship(back_populates="points")
    writeHistory: List["WriteHistory"] = Relationship(
        back_populates="point", cascade_delete=True
    )

    def generate_haystack_name(self) -> Optional[str]:
        """Generate Haystack point name from tag fields."""
        parts = [
            self.siteId,
            self.equipmentType,
            self.equipmentId,
            self.pointFunction,
            self.quantity,
            self.subject,
            self.location,
            self.qualifier,
        ]
        # Filter out None and empty values
        valid_parts = [p for p in parts if p]
        if valid_parts:
            return ".".join(valid_parts)
        return None

    def generate_mqtt_topic(self) -> Optional[str]:
        """Generate MQTT topic from Haystack name with objectInstance for uniqueness."""
        name = self.generate_haystack_name()
        if name:
            # Replace dots with slashes for topic hierarchy
            # Append objectInstance for unique identification
            return f"{name.replace('.', '/')}/{self.objectInstance}"
        return None

"""Device model - BACnet devices discovered on the network."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .point import Point


class Device(SQLModel, table=True):
    """BACnet device discovered on the network."""

    __tablename__ = "Device"

    id: Optional[int] = Field(default=None, primary_key=True)
    deviceId: int = Field(unique=True, index=True)  # BACnet device ID
    deviceName: str  # e.g., "Excelsior", "POS466.65/100"
    ipAddress: str  # e.g., "192.168.1.37"
    port: int = Field(default=47808)
    vendorId: Optional[int] = None  # BACnet vendor ID
    vendorName: Optional[str] = None  # e.g., "Siemens"
    description: Optional[str] = None
    enabled: bool = Field(default=True, index=True)

    # Timestamps
    discoveredAt: datetime = Field(default_factory=datetime.now)
    lastSeenAt: datetime = Field(default_factory=datetime.now)

    # Relationships
    points: List["Point"] = Relationship(back_populates="device", cascade_delete=True)

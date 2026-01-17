"""Discovery job tracking model."""

from datetime import datetime
from typing import Optional
import uuid
from sqlmodel import SQLModel, Field


class DiscoveryJob(SQLModel, table=True):
    """BACnet discovery job tracking."""

    __tablename__ = "DiscoveryJob"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # Configuration
    ipAddress: str
    port: int = Field(default=47808)
    timeout: int = Field(default=15)  # Seconds
    deviceId: int = Field(default=3001234)  # Scanner device ID

    # Status
    status: str  # "running", "complete", "error", "cancelled"

    # Results
    devicesFound: int = Field(default=0)
    pointsFound: int = Field(default=0)
    errorMessage: Optional[str] = None

    # Timestamps
    startedAt: datetime = Field(default_factory=datetime.now, index=True)
    completedAt: Optional[datetime] = None

"""Write command history model."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .point import Point


class WriteHistory(SQLModel, table=True):
    """Audit log for BACnet write commands."""

    __tablename__ = "WriteHistory"

    id: Optional[int] = Field(default=None, primary_key=True)
    jobId: str = Field(default_factory=lambda: str(uuid.uuid4()), unique=True)

    # Target point
    pointId: int = Field(foreign_key="Point.id", index=True)

    # Write command
    value: Optional[str] = None  # Value written (null if releasing priority)
    priority: int  # Priority level (1-16)
    release: bool = Field(default=False)  # True if releasing priority

    # Result
    success: bool
    errorMessage: Optional[str] = None

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now, index=True)

    # Relationships
    point: Optional["Point"] = Relationship(back_populates="writeHistory")

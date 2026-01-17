"""Error log model."""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class ErrorLog(SQLModel, table=True):
    """Error tracking for debugging and monitoring."""

    __tablename__ = "ErrorLog"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Context
    pointId: Optional[int] = Field(default=None, index=True)  # Optional related point
    source: Optional[str] = Field(default=None, index=True)  # e.g., "worker", "discovery", "api"
    message: str
    stackTrace: Optional[str] = None

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now, index=True)

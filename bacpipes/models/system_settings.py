"""System settings model."""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class SystemSettings(SQLModel, table=True):
    """System-wide settings including auth and BACnet config."""

    __tablename__ = "SystemSettings"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Authentication
    adminUsername: str = Field(default="admin")
    adminPasswordHash: str = Field(default="")  # bcrypt hash, empty = use default "admin"
    masterPinHash: Optional[str] = None  # bcrypt hash of master PIN

    # Network
    bacnetIp: Optional[str] = None  # Nullable - configured via setup wizard
    bacnetPort: int = Field(default=47808)
    bacnetDeviceId: int = Field(default=3001234)
    discoveryTimeout: int = Field(default=15)  # Seconds

    # System
    timezone: str = Field(default="UTC")
    defaultPollInterval: int = Field(default=60)  # Seconds
    configRefreshInterval: int = Field(default=60)  # Seconds
    dashboardRefresh: int = Field(default=10)  # Seconds
    logRetentionDays: int = Field(default=30)

    # Timestamps
    updatedAt: datetime = Field(default_factory=datetime.now)

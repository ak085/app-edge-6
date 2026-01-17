"""MQTT configuration model."""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class MqttConfig(SQLModel, table=True):
    """MQTT broker configuration."""

    __tablename__ = "MqttConfig"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Connection
    broker: Optional[str] = None  # Nullable - configured via setup wizard
    port: int = Field(default=1883)
    clientId: str = Field(default="bacpipes_worker")
    username: Optional[str] = None
    password: Optional[str] = None
    keepAlive: int = Field(default=30)  # Seconds

    # TLS/Security
    tlsEnabled: bool = Field(default=False)
    tlsInsecure: bool = Field(default=False)  # Skip certificate verification
    caCertPath: Optional[str] = None
    clientCertPath: Optional[str] = None
    clientKeyPath: Optional[str] = None

    # Topics
    writeCommandTopic: str = Field(default="bacnet/write/command")
    writeResultTopic: str = Field(default="bacnet/write/result")

    # Subscription (for setpoint overrides from ML server)
    subscribeEnabled: bool = Field(default=False)
    subscribeTopicPattern: str = Field(default="override/#")
    subscribeQos: int = Field(default=1)

    # Status
    enabled: bool = Field(default=True)
    connectionStatus: str = Field(default="disconnected")  # connected/connecting/disconnected
    lastConnected: Optional[datetime] = None
    lastDataFlow: Optional[datetime] = None

    # Timestamps
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)

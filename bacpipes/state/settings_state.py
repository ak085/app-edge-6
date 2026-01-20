"""Settings state for BacPipes."""

from datetime import datetime
from typing import Optional
import reflex as rx
from sqlmodel import select

from ..models.mqtt_config import MqttConfig
from ..models.system_settings import SystemSettings
from ..utils.auth import hash_password, verify_password, hash_pin, verify_pin
from ..utils.network import get_local_ip, get_network_interfaces


class SettingsState(rx.State):
    """Settings management state."""

    # BACnet settings
    bacnet_ip: str = ""
    bacnet_port: int = 47808
    bacnet_device_id: int = 3001234
    discovery_timeout: int = 15

    # MQTT settings
    mqtt_broker: str = ""
    mqtt_port: int = 1883
    mqtt_client_id: str = "bacpipes_worker"
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_tls_enabled: bool = False
    mqtt_tls_insecure: bool = False
    mqtt_ca_cert_path: str = ""

    # MQTT Subscription settings (override prefix is fixed to "override/#")
    mqtt_subscribe_enabled: bool = False

    # CA Certificate upload
    ca_cert_filename: str = ""
    ca_cert_upload_message: str = ""

    # System settings
    timezone: str = "UTC"
    default_poll_interval: int = 60

    # Poll interval apply message
    poll_interval_message: str = ""

    # Password change form
    current_password: str = ""
    new_password: str = ""
    confirm_password: str = ""
    master_pin: str = ""

    # PIN change form
    current_pin: str = ""
    new_pin: str = ""
    confirm_pin: str = ""

    # Status messages
    bacnet_save_message: str = ""
    mqtt_save_message: str = ""
    mqtt_subscription_message: str = ""
    password_message: str = ""
    pin_message: str = ""

    # Network interfaces for BACnet IP selection
    network_interfaces: list[dict] = []

    # Loading
    is_loading: bool = False

    # First run detection
    is_first_run: bool = False

    async def load_settings(self):
        """Load all settings from database."""
        self.is_loading = True
        yield

        # Get network interfaces
        self.network_interfaces = get_network_interfaces()

        with rx.session() as session:
            # Load system settings
            settings = session.exec(select(SystemSettings)).first()

            if not settings:
                # First run - create default settings
                self.is_first_run = True
                settings = SystemSettings()
                session.add(settings)
                session.commit()
                session.refresh(settings)
            else:
                # Check if setup is needed
                self.is_first_run = settings.bacnetIp is None

            self.bacnet_ip = settings.bacnetIp or ""
            self.bacnet_port = settings.bacnetPort
            self.bacnet_device_id = settings.bacnetDeviceId
            self.discovery_timeout = settings.discoveryTimeout
            self.timezone = settings.timezone
            self.default_poll_interval = settings.defaultPollInterval

            # Load MQTT config
            mqtt_config = session.exec(select(MqttConfig)).first()

            if not mqtt_config:
                # Create default MQTT config
                mqtt_config = MqttConfig()
                session.add(mqtt_config)
                session.commit()
                session.refresh(mqtt_config)

            self.mqtt_broker = mqtt_config.broker or ""
            self.mqtt_port = mqtt_config.port
            self.mqtt_client_id = mqtt_config.clientId
            self.mqtt_username = mqtt_config.username or ""
            self.mqtt_password = mqtt_config.password or ""
            self.mqtt_tls_enabled = mqtt_config.tlsEnabled
            self.mqtt_tls_insecure = mqtt_config.tlsInsecure
            self.mqtt_ca_cert_path = mqtt_config.caCertPath or ""
            self.mqtt_subscribe_enabled = mqtt_config.subscribeEnabled

            # Extract filename from path if cert exists
            if self.mqtt_ca_cert_path:
                import os
                self.ca_cert_filename = os.path.basename(self.mqtt_ca_cert_path)
            else:
                self.ca_cert_filename = ""

        self.is_loading = False

    async def save_bacnet_config(self, form_data: dict):
        """Save BACnet configuration."""
        self.bacnet_save_message = ""
        yield

        ip = form_data.get("bacnet_ip", "").strip()
        port = int(form_data.get("bacnet_port", 47808))
        device_id = int(form_data.get("bacnet_device_id", 3001234))
        timeout = int(form_data.get("discovery_timeout", 15))

        if not ip:
            self.bacnet_save_message = "BACnet IP is required"
            yield
            return

        with rx.session() as session:
            settings = session.exec(select(SystemSettings)).first()
            if not settings:
                settings = SystemSettings()

            settings.bacnetIp = ip
            settings.bacnetPort = port
            settings.bacnetDeviceId = device_id
            settings.discoveryTimeout = timeout
            settings.updatedAt = datetime.now()

            session.add(settings)
            session.commit()

        self.bacnet_ip = ip
        self.bacnet_port = port
        self.bacnet_device_id = device_id
        self.discovery_timeout = timeout
        self.bacnet_save_message = "BACnet configuration saved"

    async def save_mqtt_config(self, form_data: dict):
        """Save MQTT configuration."""
        self.mqtt_save_message = ""
        yield

        broker = form_data.get("mqtt_broker", "").strip()
        port = int(form_data.get("mqtt_port", 1883))
        client_id = form_data.get("mqtt_client_id", "bacpipes_worker").strip()
        username = form_data.get("mqtt_username", "").strip()
        password = form_data.get("mqtt_password", "")
        # Use state values for checkboxes (on_change already updated them)
        tls_enabled = self.mqtt_tls_enabled
        tls_insecure = self.mqtt_tls_insecure

        if not broker:
            self.mqtt_save_message = "MQTT broker is required"
            yield
            return

        with rx.session() as session:
            mqtt_config = session.exec(select(MqttConfig)).first()
            if not mqtt_config:
                mqtt_config = MqttConfig()

            mqtt_config.broker = broker
            mqtt_config.port = port
            mqtt_config.clientId = client_id
            mqtt_config.username = username or None
            mqtt_config.password = password or None
            mqtt_config.tlsEnabled = tls_enabled
            mqtt_config.tlsInsecure = tls_insecure
            # Don't overwrite caCertPath - it's managed by upload
            mqtt_config.updatedAt = datetime.now()

            session.add(mqtt_config)
            session.commit()

        self.mqtt_broker = broker
        self.mqtt_port = port
        self.mqtt_client_id = client_id
        self.mqtt_username = username
        self.mqtt_password = password
        self.mqtt_save_message = "MQTT configuration saved. Restart worker to apply TLS changes."

    async def save_system_config(self, form_data: dict):
        """Save system configuration (timezone, poll interval)."""
        timezone = form_data.get("timezone", "UTC").strip()
        poll_interval = int(form_data.get("default_poll_interval", 60))

        with rx.session() as session:
            settings = session.exec(select(SystemSettings)).first()
            if settings:
                settings.timezone = timezone
                settings.defaultPollInterval = poll_interval
                settings.updatedAt = datetime.now()
                session.add(settings)
                session.commit()

        self.timezone = timezone
        self.default_poll_interval = poll_interval

    async def change_password(self, form_data: dict):
        """Change admin password."""
        self.password_message = ""
        yield

        current = form_data.get("current_password", "")
        new = form_data.get("new_password", "")
        confirm = form_data.get("confirm_password", "")
        pin = form_data.get("master_pin", "")

        if not current:
            self.password_message = "Current password is required"
            yield
            return

        if not new:
            self.password_message = "New password is required"
            yield
            return

        if len(new) < 4:
            self.password_message = "Password must be at least 4 characters"
            yield
            return

        if new != confirm:
            self.password_message = "Passwords do not match"
            yield
            return

        with rx.session() as session:
            settings = session.exec(select(SystemSettings)).first()
            if not settings:
                self.password_message = "System settings not found"
                yield
                return

            # Verify current password
            if not verify_password(current, settings.adminPasswordHash):
                self.password_message = "Current password is incorrect"
                yield
                return

            # Verify PIN if set
            if settings.masterPinHash:
                if not pin:
                    self.password_message = "Master PIN is required"
                    yield
                    return
                if not verify_pin(pin, settings.masterPinHash):
                    self.password_message = "Invalid Master PIN"
                    yield
                    return

            # Update password
            settings.adminPasswordHash = hash_password(new)
            settings.updatedAt = datetime.now()
            session.add(settings)
            session.commit()

        self.password_message = "Password changed successfully"
        self.current_password = ""
        self.new_password = ""
        self.confirm_password = ""
        self.master_pin = ""

    async def set_master_pin(self, form_data: dict):
        """Set or change master PIN."""
        self.pin_message = ""
        yield

        current = form_data.get("current_pin", "")
        new = form_data.get("new_pin", "")
        confirm = form_data.get("confirm_pin", "")

        if not new:
            self.pin_message = "New PIN is required"
            yield
            return

        if len(new) < 4 or len(new) > 6:
            self.pin_message = "PIN must be 4-6 digits"
            yield
            return

        if not new.isdigit():
            self.pin_message = "PIN must contain only digits"
            yield
            return

        if new != confirm:
            self.pin_message = "PINs do not match"
            yield
            return

        with rx.session() as session:
            settings = session.exec(select(SystemSettings)).first()
            if not settings:
                self.pin_message = "System settings not found"
                yield
                return

            # Verify current PIN if one exists
            if settings.masterPinHash:
                if not current:
                    self.pin_message = "Current PIN is required"
                    yield
                    return
                if not verify_pin(current, settings.masterPinHash):
                    self.pin_message = "Current PIN is incorrect"
                    yield
                    return

            # Set new PIN
            settings.masterPinHash = hash_pin(new)
            settings.updatedAt = datetime.now()
            session.add(settings)
            session.commit()

        self.pin_message = "Master PIN updated successfully"
        self.current_pin = ""
        self.new_pin = ""
        self.confirm_pin = ""

    async def save_mqtt_subscription(self, form_data: dict):
        """Save MQTT subscription settings."""
        self.mqtt_subscription_message = ""
        yield

        subscribe_enabled = form_data.get("subscribe_enabled") == "on"

        with rx.session() as session:
            mqtt_config = session.exec(select(MqttConfig)).first()
            if mqtt_config:
                mqtt_config.subscribeEnabled = subscribe_enabled
                # Fixed values - override topic pattern is always "override/#" with QoS 1
                mqtt_config.subscribeTopicPattern = "override/#"
                mqtt_config.subscribeQos = 1
                mqtt_config.updatedAt = datetime.now()
                session.add(mqtt_config)
                session.commit()

        self.mqtt_subscribe_enabled = subscribe_enabled
        self.mqtt_subscription_message = "Settings saved. Restart worker to apply."

    def set_mqtt_subscribe_enabled(self, value: bool):
        """Toggle MQTT subscription."""
        self.mqtt_subscribe_enabled = value

    def set_mqtt_tls_enabled(self, value: bool):
        """Toggle MQTT TLS."""
        self.mqtt_tls_enabled = value
        self.ca_cert_upload_message = ""  # Clear any message

    def set_mqtt_tls_insecure(self, value: bool):
        """Toggle MQTT TLS insecure mode."""
        self.mqtt_tls_insecure = value
        self.ca_cert_upload_message = ""  # Clear any message

    async def handle_ca_cert_upload(self, files: list[rx.UploadFile]):
        """Handle CA certificate file upload."""
        import os

        self.ca_cert_upload_message = ""

        if not files:
            # Silently ignore - user just opened dialog without selecting
            return

        upload_file = files[0]
        filename = upload_file.filename

        # Validate file extension
        if not filename.lower().endswith(('.crt', '.pem', '.cer')):
            self.ca_cert_upload_message = "Invalid file type. Use .crt, .pem, or .cer"
            return

        try:
            # Read file content
            content = await upload_file.read()

            # Save to certs directory
            cert_dir = "/app/certs"
            os.makedirs(cert_dir, exist_ok=True)

            cert_path = os.path.join(cert_dir, "ca.crt")
            with open(cert_path, "wb") as f:
                f.write(content)

            # Update database
            with rx.session() as session:
                mqtt_config = session.exec(select(MqttConfig)).first()
                if mqtt_config:
                    mqtt_config.caCertPath = cert_path
                    mqtt_config.updatedAt = datetime.now()
                    session.add(mqtt_config)
                    session.commit()

            self.mqtt_ca_cert_path = cert_path
            self.ca_cert_filename = filename
            self.ca_cert_upload_message = "Certificate uploaded successfully"

        except Exception as e:
            self.ca_cert_upload_message = f"Upload failed: {str(e)}"

    async def remove_ca_cert(self):
        """Remove uploaded CA certificate."""
        import os

        self.ca_cert_upload_message = ""

        try:
            # Remove file if exists
            if self.mqtt_ca_cert_path and os.path.exists(self.mqtt_ca_cert_path):
                os.remove(self.mqtt_ca_cert_path)

            # Update database
            with rx.session() as session:
                mqtt_config = session.exec(select(MqttConfig)).first()
                if mqtt_config:
                    mqtt_config.caCertPath = None
                    mqtt_config.updatedAt = datetime.now()
                    session.add(mqtt_config)
                    session.commit()

            self.mqtt_ca_cert_path = ""
            self.ca_cert_filename = ""
            self.ca_cert_upload_message = "Certificate removed"

        except Exception as e:
            self.ca_cert_upload_message = f"Remove failed: {str(e)}"

    def set_default_poll_interval(self, value: str):
        """Set default poll interval."""
        try:
            self.default_poll_interval = int(value) if value else 60
        except ValueError:
            self.default_poll_interval = 60

    async def apply_poll_interval_to_all(self):
        """Apply default poll interval to all MQTT-enabled points."""
        from ..models.point import Point

        self.poll_interval_message = ""
        yield

        with rx.session() as session:
            # Get all MQTT-enabled points
            points = session.exec(
                select(Point).where(Point.mqttPublish == True)
            ).all()

            count = 0
            for point in points:
                point.pollInterval = self.default_poll_interval
                point.updatedAt = datetime.now()
                session.add(point)
                count += 1

            # Also save to system settings
            settings = session.exec(select(SystemSettings)).first()
            if settings:
                settings.defaultPollInterval = self.default_poll_interval
                settings.updatedAt = datetime.now()
                session.add(settings)

            session.commit()

        self.poll_interval_message = f"Applied {self.default_poll_interval}s interval to {count} points"

    def set_timezone(self, value: str):
        """Set timezone."""
        self.timezone = value

    async def save_timezone(self):
        """Save timezone to database."""
        with rx.session() as session:
            settings = session.exec(select(SystemSettings)).first()
            if settings:
                settings.timezone = self.timezone
                settings.updatedAt = datetime.now()
                session.add(settings)
                session.commit()

    def shutdown_gui(self):
        """Shutdown the entire application (GUI + Worker).

        Note: The worker runs as a lifespan task in the same process as the GUI,
        so SIGTERM kills both. Restart with: docker compose up -d
        """
        import os
        import signal
        os.kill(os.getpid(), signal.SIGTERM)

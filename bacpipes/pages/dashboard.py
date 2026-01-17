"""Main dashboard page with tabs for BacPipes."""

import reflex as rx

from ..state.auth_state import AuthState
from ..state.dashboard_state import DashboardState
from ..state.discovery_state import DiscoveryState
from ..state.points_state import PointsState
from ..state.settings_state import SettingsState
from ..state.worker_state import WorkerState
from ..components.layout import page_layout
from ..components.status_card import status_card
from ..components.point_table import point_table
from ..components.point_editor import point_editor_dialog


def dashboard_tab() -> rx.Component:
    """Dashboard tab content with status cards and recent points."""
    return rx.vstack(
        # Auto-refresh toggle
        rx.hstack(
            rx.checkbox(
                "Auto-refresh",
                checked=DashboardState.auto_refresh_enabled,
                on_change=DashboardState.toggle_auto_refresh,
            ),
            rx.text(
                f"Last updated: {DashboardState.last_refresh}",
                size="2",
                color="gray",
            ),
            spacing="4",
            align="center",
            width="100%",
            padding_bottom="2",
        ),
        # Status cards row
        rx.hstack(
            status_card(
                title="MQTT Status",
                value=DashboardState.mqtt_status,
                icon="wifi",
                color=rx.cond(
                    DashboardState.mqtt_status == "connected",
                    "green",
                    "red",
                ),
            ),
            status_card(
                title="Devices",
                value=DashboardState.total_devices,
                icon="server",
                color="blue",
            ),
            status_card(
                title="Total Points",
                value=DashboardState.total_points,
                icon="database",
                color="purple",
            ),
            status_card(
                title="Publishing",
                value=DashboardState.publishing_points,
                icon="send",
                color="green",
            ),
            spacing="4",
            width="100%",
            wrap="wrap",
        ),
        # Connection info
        rx.hstack(
            rx.card(
                rx.vstack(
                    rx.text("MQTT Broker", size="2", color="gray"),
                    rx.text(DashboardState.mqtt_broker, weight="medium"),
                    spacing="1",
                ),
                padding="4",
            ),
            rx.card(
                rx.vstack(
                    rx.text("BACnet Interface", size="2", color="gray"),
                    rx.text(DashboardState.bacnet_ip, weight="medium"),
                    spacing="1",
                ),
                padding="4",
            ),
            rx.card(
                rx.vstack(
                    rx.text("Last Refresh", size="2", color="gray"),
                    rx.text(DashboardState.last_refresh, weight="medium"),
                    spacing="1",
                ),
                padding="4",
            ),
            spacing="4",
            width="100%",
        ),
        # Devices table
        rx.card(
            rx.vstack(
                rx.heading("Devices", size="4"),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Device ID"),
                            rx.table.column_header_cell("Name"),
                            rx.table.column_header_cell("IP Address"),
                            rx.table.column_header_cell("Points"),
                            rx.table.column_header_cell("Status"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            DashboardState.devices,
                            lambda device: rx.table.row(
                                rx.table.cell(device["deviceId"]),
                                rx.table.cell(device["deviceName"]),
                                rx.table.cell(device["ipAddress"]),
                                rx.table.cell(device["pointCount"]),
                                rx.table.cell(
                                    rx.badge(
                                        rx.cond(
                                            device["enabled"],
                                            "Enabled",
                                            "Disabled",
                                        ),
                                        color=rx.cond(
                                            device["enabled"],
                                            "green",
                                            "gray",
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        spacing="4",
        width="100%",
        on_mount=DashboardState.load_dashboard,
    )


def device_row(device: dict) -> rx.Component:
    """Row for discovered devices table."""
    return rx.table.row(
        rx.table.cell(device["deviceId"]),
        rx.table.cell(device["deviceName"]),
        rx.table.cell(device["ipAddress"]),
        rx.table.cell(device["vendorName"]),
        rx.table.cell(device["pointCount"]),
        rx.table.cell(
            rx.hstack(
                rx.switch(
                    checked=device["enabled"],
                    on_change=DiscoveryState.toggle_device_enabled(device["id"]),
                    color_scheme=rx.cond(device["enabled"], "green", "gray"),
                ),
                rx.text(
                    rx.cond(device["enabled"], "ON", "OFF"),
                    size="1",
                    color=rx.cond(device["enabled"], "green", "gray"),
                    weight="medium",
                ),
                spacing="2",
                align="center",
            ),
        ),
    )


def discovery_tab() -> rx.Component:
    """Discovery tab content."""
    return rx.vstack(
        # Scan form
        rx.card(
            rx.vstack(
                rx.heading("BACnet Discovery", size="4"),
                rx.form(
                    rx.hstack(
                        rx.vstack(
                            rx.text("IP Address", size="2"),
                            rx.input(
                                name="ip_address",
                                placeholder="192.168.1.35",
                                default_value=DiscoveryState.scan_ip,
                                width="200px",
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Timeout (s)", size="2"),
                            rx.input(
                                name="timeout",
                                type="number",
                                default_value=DiscoveryState.scan_timeout.to_string(),
                                width="100px",
                            ),
                            spacing="1",
                        ),
                        rx.button(
                            rx.cond(
                                DiscoveryState.is_scanning,
                                rx.hstack(
                                    rx.spinner(size="2"),
                                    rx.text("Scanning..."),
                                    spacing="2",
                                ),
                                rx.text("Start Discovery"),
                            ),
                            type="submit",
                            disabled=DiscoveryState.is_scanning,
                            size="3",
                        ),
                        rx.cond(
                            DiscoveryState.is_scanning,
                            rx.button(
                                "Cancel",
                                on_click=DiscoveryState.cancel_discovery,
                                color_scheme="red",
                                variant="outline",
                            ),
                        ),
                        spacing="4",
                        align="end",
                    ),
                    on_submit=DiscoveryState.start_discovery,
                ),
                rx.cond(
                    DiscoveryState.scan_progress != "",
                    rx.text(DiscoveryState.scan_progress, color="blue"),
                ),
                rx.cond(
                    DiscoveryState.last_scan_result != "",
                    rx.callout(
                        DiscoveryState.last_scan_result,
                        icon="info",
                    ),
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        # Discovered devices
        rx.card(
            rx.vstack(
                rx.heading("Discovered Devices", size="4"),
                rx.cond(
                    DiscoveryState.discovered_devices.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Device ID"),
                                rx.table.column_header_cell("Name"),
                                rx.table.column_header_cell("IP Address"),
                                rx.table.column_header_cell("Vendor"),
                                rx.table.column_header_cell("Points"),
                                rx.table.column_header_cell("Enabled"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                DiscoveryState.discovered_devices,
                                device_row,
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("No devices discovered yet. Run a discovery scan.", color="gray"),
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        spacing="4",
        width="100%",
        on_mount=DiscoveryState.load_discovery_data,
    )


def points_tab() -> rx.Component:
    """Points tab content."""
    return rx.vstack(
        # Bulk Configuration Card
        rx.card(
            rx.vstack(
                rx.heading("Bulk Configuration", size="4"),
                rx.text(
                    "Apply Site ID and Equipment mapping to all points at once",
                    size="2",
                    color="gray",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.text("Site ID *", size="2"),
                        rx.input(
                            placeholder="e.g., klcc",
                            value=PointsState.bulk_site_id,
                            on_change=PointsState.set_bulk_site_id,
                            width="200px",
                        ),
                        rx.text("Applied to all points", size="1", color="gray"),
                        spacing="1",
                    ),
                    spacing="4",
                ),
                # Device to Equipment Mapping Table
                rx.cond(
                    PointsState.bulk_devices.length() > 0,
                    rx.vstack(
                        rx.text("Device to Equipment Mapping", size="2", weight="medium"),
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Device"),
                                    rx.table.column_header_cell("IP"),
                                    rx.table.column_header_cell("Points"),
                                    rx.table.column_header_cell("Equipment Type"),
                                    rx.table.column_header_cell("Equipment ID"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    PointsState.bulk_devices,
                                    bulk_device_row,
                                ),
                            ),
                            width="100%",
                            size="1",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                rx.hstack(
                    rx.button(
                        "Apply to All Points",
                        on_click=PointsState.apply_bulk_config,
                        disabled=PointsState.bulk_site_id == "",
                    ),
                    rx.cond(
                        PointsState.bulk_save_message != "",
                        rx.text(
                            PointsState.bulk_save_message,
                            color=rx.cond(
                                PointsState.bulk_save_message.contains("applied"),
                                "green",
                                "red",
                            ),
                        ),
                    ),
                    spacing="4",
                    align="center",
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        # Filters
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("Device", size="1", color="gray"),
                        rx.select(
                            PointsState.device_options,
                            value=PointsState.filter_device_name,
                            on_change=PointsState.set_filter_device,
                            width="180px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Object Type", size="1", color="gray"),
                        rx.select(
                            PointsState.object_type_options,
                            value=PointsState.filter_object_type,
                            on_change=PointsState.set_filter_object_type,
                            width="180px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("MQTT Status", size="1", color="gray"),
                        rx.select(
                            ["All", "MQTT Enabled", "MQTT Disabled"],
                            value=PointsState.filter_mqtt_status,
                            on_change=PointsState.set_filter_mqtt_status,
                            width="150px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Search", size="1", color="gray"),
                        rx.input(
                            placeholder="Search points...",
                            value=PointsState.search_query,
                            on_change=PointsState.set_search_query,
                            width="200px",
                        ),
                        spacing="1",
                    ),
                    rx.cond(
                        (PointsState.filter_device_name != "All Devices") |
                        (PointsState.filter_object_type != "All Types") |
                        (PointsState.filter_mqtt_status != "All") |
                        (PointsState.search_query != ""),
                        rx.vstack(
                            rx.text(" ", size="1"),
                            rx.button(
                                "Clear Filters",
                                variant="outline",
                                on_click=PointsState.clear_filters,
                            ),
                            spacing="1",
                        ),
                    ),
                    rx.spacer(),
                    rx.text(
                        f"Total: {PointsState.total_count} points",
                        color="gray",
                        size="2",
                    ),
                    spacing="3",
                    align="end",
                    width="100%",
                    wrap="wrap",
                ),
                spacing="2",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        # Bulk Operations Bar (appears when points selected)
        rx.cond(
            PointsState.selected_count > 0,
            rx.card(
                rx.hstack(
                    rx.text(
                        f"{PointsState.selected_count} points selected",
                        weight="medium",
                    ),
                    rx.spacer(),
                    rx.button(
                        "Enable MQTT",
                        color_scheme="green",
                        on_click=PointsState.bulk_enable_mqtt,
                    ),
                    rx.button(
                        "Disable MQTT",
                        color_scheme="red",
                        variant="outline",
                        on_click=PointsState.bulk_disable_mqtt,
                    ),
                    rx.button(
                        "Clear Selection",
                        variant="ghost",
                        on_click=PointsState.clear_selection,
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                padding="3",
                width="100%",
                background="rgba(59, 130, 246, 0.1)",
            ),
        ),
        # Points table
        point_table(),
        # Point editor dialog
        point_editor_dialog(),
        spacing="4",
        width="100%",
        on_mount=PointsState.load_points,
    )


def bulk_device_row(device: dict) -> rx.Component:
    """Row for bulk device configuration table."""
    # Standard equipment types
    standard_types = ["ahu", "vav", "fcu", "chiller", "chwp", "cwp", "ct", "boiler"]

    return rx.table.row(
        rx.table.cell(rx.text(device["deviceName"], size="2")),
        rx.table.cell(rx.text(device["ipAddress"], size="2")),
        rx.table.cell(rx.text(device["pointCount"], size="2")),
        rx.table.cell(
            rx.vstack(
                rx.select(
                    ["ahu", "vav", "fcu", "chiller", "chwp", "cwp", "ct", "boiler", "other"],
                    placeholder="Select type...",
                    value=rx.cond(
                        device["equipmentType"] != "",
                        rx.cond(
                            # If it's a standard type, show it; otherwise show "other"
                            (device["equipmentType"] == "ahu") |
                            (device["equipmentType"] == "vav") |
                            (device["equipmentType"] == "fcu") |
                            (device["equipmentType"] == "chiller") |
                            (device["equipmentType"] == "chwp") |
                            (device["equipmentType"] == "cwp") |
                            (device["equipmentType"] == "ct") |
                            (device["equipmentType"] == "boiler"),
                            device["equipmentType"],
                            "other",
                        ),
                        None,
                    ),
                    on_change=PointsState.set_device_equipment_type(device["id"]),
                    size="1",
                ),
                # Show custom input when "other" is selected or custom type is set
                rx.cond(
                    (device["equipmentType"] == "other") |
                    ((device["equipmentType"] != "") &
                     (device["equipmentType"] != "ahu") &
                     (device["equipmentType"] != "vav") &
                     (device["equipmentType"] != "fcu") &
                     (device["equipmentType"] != "chiller") &
                     (device["equipmentType"] != "chwp") &
                     (device["equipmentType"] != "cwp") &
                     (device["equipmentType"] != "ct") &
                     (device["equipmentType"] != "boiler")),
                    rx.input(
                        placeholder="Custom type...",
                        value=rx.cond(
                            device["equipmentType"] == "other",
                            "",
                            device["equipmentType"],
                        ),
                        on_change=PointsState.set_device_custom_equipment_type(device["id"]),
                        size="1",
                        width="120px",
                    ),
                ),
                spacing="1",
            ),
        ),
        rx.table.cell(
            rx.input(
                placeholder="e.g., 12",
                value=device["equipmentId"],
                on_change=PointsState.set_device_equipment_id(device["id"]),
                size="1",
                width="100px",
            ),
        ),
    )


def settings_tab() -> rx.Component:
    """Settings tab content."""
    return rx.vstack(
        # BACnet Configuration
        rx.card(
            rx.vstack(
                rx.heading("BACnet Configuration", size="4"),
                rx.form(
                    rx.vstack(
                        rx.hstack(
                            rx.vstack(
                                rx.text("BACnet IP Address", size="2"),
                                rx.input(
                                    name="bacnet_ip",
                                    placeholder="192.168.1.35",
                                    default_value=SettingsState.bacnet_ip,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Port", size="2"),
                                rx.input(
                                    name="bacnet_port",
                                    type="number",
                                    default_value=SettingsState.bacnet_port.to_string(),
                                    width="100px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Device ID", size="2"),
                                rx.input(
                                    name="bacnet_device_id",
                                    type="number",
                                    default_value=SettingsState.bacnet_device_id.to_string(),
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Discovery Timeout", size="2"),
                                rx.input(
                                    name="discovery_timeout",
                                    type="number",
                                    default_value=SettingsState.discovery_timeout.to_string(),
                                    width="100px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                        ),
                        rx.hstack(
                            rx.button("Save BACnet Config", type="submit"),
                            rx.cond(
                                SettingsState.bacnet_save_message != "",
                                rx.text(
                                    SettingsState.bacnet_save_message,
                                    color=rx.cond(
                                        SettingsState.bacnet_save_message.contains("saved"),
                                        "green",
                                        "red",
                                    ),
                                ),
                            ),
                            spacing="4",
                            align="center",
                        ),
                        spacing="4",
                    ),
                    on_submit=SettingsState.save_bacnet_config,
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        # MQTT Configuration
        rx.card(
            rx.vstack(
                rx.heading("MQTT Configuration", size="4"),
                rx.form(
                    rx.vstack(
                        rx.hstack(
                            rx.vstack(
                                rx.text("Broker", size="2"),
                                rx.input(
                                    name="mqtt_broker",
                                    placeholder="10.0.60.3",
                                    default_value=SettingsState.mqtt_broker,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Port", size="2"),
                                rx.input(
                                    name="mqtt_port",
                                    type="number",
                                    default_value=SettingsState.mqtt_port.to_string(),
                                    width="100px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Client ID", size="2"),
                                rx.input(
                                    name="mqtt_client_id",
                                    default_value=SettingsState.mqtt_client_id,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                        ),
                        rx.hstack(
                            rx.vstack(
                                rx.text("Username", size="2"),
                                rx.input(
                                    name="mqtt_username",
                                    default_value=SettingsState.mqtt_username,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Password", size="2"),
                                rx.input(
                                    name="mqtt_password",
                                    type="password",
                                    default_value=SettingsState.mqtt_password,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                        ),
                        rx.hstack(
                            rx.checkbox(
                                "Enable TLS",
                                name="mqtt_tls_enabled",
                                checked=SettingsState.mqtt_tls_enabled,
                                on_change=SettingsState.set_mqtt_tls_enabled,
                            ),
                            rx.checkbox(
                                "Skip Certificate Verification",
                                name="mqtt_tls_insecure",
                                checked=SettingsState.mqtt_tls_insecure,
                                on_change=SettingsState.set_mqtt_tls_insecure,
                            ),
                            spacing="4",
                        ),
                        # CA Certificate section - only show when TLS enabled and not insecure
                        rx.cond(
                            SettingsState.mqtt_tls_enabled & ~SettingsState.mqtt_tls_insecure,
                            rx.vstack(
                                rx.text("CA Certificate", size="2"),
                                rx.hstack(
                                    rx.upload(
                                        rx.button(
                                            rx.icon("upload", size=14),
                                            "Select CA Cert",
                                            variant="outline",
                                            size="2",
                                        ),
                                        id="ca_cert_upload",
                                        accept={".crt": ["application/x-x509-ca-cert"], ".pem": ["application/x-pem-file"], ".cer": ["application/pkix-cert"]},
                                        max_files=1,
                                        border="none",
                                        padding="0",
                                        on_drop=SettingsState.handle_ca_cert_upload(rx.upload_files(upload_id="ca_cert_upload")),
                                    ),
                                    rx.cond(
                                        SettingsState.ca_cert_filename != "",
                                        rx.hstack(
                                            rx.icon("check-circle", size=14, color="green"),
                                            rx.text(SettingsState.ca_cert_filename, size="2", color="green"),
                                            rx.button(
                                                rx.icon("x", size=12),
                                                variant="ghost",
                                                size="1",
                                                color_scheme="red",
                                                on_click=SettingsState.remove_ca_cert,
                                            ),
                                            spacing="2",
                                            align="center",
                                        ),
                                        rx.text("No certificate uploaded", size="2", color="gray"),
                                    ),
                                    spacing="3",
                                    align="center",
                                ),
                                rx.cond(
                                    SettingsState.ca_cert_upload_message != "",
                                    rx.text(
                                        SettingsState.ca_cert_upload_message,
                                        size="1",
                                        color=rx.cond(
                                            SettingsState.ca_cert_upload_message.contains("success"),
                                            "green",
                                            "red",
                                        ),
                                    ),
                                ),
                                spacing="2",
                                width="100%",
                            ),
                        ),
                        rx.hstack(
                            rx.button("Save MQTT Config", type="submit"),
                            rx.cond(
                                SettingsState.mqtt_save_message != "",
                                rx.text(
                                    SettingsState.mqtt_save_message,
                                    color=rx.cond(
                                        SettingsState.mqtt_save_message.contains("saved"),
                                        "green",
                                        "red",
                                    ),
                                ),
                            ),
                            spacing="4",
                            align="center",
                        ),
                        spacing="4",
                    ),
                    on_submit=SettingsState.save_mqtt_config,
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        # MQTT Override Subscription
        rx.card(
            rx.vstack(
                rx.heading("MQTT Override Subscription", size="4"),
                rx.text(
                    "Enable subscription for receiving setpoint overrides from ML/optimizer systems",
                    color="gray",
                    size="2",
                ),
                rx.form(
                    rx.vstack(
                        rx.checkbox(
                            "Enable Override Subscription",
                            name="subscribe_enabled",
                            checked=SettingsState.mqtt_subscribe_enabled,
                            on_change=SettingsState.set_mqtt_subscribe_enabled,
                        ),
                        rx.cond(
                            SettingsState.mqtt_subscribe_enabled,
                            rx.callout(
                                rx.vstack(
                                    rx.text("Override Flow:", weight="bold", size="2"),
                                    rx.hstack(
                                        rx.text("1.", size="2", color="gray"),
                                        rx.text("Worker subscribes to:", size="2"),
                                        rx.code("override/#"),
                                        spacing="1",
                                    ),
                                    rx.hstack(
                                        rx.text("2.", size="2", color="gray"),
                                        rx.text("ML publishes to:", size="2"),
                                        rx.code("override/<mqtt_topic>"),
                                        spacing="1",
                                    ),
                                    rx.hstack(
                                        rx.text("3.", size="2", color="gray"),
                                        rx.text("Worker writes value to BACnet point", size="2"),
                                        spacing="1",
                                    ),
                                    rx.hstack(
                                        rx.text("4.", size="2", color="gray"),
                                        rx.text("Only writable (R/W) points accept overrides", size="2"),
                                        spacing="1",
                                    ),
                                    rx.divider(),
                                    rx.text("Payload format:", weight="medium", size="2"),
                                    rx.code('{"value": 22.5, "priority": 8}', style={"font_size": "12px"}),
                                    rx.text("or just a raw value: 22.5", size="1", color="gray"),
                                    spacing="2",
                                ),
                                icon="info",
                                size="1",
                            ),
                        ),
                        rx.hstack(
                            rx.button("Save Settings", type="submit"),
                            rx.cond(
                                SettingsState.mqtt_subscription_message != "",
                                rx.text(
                                    SettingsState.mqtt_subscription_message,
                                    color=rx.cond(
                                        SettingsState.mqtt_subscription_message.contains("saved"),
                                        "green",
                                        "red",
                                    ),
                                ),
                            ),
                            spacing="4",
                            align="center",
                        ),
                        spacing="4",
                    ),
                    on_submit=SettingsState.save_mqtt_subscription,
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        # System Configuration
        rx.card(
            rx.vstack(
                rx.heading("System Configuration", size="4"),
                rx.hstack(
                    rx.vstack(
                        rx.text("Default Poll Interval (seconds)", size="2"),
                        rx.input(
                            type="number",
                            value=SettingsState.default_poll_interval.to_string(),
                            on_change=SettingsState.set_default_poll_interval,
                            width="100px",
                            min="1",
                            max="3600",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text(" ", size="2"),
                        rx.button(
                            "Apply to All MQTT Points",
                            color_scheme="green",
                            on_click=SettingsState.apply_poll_interval_to_all,
                        ),
                        spacing="1",
                    ),
                    rx.cond(
                        SettingsState.poll_interval_message != "",
                        rx.vstack(
                            rx.text(" ", size="2"),
                            rx.text(
                                SettingsState.poll_interval_message,
                                color="green",
                            ),
                            spacing="1",
                        ),
                    ),
                    spacing="4",
                    align="end",
                ),
                rx.divider(),
                rx.vstack(
                    rx.text("Timezone", size="2"),
                    rx.select(
                        [
                            "UTC",
                            "Asia/Kuala_Lumpur",
                            "Asia/Singapore",
                            "Asia/Hong_Kong",
                            "Asia/Tokyo",
                            "Asia/Seoul",
                            "Asia/Shanghai",
                            "Asia/Bangkok",
                            "Asia/Jakarta",
                            "Asia/Dubai",
                            "Europe/London",
                            "Europe/Paris",
                            "Europe/Berlin",
                            "Europe/Moscow",
                            "America/New_York",
                            "America/Chicago",
                            "America/Denver",
                            "America/Los_Angeles",
                            "America/Toronto",
                            "America/Vancouver",
                            "Australia/Sydney",
                            "Australia/Melbourne",
                            "Australia/Perth",
                            "Pacific/Auckland",
                        ],
                        value=SettingsState.timezone,
                        on_change=[SettingsState.set_timezone, SettingsState.save_timezone],
                        width="250px",
                    ),
                    rx.text("MQTT timestamps will be in UTC with timezone offset", size="1", color="gray"),
                    spacing="1",
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        # Password Change
        rx.card(
            rx.vstack(
                rx.heading("Change Password", size="4"),
                rx.form(
                    rx.vstack(
                        rx.hstack(
                            rx.vstack(
                                rx.text("Current Password", size="2"),
                                rx.input(
                                    name="current_password",
                                    type="password",
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("New Password", size="2"),
                                rx.input(
                                    name="new_password",
                                    type="password",
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Confirm Password", size="2"),
                                rx.input(
                                    name="confirm_password",
                                    type="password",
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Master PIN", size="2"),
                                rx.input(
                                    name="master_pin",
                                    type="password",
                                    placeholder="Required if set",
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                        ),
                        rx.hstack(
                            rx.button("Change Password", type="submit"),
                            rx.cond(
                                SettingsState.password_message != "",
                                rx.text(
                                    SettingsState.password_message,
                                    color=rx.cond(
                                        SettingsState.password_message.contains("success"),
                                        "green",
                                        "red",
                                    ),
                                ),
                            ),
                            spacing="4",
                            align="center",
                        ),
                        spacing="4",
                    ),
                    on_submit=SettingsState.change_password,
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        # Master PIN
        rx.card(
            rx.vstack(
                rx.heading("Master PIN", size="4"),
                rx.text(
                    "The Master PIN is required for password changes. Keep it safe.",
                    color="gray",
                    size="2",
                ),
                rx.form(
                    rx.vstack(
                        rx.hstack(
                            rx.vstack(
                                rx.text("Current PIN", size="2"),
                                rx.input(
                                    name="current_pin",
                                    type="password",
                                    placeholder="If already set",
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("New PIN (4-6 digits)", size="2"),
                                rx.input(
                                    name="new_pin",
                                    type="password",
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("Confirm PIN", size="2"),
                                rx.input(
                                    name="confirm_pin",
                                    type="password",
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                        ),
                        rx.hstack(
                            rx.button("Set Master PIN", type="submit"),
                            rx.cond(
                                SettingsState.pin_message != "",
                                rx.text(
                                    SettingsState.pin_message,
                                    color=rx.cond(
                                        SettingsState.pin_message.contains("success"),
                                        "green",
                                        "red",
                                    ),
                                ),
                            ),
                            spacing="4",
                            align="center",
                        ),
                        spacing="4",
                    ),
                    on_submit=SettingsState.set_master_pin,
                ),
                spacing="3",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        spacing="4",
        width="100%",
        on_mount=SettingsState.load_settings,
    )


def dashboard_page() -> rx.Component:
    """Main dashboard page with tabs."""
    return page_layout(
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Dashboard", value="dashboard"),
                rx.tabs.trigger("Discovery", value="discovery"),
                rx.tabs.trigger("Points", value="points"),
                rx.tabs.trigger("Settings", value="settings"),
            ),
            rx.tabs.content(
                dashboard_tab(),
                value="dashboard",
                padding_top="4",
            ),
            rx.tabs.content(
                discovery_tab(),
                value="discovery",
                padding_top="4",
            ),
            rx.tabs.content(
                points_tab(),
                value="points",
                padding_top="4",
            ),
            rx.tabs.content(
                settings_tab(),
                value="settings",
                padding_top="4",
            ),
            default_value="dashboard",
            width="100%",
        ),
    )

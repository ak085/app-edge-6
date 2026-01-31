"""Setup wizard page for first-time configuration."""

import reflex as rx

from ..state.settings_state import SettingsState


def setup_wizard_page() -> rx.Component:
    """Setup wizard for first-time configuration."""
    return rx.center(
        rx.vstack(
            rx.card(
                rx.vstack(
                    rx.heading("BacPipes Setup", size="7", weight="bold"),
                    rx.text(
                        "Welcome! Let's configure your BACnet-to-MQTT gateway.",
                        color="gray",
                        size="3",
                    ),
                    rx.divider(margin_y="4"),
                    # Step 1: BACnet Configuration
                    rx.vstack(
                        rx.hstack(
                            rx.badge("1", color="blue", radius="full"),
                            rx.text("BACnet Configuration", weight="medium"),
                            spacing="2",
                        ),
                        rx.form(
                            rx.vstack(
                                rx.hstack(
                                    rx.vstack(
                                        rx.text("BACnet IP Address", size="2"),
                                        rx.input(
                                            name="bacnet_ip",
                                            placeholder="192.168.1.35",
                                            width="200px",
                                        ),
                                        rx.text(
                                            "Enter your BACnet network interface IP",
                                            size="1",
                                            color="gray",
                                        ),
                                        spacing="1",
                                    ),
                                    rx.vstack(
                                        rx.text("Port", size="2"),
                                        rx.input(
                                            name="bacnet_port",
                                            type="number",
                                            default_value="47808",
                                            width="100px",
                                        ),
                                        spacing="1",
                                    ),
                                    rx.vstack(
                                        rx.text("Device ID", size="2"),
                                        rx.input(
                                            name="bacnet_device_id",
                                            type="number",
                                            default_value="3001234",
                                            width="150px",
                                        ),
                                        rx.text(
                                            "Unique ID for this gateway",
                                            size="1",
                                            color="gray",
                                        ),
                                        spacing="1",
                                    ),
                                    spacing="4",
                                ),
                                rx.button("Save BACnet Config", type="submit", width="100%"),
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
                            ),
                            on_submit=SettingsState.save_bacnet_config,
                        ),
                        spacing="3",
                        width="100%",
                        padding="4",
                        background=rx.color("gray", 2),
                        border_radius="8px",
                    ),
                    # Step 2: MQTT Configuration
                    rx.vstack(
                        rx.hstack(
                            rx.badge("2", color="blue", radius="full"),
                            rx.text("MQTT Configuration", weight="medium"),
                            spacing="2",
                        ),
                        rx.form(
                            rx.vstack(
                                rx.hstack(
                                    rx.vstack(
                                        rx.text("Broker Address", size="2"),
                                        rx.input(
                                            name="mqtt_broker",
                                            placeholder="10.0.60.3",
                                            width="200px",
                                        ),
                                        spacing="1",
                                    ),
                                    rx.vstack(
                                        rx.text("Port", size="2"),
                                        rx.input(
                                            name="mqtt_port",
                                            type="number",
                                            default_value="1883",
                                            width="100px",
                                        ),
                                        spacing="1",
                                    ),
                                    rx.vstack(
                                        rx.text("Client ID", size="2"),
                                        rx.input(
                                            name="mqtt_client_id",
                                            default_value="bacpipes_worker",
                                            width="200px",
                                        ),
                                        rx.text(
                                            "Shown on MQTT broker",
                                            size="1",
                                            color="gray",
                                        ),
                                        spacing="1",
                                    ),
                                    spacing="4",
                                ),
                                rx.hstack(
                                    rx.vstack(
                                        rx.text("Username (optional)", size="2"),
                                        rx.input(
                                            name="mqtt_username",
                                            width="200px",
                                        ),
                                        spacing="1",
                                    ),
                                    rx.vstack(
                                        rx.text("Password (optional)", size="2"),
                                        rx.input(
                                            name="mqtt_password",
                                            type="password",
                                            width="200px",
                                        ),
                                        spacing="1",
                                    ),
                                    spacing="4",
                                ),
                                rx.button("Save MQTT Config", type="submit", width="100%"),
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
                            ),
                            on_submit=SettingsState.save_mqtt_config,
                        ),
                        spacing="3",
                        width="100%",
                        padding="4",
                        background=rx.color("gray", 2),
                        border_radius="8px",
                    ),
                    # Continue button
                    rx.cond(
                        (SettingsState.bacnet_ip != "") & (SettingsState.mqtt_broker != ""),
                        rx.button(
                            "Continue to Dashboard",
                            on_click=rx.redirect("/"),
                            width="100%",
                            size="3",
                            color_scheme="green",
                        ),
                        rx.text(
                            "Complete both configurations to continue",
                            color="gray",
                            size="2",
                        ),
                    ),
                    spacing="4",
                    width="100%",
                    padding="6",
                ),
                width="600px",
                style={
                    "box_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                },
            ),
            spacing="4",
        ),
        min_height="100vh",
        background=rx.color("gray", 2),
        on_mount=SettingsState.load_settings,
    )

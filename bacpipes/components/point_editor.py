"""Point editor dialog for Haystack tagging and MQTT configuration."""

import reflex as rx

from ..state.points_state import PointsState


# Haystack dropdown options
POINT_FUNCTION_OPTIONS = [
    ("sensor", "sensor - Measures/reads values"),
    ("sp", "sp - Sets target/desired values"),
    ("cmd", "cmd - Commands/controls equipment"),
    ("synthetic", "synthetic - Computed/calculated data"),
]

QUANTITY_OPTIONS = [
    ("temp", "temp - Temperature"),
    ("humidity", "humidity - Humidity"),
    ("co2", "co2 - CO2 level"),
    ("flow", "flow - Flow rate"),
    ("pressure", "pressure - Pressure"),
    ("speed", "speed - Speed"),
    ("percent", "percent - Percentage"),
    ("power", "power - Power"),
    ("run", "run - Run status"),
    ("pos", "pos - Position"),
    ("level", "level - Level"),
    ("occupancy", "occupancy - Occupancy"),
    ("enthalpy", "enthalpy - Enthalpy"),
    ("dewpoint", "dewpoint - Dew point"),
    ("schedule", "schedule - Schedule (meta-data)"),
    ("calendar", "calendar - Calendar (meta-data)"),
    ("datetime", "datetime - Date/Time (meta-data)"),
    ("date", "date - Date (meta-data)"),
]

SUBJECT_OPTIONS = [
    ("", "-- Select --"),
    ("air", "air - Air"),
    ("water", "water - Water"),
    ("chilled-water", "chilled-water - Chilled water"),
    ("hot-water", "hot-water - Hot water"),
    ("steam", "steam - Steam"),
    ("refrig", "refrig - Refrigerant"),
    ("gas", "gas - Gas"),
]

LOCATION_OPTIONS = [
    ("", "-- Select --"),
    ("zone", "zone - Zone"),
    ("supply", "supply - Supply"),
    ("return", "return - Return"),
    ("outside", "outside - Outside"),
    ("mixed", "mixed - Mixed"),
    ("exhaust", "exhaust - Exhaust"),
    ("entering", "entering - Entering"),
    ("leaving", "leaving - Leaving"),
    ("coil", "coil - Coil"),
    ("filter", "filter - Filter"),
    ("economizer", "economizer - Economizer"),
]

QUALIFIER_OPTIONS = [
    ("actual", "actual - Current/measured value"),
    ("effective", "effective - Effective value"),
    ("min", "min - Minimum"),
    ("max", "max - Maximum"),
    ("nominal", "nominal - Nominal/design value"),
    ("alarm", "alarm - Alarm state"),
    ("enable", "enable - Enable state"),
    ("reset", "reset - Reset command"),
    ("manual", "manual - Manual mode"),
    ("auto", "auto - Auto mode"),
]

QOS_OPTIONS = [
    ("0", "0 - At most once"),
    ("1", "1 - At least once (recommended)"),
    ("2", "2 - Exactly once"),
]


def point_editor_dialog() -> rx.Component:
    """Dialog for editing point Haystack tags and MQTT configuration."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Edit Point Configuration"),
            rx.dialog.description(
                rx.hstack(
                    rx.text(PointsState.selected_point.get("deviceName", ""), color="gray"),
                    rx.text(" - "),
                    rx.text(PointsState.selected_point.get("bacnetName", ""), weight="medium"),  # Original BACnet name
                    spacing="1",
                ),
            ),
            rx.scroll_area(
                rx.vstack(
                    # Point Information (read-only)
                    point_info_section(),
                    rx.divider(),
                    # Haystack Decision Tree Guide
                    haystack_guide(),
                    rx.divider(),
                    # Bulk Configuration Display (read-only)
                    bulk_config_display(),
                    rx.divider(),
                    # Haystack Fields
                    haystack_fields_section(),
                    rx.divider(),
                    # MQTT Configuration
                    mqtt_config_section(),
                    # Save message
                    rx.cond(
                        PointsState.save_message != "",
                        rx.callout(
                            PointsState.save_message,
                            icon=rx.cond(
                                PointsState.save_message.contains("success"),
                                "check",
                                "alert-circle",
                            ),
                            color=rx.cond(
                                PointsState.save_message.contains("success"),
                                "green",
                                "red",
                            ),
                        ),
                    ),
                    spacing="4",
                    width="100%",
                    padding="2",
                ),
                type="always",
                scrollbars="vertical",
                style={"max_height": "70vh"},
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="outline",
                        on_click=PointsState.close_editor,
                    ),
                ),
                rx.button(
                    "Save Changes",
                    on_click=PointsState.save_point,
                    color_scheme="blue",
                ),
                spacing="3",
                justify="end",
                width="100%",
                padding_top="4",
            ),
            max_width="700px",
        ),
        open=PointsState.show_editor,
    )


def point_info_section() -> rx.Component:
    """Read-only point information section."""
    return rx.vstack(
        rx.text("Point Information", weight="bold", size="3"),
        rx.hstack(
            rx.vstack(
                rx.text("Object Type", size="1", color="gray"),
                rx.text(PointsState.selected_point.get("objectType", ""), size="2"),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Instance", size="1", color="gray"),
                rx.text(PointsState.selected_point.get("objectInstance", ""), size="2"),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Units", size="1", color="gray"),
                rx.text(
                    rx.cond(
                        PointsState.selected_point.get("units", "") != "",
                        PointsState.selected_point.get("units", ""),
                        "N/A",
                    ),
                    size="2",
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Device", size="1", color="gray"),
                rx.text(PointsState.selected_point.get("deviceName", ""), size="2"),
                spacing="1",
            ),
            spacing="6",
            width="100%",
        ),
        spacing="2",
        width="100%",
    )


def haystack_guide() -> rx.Component:
    """Haystack decision tree guide."""
    return rx.callout(
        rx.vstack(
            rx.text("Haystack Tagging Decision Tree:", weight="medium"),
            rx.text("1. What does it DO? -> Point Function", size="1"),
            rx.text("2. What does it measure/control? -> Quantity", size="1"),
            rx.text("3. What substance/medium? -> Subject", size="1"),
            rx.text("4. Where in the system? -> Location", size="1"),
            rx.text("5. What type/role? -> Qualifier", size="1"),
            spacing="1",
        ),
        icon="info",
        color="amber",
        size="1",
    )


def bulk_config_display() -> rx.Component:
    """Display bulk configuration values (read-only)."""
    return rx.vstack(
        rx.text("Bulk Configuration (Read-Only)", weight="bold", size="3", color="gray"),
        rx.hstack(
            rx.vstack(
                rx.text("Site ID", size="1", color="gray"),
                rx.text(
                    rx.cond(
                        PointsState.selected_point.get("siteId", "") != "",
                        PointsState.selected_point.get("siteId", ""),
                        "Not set",
                    ),
                    size="2",
                    style={"font_style": rx.cond(
                        PointsState.selected_point.get("siteId", "") != "",
                        "normal",
                        "italic",
                    )},
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Equipment Type", size="1", color="gray"),
                rx.text(
                    rx.cond(
                        PointsState.selected_point.get("equipmentType", "") != "",
                        PointsState.selected_point.get("equipmentType", ""),
                        "Not set",
                    ),
                    size="2",
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Equipment ID", size="1", color="gray"),
                rx.text(
                    rx.cond(
                        PointsState.selected_point.get("equipmentId", "") != "",
                        PointsState.selected_point.get("equipmentId", ""),
                        "Not set",
                    ),
                    size="2",
                ),
                spacing="1",
            ),
            spacing="6",
            width="100%",
        ),
        rx.text(
            "Set these values in the Bulk Configuration card on the Points page",
            size="1",
            color="gray",
        ),
        spacing="2",
        width="100%",
        padding="3",
        background="#F9FAFB",
        border_radius="8px",
    )


def haystack_fields_section() -> rx.Component:
    """Haystack tagging fields with dropdowns."""
    return rx.vstack(
        rx.text("Haystack Tags", weight="bold", size="3"),
        # Row 1: Point Function and Quantity
        rx.hstack(
            rx.vstack(
                rx.text("Point Function *", size="2"),
                rx.select(
                    [opt[1] for opt in POINT_FUNCTION_OPTIONS],
                    placeholder="Select function...",
                    value=PointsState.edit_point_function_display,
                    on_change=PointsState.set_point_function_from_display,
                    width="100%",
                ),
                rx.text("What does this point do?", size="1", color="gray"),
                spacing="1",
                flex="1",
            ),
            rx.vstack(
                rx.text("Quantity *", size="2"),
                rx.select(
                    [opt[1] for opt in QUANTITY_OPTIONS],
                    placeholder="Select quantity...",
                    value=PointsState.edit_quantity_display,
                    on_change=PointsState.set_quantity_from_display,
                    width="100%",
                ),
                rx.text("What does it measure/control?", size="1", color="gray"),
                spacing="1",
                flex="1",
            ),
            spacing="4",
            width="100%",
        ),
        # Row 2: Subject and Location
        rx.hstack(
            rx.vstack(
                rx.text("Subject", size="2"),
                rx.select(
                    [opt[1] for opt in SUBJECT_OPTIONS],
                    placeholder="Select subject...",
                    value=PointsState.edit_subject_display,
                    on_change=PointsState.set_subject_from_display,
                    width="100%",
                ),
                rx.text("What substance/medium?", size="1", color="gray"),
                spacing="1",
                flex="1",
            ),
            rx.vstack(
                rx.text("Location", size="2"),
                rx.select(
                    [opt[1] for opt in LOCATION_OPTIONS],
                    placeholder="Select location...",
                    value=PointsState.edit_location_display,
                    on_change=PointsState.set_location_from_display,
                    width="100%",
                ),
                rx.text("Where in the system?", size="1", color="gray"),
                spacing="1",
                flex="1",
            ),
            spacing="4",
            width="100%",
        ),
        # Row 3: Qualifier
        rx.hstack(
            rx.vstack(
                rx.text("Qualifier *", size="2"),
                rx.select(
                    [opt[1] for opt in QUALIFIER_OPTIONS],
                    placeholder="Select qualifier...",
                    value=PointsState.edit_qualifier_display,
                    on_change=PointsState.set_qualifier_from_display,
                    width="100%",
                ),
                rx.text("What type/role?", size="1", color="gray"),
                spacing="1",
                flex="1",
            ),
            rx.vstack(
                rx.text("Display Name", size="2"),
                rx.input(
                    placeholder="e.g., AHU-12 Supply Air Temperature",
                    value=PointsState.edit_dis,
                    on_change=PointsState.set_edit_dis,
                    width="100%",
                ),
                rx.text("Human-readable description", size="1", color="gray"),
                spacing="1",
                flex="1",
            ),
            spacing="4",
            width="100%",
        ),
        # Haystack Name Preview
        rx.box(
            rx.vstack(
                rx.text("Generated Haystack Name", size="2", weight="medium"),
                rx.text(
                    PointsState.haystack_preview,
                    size="2",
                    style={"font_family": "monospace"},
                    color=rx.cond(
                        PointsState.haystack_preview.contains("Complete"),
                        "gray",
                        "green",
                    ),
                ),
                spacing="1",
            ),
            padding="3",
            background="#F0FDF4",
            border_radius="4px",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


def mqtt_config_section() -> rx.Component:
    """MQTT configuration section."""
    return rx.vstack(
        rx.text("MQTT Configuration", weight="bold", size="3"),
        # Publish toggle
        rx.hstack(
            rx.switch(
                checked=PointsState.edit_mqtt_publish,
                on_change=PointsState.set_edit_mqtt_publish,
            ),
            rx.vstack(
                rx.text("Publish to MQTT Broker", size="2"),
                rx.text("Enable to publish this point's values to MQTT", size="1", color="gray"),
                spacing="0",
            ),
            spacing="3",
            align="center",
        ),
        # Writable toggle
        rx.hstack(
            rx.switch(
                checked=PointsState.edit_is_writable,
                on_change=PointsState.set_edit_is_writable,
            ),
            rx.vstack(
                rx.text("Point is Writable", size="2"),
                rx.text("Allow BACnet write commands to this point", size="1", color="gray"),
                spacing="0",
            ),
            spacing="3",
            align="center",
        ),
        # Write Validation (only when writable)
        rx.cond(
            PointsState.edit_is_writable,
            rx.vstack(
                rx.text("Write Validation", size="2", weight="medium"),
                rx.hstack(
                    rx.vstack(
                        rx.text("Min Value", size="1"),
                        rx.input(
                            type="number",
                            placeholder="e.g., 15",
                            value=PointsState.edit_min_value,
                            on_change=PointsState.set_edit_min_value,
                            width="120px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Max Value", size="1"),
                        rx.input(
                            type="number",
                            placeholder="e.g., 30",
                            value=PointsState.edit_max_value,
                            on_change=PointsState.set_edit_max_value,
                            width="120px",
                        ),
                        spacing="1",
                    ),
                    spacing="4",
                ),
                rx.cond(
                    (PointsState.edit_min_value != "") | (PointsState.edit_max_value != ""),
                    rx.text(
                        f"Write commands will be validated: {PointsState.edit_min_value} to {PointsState.edit_max_value}",
                        size="1",
                        color="green",
                    ),
                    rx.text(
                        "No limits configured - any value will be accepted",
                        size="1",
                        color="amber",
                    ),
                ),
                spacing="2",
                padding="3",
                background="#FFFBEB",
                border_radius="4px",
                width="100%",
            ),
        ),
        # Poll Interval and QoS
        rx.hstack(
            rx.vstack(
                rx.text("Poll Interval (seconds)", size="2"),
                rx.input(
                    type="number",
                    value=PointsState.edit_poll_interval,
                    on_change=PointsState.set_edit_poll_interval,
                    width="120px",
                    min="1",
                    max="3600",
                ),
                rx.text("1-3600 seconds", size="1", color="gray"),
                spacing="1",
            ),
            rx.vstack(
                rx.text("QoS Level", size="2"),
                rx.select(
                    [opt[1] for opt in QOS_OPTIONS],
                    value=PointsState.edit_qos_display,
                    on_change=PointsState.set_qos_from_display,
                    width="200px",
                ),
                rx.text("Message delivery guarantee", size="1", color="gray"),
                spacing="1",
            ),
            spacing="4",
            width="100%",
        ),
        # MQTT Topic Preview
        rx.box(
            rx.vstack(
                rx.text("MQTT Topic", size="2", weight="medium"),
                rx.text(
                    rx.cond(
                        PointsState.mqtt_topic_preview != "",
                        PointsState.mqtt_topic_preview,
                        "Complete Haystack tags to generate topic",
                    ),
                    size="2",
                    style={"font_family": "monospace"},
                    color=rx.cond(
                        PointsState.mqtt_topic_preview != "",
                        "blue",
                        "gray",
                    ),
                ),
                spacing="1",
            ),
            padding="3",
            background="#EFF6FF",
            border_radius="4px",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )

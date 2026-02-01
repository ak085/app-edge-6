"""Point table component for points tab."""

import reflex as rx

from ..state.points_state import PointsState


def pagination_controls() -> rx.Component:
    """Pagination controls for the points table."""
    return rx.hstack(
        rx.hstack(
            rx.button(
                rx.icon("chevrons-left", size=14),
                variant="outline",
                size="1",
                on_click=PointsState.first_page,
                disabled=~PointsState.has_prev_page,
            ),
            rx.button(
                rx.icon("chevron-left", size=14),
                variant="outline",
                size="1",
                on_click=PointsState.prev_page,
                disabled=~PointsState.has_prev_page,
            ),
            spacing="1",
        ),
        rx.text(
            PointsState.page_display,
            size="2",
            color="gray",
        ),
        rx.hstack(
            rx.button(
                rx.icon("chevron-right", size=14),
                variant="outline",
                size="1",
                on_click=PointsState.next_page,
                disabled=~PointsState.has_next_page,
            ),
            spacing="1",
        ),
        spacing="3",
        align="center",
        justify="center",
        width="100%",
        padding_top="3",
    )


def point_table() -> rx.Component:
    """Table displaying BACnet points with Haystack tags."""
    return rx.card(
        rx.vstack(
            rx.cond(
                PointsState.is_loading,
                rx.center(
                    rx.spinner(size="3"),
                    padding="8",
                ),
                rx.cond(
                    PointsState.points.length() > 0,
                    rx.vstack(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell(
                                        rx.checkbox(
                                            checked=PointsState.selected_count == PointsState.points.length(),
                                            on_change=PointsState.toggle_select_all,
                                        ),
                                        width="40px",
                                    ),
                                    rx.table.column_header_cell("Point Name"),
                                    rx.table.column_header_cell("Value"),
                                    rx.table.column_header_cell("Type"),
                                    rx.table.column_header_cell("MQTT Topic"),
                                    rx.table.column_header_cell("Status"),
                                    rx.table.column_header_cell("Actions"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    PointsState.points,
                                    point_row,
                                ),
                            ),
                            width="100%",
                        ),
                        pagination_controls(),
                        spacing="2",
                        width="100%",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon("database", size=48, color="gray"),
                            rx.text("No points found", color="gray"),
                            rx.text(
                                "Run a discovery scan to find BACnet points",
                                color="gray",
                                size="2",
                            ),
                            spacing="2",
                            align="center",
                        ),
                        padding="8",
                    ),
                ),
            ),
            width="100%",
        ),
        padding="4",
        width="100%",
    )


def point_row(point: dict) -> rx.Component:
    """Single row in the points table."""
    return rx.table.row(
        # Checkbox
        rx.table.cell(
            rx.checkbox(
                checked=PointsState.selected_point_ids.contains(point["id"]),
                on_change=PointsState.toggle_point_selection(point["id"]),
            ),
            width="40px",
        ),
        # Point Name with subtitle
        rx.table.cell(
            rx.vstack(
                rx.text(
                    rx.cond(
                        point["dis"] != "",
                        point["dis"],
                        point["pointName"],
                    ),
                    size="2",
                    weight="medium",
                ),
                rx.hstack(
                    rx.text(
                        rx.match(
                            point["objectType"],
                            ("analog-input", "AI"),
                            ("analog-output", "AO"),
                            ("analog-value", "AV"),
                            ("binary-input", "BI"),
                            ("binary-output", "BO"),
                            ("binary-value", "BV"),
                            point["objectType"],
                        ),
                        size="1",
                        color="gray",
                    ),
                    rx.text(":", size="1", color="gray"),
                    rx.text(point["objectInstance"], size="1", color="gray"),
                    rx.text("-", size="1", color="gray"),
                    rx.text(point["deviceName"], size="1", color="gray"),
                    spacing="1",
                ),
                spacing="0",
            ),
        ),
        # Value with units
        rx.table.cell(
            rx.hstack(
                rx.text(
                    rx.cond(
                        point["lastValue"] != "",
                        point["lastValue"],
                        "-",
                    ),
                    weight="medium",
                ),
                rx.cond(
                    point["units"] != "",
                    rx.text(point["units"], size="1", color="gray"),
                ),
                spacing="1",
            ),
        ),
        # Type with R/W indicator
        rx.table.cell(
            rx.vstack(
                rx.badge(
                    point["objectType"],
                    color=rx.match(
                        point["objectType"],
                        ("analog-input", "blue"),
                        ("analog-output", "green"),
                        ("analog-value", "purple"),
                        ("binary-input", "orange"),
                        ("binary-output", "red"),
                        "gray",
                    ),
                    size="1",
                ),
                rx.cond(
                    point["isWritable"],
                    rx.text("R/W", size="1", color="orange"),
                    rx.text("Read-only", size="1", color="gray"),
                ),
                spacing="1",
            ),
        ),
        # MQTT Topic
        rx.table.cell(
            rx.cond(
                point["mqttTopic"] != "",
                rx.hstack(
                    rx.text(
                        point["mqttTopic"],
                        size="1",
                        style={"font_family": "monospace"},
                        max_width="200px",
                        overflow="hidden",
                        text_overflow="ellipsis",
                    ),
                    spacing="1",
                ),
                rx.text("Not configured", size="1", color="gray", style={"font_style": "italic"}),
            ),
        ),
        # Status
        rx.table.cell(
            rx.vstack(
                rx.badge(
                    rx.cond(point["mqttPublish"], "Publishing", "Disabled"),
                    color=rx.cond(point["mqttPublish"], "green", "gray"),
                    size="1",
                ),
                rx.cond(
                    point["mqttPublish"] & point["isWritable"],
                    rx.hstack(
                        rx.icon("arrow-down-circle", size=12, color="orange"),
                        rx.text("Override", size="1", color="orange"),
                        spacing="1",
                    ),
                ),
                spacing="1",
                align="start",
            ),
        ),
        # Actions
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    rx.switch(
                        checked=point["mqttPublish"],
                        on_change=PointsState.toggle_mqtt_publish(point["id"]),
                        size="1",
                    ),
                    content="Enable/disable MQTT publishing",
                ),
                rx.tooltip(
                    rx.button(
                        rx.icon("pencil", size=14),
                        variant="ghost",
                        size="1",
                        on_click=PointsState.open_editor(point["id"]),
                    ),
                    content="Edit point configuration",
                ),
                spacing="2",
            ),
        ),
    )

"""Status card component for dashboard."""

import reflex as rx
from typing import Union


def status_card(
    title: str,
    value: Union[str, int, rx.Var],
    icon: str,
    color: Union[str, rx.Var] = "blue",
) -> rx.Component:
    """Status card showing a metric with icon.

    Args:
        title: Card title/label
        value: The value to display
        icon: Lucide icon name
        color: Color scheme (blue, green, purple, red, orange)
    """
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(title, size="2", color="gray"),
                rx.text(
                    value,
                    size="6",
                    weight="bold",
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            rx.box(
                rx.icon(icon, size=24),
                padding="3",
                border_radius="full",
                background=rx.match(
                    color,
                    ("green", "#D1FAE5"),
                    ("red", "#FEE2E2"),
                    ("purple", "#EDE9FE"),
                    ("orange", "#FFEDD5"),
                    "#DBEAFE",  # default blue
                ),
                color=rx.match(
                    color,
                    ("green", "#059669"),
                    ("red", "#DC2626"),
                    ("purple", "#7C3AED"),
                    ("orange", "#EA580C"),
                    "#2563EB",  # default blue
                ),
            ),
            width="100%",
            align="center",
        ),
        padding="4",
        min_width="200px",
        flex="1",
        style={
            "border": "1px solid #E5E7EB",
            "box_shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.1)",
        },
    )

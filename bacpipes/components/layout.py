"""Layout component for BacPipes pages."""

import reflex as rx

from ..state.auth_state import AuthState
from ..state.dashboard_state import DashboardState
from ..state.worker_state import WorkerState


def header_bar() -> rx.Component:
    """Header bar with title and action buttons."""
    return rx.hstack(
        rx.hstack(
            rx.heading("BacPipes", size="5", weight="bold"),
            rx.badge(
                WorkerState.mqtt_status,
                color=rx.cond(
                    WorkerState.mqtt_status == "connected",
                    "green",
                    "orange",
                ),
            ),
            spacing="3",
            align="center",
        ),
        rx.spacer(),
        rx.hstack(
            rx.color_mode.button(size="2", variant="outline"),
            rx.button(
                rx.icon("refresh-cw", size=16),
                "Refresh",
                variant="outline",
                size="2",
                on_click=DashboardState.load_dashboard,
                loading=DashboardState.is_loading,
            ),
            rx.button(
                rx.icon("rotate-cw", size=16),
                "Restart Worker",
                variant="outline",
                color_scheme="orange",
                size="2",
                on_click=WorkerState.restart_worker,
                loading=WorkerState.is_restarting,
            ),
            rx.button(
                rx.icon("log-out", size=16),
                "Logout",
                variant="ghost",
                size="2",
                on_click=AuthState.logout,
            ),
            spacing="2",
        ),
        width="100%",
        padding="4",
        background=rx.color("gray", 1),
        border_bottom="1px solid var(--gray-5)",
        position="sticky",
        top="0",
        z_index="100",
    )


def page_layout(content: rx.Component) -> rx.Component:
    """Main page layout with header."""
    return rx.box(
        rx.cond(
            AuthState.is_authenticated,
            rx.vstack(
                header_bar(),
                rx.box(
                    content,
                    padding="4",
                    width="100%",
                    max_width="1400px",
                    margin_x="auto",
                ),
                width="100%",
                min_height="100vh",
                background=rx.color("gray", 2),
                spacing="0",
            ),
            # Show loading while checking auth - redirect handled by check_session
            rx.center(
                rx.spinner(size="3"),
                min_height="100vh",
                background=rx.color("gray", 2),
            ),
        ),
        on_mount=[
            AuthState.check_session,
            WorkerState.load_worker_status,
        ],
    )

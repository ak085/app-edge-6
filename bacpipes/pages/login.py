"""Login page for BacPipes."""

import reflex as rx

from ..state.auth_state import AuthState


def login_page() -> rx.Component:
    """Login page component."""
    return rx.center(
        rx.vstack(
            rx.card(
                rx.vstack(
                    rx.heading("BacPipes", size="7", weight="bold"),
                    rx.text(
                        "BACnet-to-MQTT Edge Gateway",
                        color="gray",
                        size="2",
                    ),
                    rx.divider(margin_y="4"),
                    rx.form(
                        rx.vstack(
                            rx.text("Username", size="2", weight="medium"),
                            rx.input(
                                name="username",
                                placeholder="admin",
                                width="100%",
                                size="3",
                            ),
                            rx.text("Password", size="2", weight="medium"),
                            rx.input(
                                name="password",
                                type="password",
                                placeholder="Enter password",
                                width="100%",
                                size="3",
                            ),
                            rx.cond(
                                AuthState.login_error != "",
                                rx.callout(
                                    AuthState.login_error,
                                    icon="circle-alert",
                                    color="red",
                                    size="1",
                                ),
                            ),
                            rx.button(
                                rx.cond(
                                    AuthState.is_loading,
                                    rx.spinner(size="2"),
                                    rx.text("Sign In"),
                                ),
                                type="submit",
                                width="100%",
                                size="3",
                                disabled=AuthState.is_loading,
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        on_submit=AuthState.login,
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                    padding="6",
                ),
                width="350px",
                style={
                    "box_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
                },
            ),
            rx.text(
                "Default: admin / admin",
                color="gray",
                size="1",
            ),
            spacing="4",
        ),
        min_height="100vh",
        background=rx.color("gray", 2),
    )

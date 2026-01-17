"""BacPipes - Main Reflex Application."""

import reflex as rx

from .pages.login import login_page
from .pages.dashboard import dashboard_page
from .pages.setup_wizard import setup_wizard_page
from .state.settings_state import SettingsState


# Create the Reflex app
app = rx.App(
    theme=rx.theme(
        appearance="light",
        has_background=True,
        radius="medium",
        accent_color="blue",
    ),
    stylesheets=[
        # Custom styles
    ],
)

# Add pages
app.add_page(login_page, route="/login", title="Login - BacPipes")
app.add_page(dashboard_page, route="/", title="BacPipes")
app.add_page(setup_wizard_page, route="/setup", title="Setup - BacPipes")


# Lifespan task for worker
async def start_worker_task():
    """Start the BACnet/MQTT worker as a background task."""
    import asyncio
    from .worker.polling import start_worker

    # Wait a bit for the app to fully start
    await asyncio.sleep(2)

    # Start worker
    try:
        await start_worker()
    except Exception as e:
        print(f"Worker error: {e}")


# Register the worker as a lifespan task
# This runs when the backend starts
app.register_lifespan_task(start_worker_task)

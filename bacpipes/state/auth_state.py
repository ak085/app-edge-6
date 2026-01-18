"""Authentication state for BacPipes."""

from datetime import datetime, timedelta
from typing import Optional
import reflex as rx
from sqlmodel import select

from ..models.system_settings import SystemSettings
from ..utils.auth import verify_password, hash_password, verify_pin, hash_pin


# Session duration: 3 hours
SESSION_DURATION_HOURS = 3


class AuthState(rx.State):
    """Authentication state management."""

    # Session state (stored server-side)
    _is_logged_in: bool = False
    _expires_at: Optional[datetime] = None
    _username: str = ""

    # Form state
    login_error: str = ""
    is_loading: bool = False

    @rx.var
    def is_authenticated(self) -> bool:
        """Check if user is authenticated and session is valid."""
        if not self._is_logged_in:
            return False
        if self._expires_at is None:
            return False
        if datetime.now() > self._expires_at:
            self._is_logged_in = False
            return False
        return True

    @rx.var
    def username(self) -> str:
        """Get current username."""
        return self._username if self.is_authenticated else ""

    def check_session(self):
        """Check if session is valid on page load."""
        if not self.is_authenticated:
            return rx.redirect("/login")

    async def login(self, form_data: dict):
        """Handle login form submission."""
        self.is_loading = True
        self.login_error = ""
        yield

        username = form_data.get("username", "").strip()
        password = form_data.get("password", "")

        if not username or not password:
            self.login_error = "Username and password are required"
            self.is_loading = False
            yield
            return

        # Get settings from database
        with rx.session() as session:
            settings = session.exec(select(SystemSettings)).first()

            if not settings:
                # Create default settings if not exists
                settings = SystemSettings(
                    adminUsername="admin",
                    adminPasswordHash="",
                )
                session.add(settings)
                session.commit()
                session.refresh(settings)

            # Verify credentials
            if username != settings.adminUsername:
                self.login_error = "Invalid username or password"
                self.is_loading = False
                yield
                return

            if not verify_password(password, settings.adminPasswordHash):
                self.login_error = "Invalid username or password"
                self.is_loading = False
                yield
                return

            # Create session
            self._is_logged_in = True
            self._expires_at = datetime.now() + timedelta(hours=SESSION_DURATION_HOURS)
            self._username = username
            self.is_loading = False

            yield rx.redirect("/")

    def logout(self):
        """Clear session and redirect to login."""
        self._is_logged_in = False
        self._expires_at = None
        self._username = ""
        return rx.redirect("/login")

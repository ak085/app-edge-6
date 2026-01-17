"""Authentication utilities using bcrypt."""

import bcrypt

# Default password for admin user (used when hash is empty)
DEFAULT_PASSWORD = "admin"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash.

    If the hash is empty, verify against default password "admin".
    """
    if not password_hash:
        # Empty hash means use default password
        return password == DEFAULT_PASSWORD

    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def hash_pin(pin: str) -> str:
    """Hash a PIN using bcrypt."""
    return hash_password(pin)


def verify_pin(pin: str, pin_hash: str) -> bool:
    """Verify a PIN against a bcrypt hash."""
    if not pin_hash:
        return False  # No PIN set

    try:
        return bcrypt.checkpw(pin.encode("utf-8"), pin_hash.encode("utf-8"))
    except Exception:
        return False

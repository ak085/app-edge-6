"""Reflex configuration for BacPipes."""

import os
import reflex as rx

# Get database URL from environment or use default
db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://anatoli@localhost:5432/bacpipes"
)

config = rx.Config(
    app_name="bacpipes",
    db_url=db_url,
)

#!/bin/bash
set -e

echo "=== BacPipes Startup ==="
echo "Database: $DATABASE_URL"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until pg_isready -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432} -U ${DB_USER:-anatoli} -q 2>/dev/null; do
    echo "  PostgreSQL not ready, waiting..."
    sleep 2
done
echo "PostgreSQL is ready!"

# Initialize Reflex if needed
if [ ! -f ".web/.initialized" ]; then
    echo "Initializing Reflex app..."
    reflex init --loglevel warning || true
    touch .web/.initialized
fi

# Initialize database tables
echo "Initializing database..."
reflex db init || true

# Run database migrations
echo "Running database migrations..."
reflex db migrate || true

# Initialize default data if tables are empty
echo "Checking default data..."
python3 << 'INITDB'
import os
import sys

# Add app to path
sys.path.insert(0, '/app')

from sqlmodel import Session, create_engine, select, text

db_url = os.environ.get("DATABASE_URL", "postgresql://anatoli@localhost:5432/bacpipes")
engine = create_engine(db_url)

try:
    with Session(engine) as session:
        # Check if tables exist first
        result = session.exec(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'SystemSettings'
            )
        """))
        table_exists = result.first()[0]

        if not table_exists:
            print("Tables not yet created, will be created by Reflex")
        else:
            from bacpipes.models.system_settings import SystemSettings
            from bacpipes.models.mqtt_config import MqttConfig

            # Check if SystemSettings exists
            settings = session.exec(select(SystemSettings)).first()
            if not settings:
                print("Creating default SystemSettings...")
                settings = SystemSettings(
                    adminUsername="admin",
                    adminPasswordHash="",
                    timezone="Asia/Kuala_Lumpur",
                )
                session.add(settings)
                session.commit()
                print("  Created!")
            else:
                print("SystemSettings exists")

            # Check if MqttConfig exists
            mqtt = session.exec(select(MqttConfig)).first()
            if not mqtt:
                print("Creating default MqttConfig...")
                mqtt = MqttConfig(
                    port=1883,
                    clientId="bacpipes_worker",
                )
                session.add(mqtt)
                session.commit()
                print("  Created!")
            else:
                print("MqttConfig exists")

    print("Database initialization complete!")
except Exception as e:
    print(f"Database init note: {e}")
INITDB

echo "=== Starting BacPipes ==="
exec "$@"

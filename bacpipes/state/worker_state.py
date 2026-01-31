"""Worker state for BacPipes."""

import os
from datetime import datetime
from typing import Optional
import reflex as rx
from sqlmodel import select

from ..models.mqtt_config import MqttConfig


# Global worker process reference (set by lifespan task)
_worker_process = None


def set_worker_process(process):
    """Set the worker process reference (called from lifespan task)."""
    global _worker_process
    _worker_process = process


def get_worker_process():
    """Get the worker process reference."""
    return _worker_process


class WorkerState(rx.State):
    """Worker control state."""

    # Worker status
    worker_running: bool = False
    worker_status: str = "unknown"

    # Statistics
    last_poll_time: Optional[str] = None
    messages_published: int = 0

    # MQTT connection
    mqtt_status: str = "disconnected"
    mqtt_broker: str = ""

    # Restart state
    restart_message: str = ""
    is_restarting: bool = False

    async def load_worker_status(self):
        """Load worker status from database."""
        with rx.session() as session:
            mqtt_config = session.exec(select(MqttConfig)).first()
            if mqtt_config:
                self.mqtt_status = mqtt_config.connectionStatus or "disconnected"
                self.mqtt_broker = f"{mqtt_config.broker}:{mqtt_config.port}" if mqtt_config.broker else "Not configured"
                if mqtt_config.lastDataFlow:
                    self.last_poll_time = mqtt_config.lastDataFlow.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    self.last_poll_time = None

        # Check if worker process is running
        worker = get_worker_process()
        if worker:
            self.worker_running = worker.is_alive() if hasattr(worker, 'is_alive') else True
            self.worker_status = "running" if self.worker_running else "stopped"
        else:
            self.worker_running = False
            self.worker_status = "not started"

    async def restart_worker(self):
        """Request worker restart."""
        if self.is_restarting:
            return

        self.is_restarting = True
        self.restart_message = "Restarting worker..."
        yield

        try:
            # The worker checks for config changes periodically
            # We can trigger a restart by touching a restart flag file
            restart_flag = "/tmp/bacpipes_worker_restart"

            with open(restart_flag, "w") as f:
                f.write(str(datetime.now().timestamp()))

            self.restart_message = "Worker restart requested. Changes will take effect within 10 seconds."
            yield rx.toast.success("Worker restart requested")

        except Exception as e:
            self.restart_message = f"Failed to restart worker: {str(e)}"
            yield rx.toast.error(f"Failed: {str(e)}")

        finally:
            self.is_restarting = False

        # Reload status after a short delay
        import asyncio
        await asyncio.sleep(2)
        await self.load_worker_status()

    def clear_restart_message(self):
        """Clear the restart message."""
        self.restart_message = ""

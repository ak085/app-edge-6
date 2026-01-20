"""BacPipes CLI entry point.

Usage:
    python -m bacpipes          # Full app with web UI
    python -m bacpipes --headless  # Worker only, no web UI
"""

import argparse
import asyncio
import sys


def main():
    """Main entry point for BacPipes."""
    parser = argparse.ArgumentParser(
        description="BacPipes - BACnet-to-MQTT Edge Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m bacpipes              Run full app with web UI
    python -m bacpipes --headless   Run worker only (no web UI)
    python -m bacpipes --version    Show version
        """
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run worker only without web UI",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    parser.add_argument(
        "--db-url",
        type=str,
        default="postgresql://bacpipes@localhost:5432/bacpipes",
        help="Database URL (default: postgresql://bacpipes@localhost:5432/bacpipes)",
    )

    args = parser.parse_args()

    if args.version:
        from . import __version__
        print(f"BacPipes version {__version__}")
        sys.exit(0)

    if args.headless:
        # Run worker only, no web UI
        print("Starting BacPipes in headless mode (worker only)...")
        print(f"Database: {args.db_url}")

        import os
        os.environ["DATABASE_URL"] = args.db_url

        from .worker.polling import start_worker

        try:
            asyncio.run(start_worker())
        except KeyboardInterrupt:
            print("\nShutdown requested")
            sys.exit(0)
    else:
        # Run full Reflex app with web UI
        print("Starting BacPipes with web UI...")
        print("Open http://localhost:3000 in your browser")

        try:
            # Import and run Reflex
            import reflex as rx
            from . import bacpipes  # noqa: F401

            rx.utils.console.print(
                "[bold green]BacPipes[/bold green] - BACnet-to-MQTT Edge Gateway"
            )

            # Start Reflex
            from reflex.reflex import cli
            cli()

        except ImportError as e:
            print(f"Error importing Reflex: {e}")
            print("Make sure Reflex is installed: pip install reflex")
            sys.exit(1)
        except Exception as e:
            print(f"Error starting app: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

"""
Job Processor - Polls database for discovery jobs and executes them

This runs continuously in the background, checking for new discovery jobs
every 5 seconds and executing them automatically.
"""

import time
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from discovery import run_discovery

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'bacpipes'),
        user=os.getenv('DB_USER', 'anatoli'),
        password=""
    )

def poll_and_process_jobs():
    """Main loop - poll database for new jobs and process them"""

    print("=== BacPipes Discovery Job Processor Started ===")
    print(f"Database: {os.getenv('DB_HOST', 'postgres')}:{os.getenv('DB_PORT', '5432')}")
    print(f"Polling for new discovery jobs every 5 seconds...")
    print("=" * 60)

    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Find jobs with status="running"
            cursor.execute(
                '''SELECT id, "ipAddress", port, timeout, "deviceId"
                   FROM "DiscoveryJob"
                   WHERE status = 'running'
                   ORDER BY "startedAt" ASC
                   LIMIT 1'''
            )

            job = cursor.fetchone()
            conn.close()

            if job:
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Found job: {job['id']}")
                print(f"  Executing discovery...")

                try:
                    # Execute discovery
                    run_discovery(job['id'])
                    print(f"  ✅ Job {job['id']} completed successfully")
                except Exception as e:
                    print(f"  ❌ Job {job['id']} failed: {e}")

            # Wait 5 seconds before checking again
            time.sleep(5)

        except KeyboardInterrupt:
            print("\n\nShutting down job processor...")
            break
        except Exception as e:
            print(f"Error in job processor: {e}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    poll_and_process_jobs()

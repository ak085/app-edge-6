"""
BacPipes Remote API - Central Data Collection Endpoint
Receives sensor data from multiple BacPipes site installations
"""

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DB_HOST = os.getenv('DB_HOST', 'remote-timescaledb')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'bacnet_central')
DB_USER = os.getenv('DB_USER', 'anatoli')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
API_KEY = os.getenv('API_KEY', 'your-secret-api-key')

app = FastAPI(
    title="BacPipes Remote API",
    description="Central data collection endpoint for multi-site BacPipes deployments",
    version="1.0.0"
)

# Database connection pool
conn = None

def get_db_connection():
    """Get database connection"""
    global conn
    if conn is None or conn.closed:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    return conn

# Pydantic models
class SensorReading(BaseModel):
    """Single sensor reading"""
    time: datetime
    device_id: int
    device_name: str
    object_type: str
    object_instance: int
    haystack_name: str
    dis: Optional[str] = None
    value: float
    units: str
    quality: str = "good"
    equipment_type: Optional[str] = None

class BulkReadings(BaseModel):
    """Bulk sensor readings from a site"""
    site_name: str
    readings: List[SensorReading]

class SiteRegistration(BaseModel):
    """Site registration request"""
    site_name: str
    location: str
    timezone: str = "UTC"

# Authentication
async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key from request header"""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key

# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)}
        )

# Site registration endpoint
@app.post("/api/sites/register")
async def register_site(
    site: SiteRegistration,
    api_key: str = Depends(verify_api_key)
):
    """Register a new site"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sites (site_name, location, timezone)
                VALUES (%s, %s, %s)
                ON CONFLICT (site_name)
                DO UPDATE SET location = EXCLUDED.location, timezone = EXCLUDED.timezone
                RETURNING site_id, api_key
            """, (site.site_name, site.location, site.timezone))
            result = cur.fetchone()
            conn.commit()

        return {
            "success": True,
            "site_id": result[0],
            "message": f"Site '{site.site_name}' registered successfully"
        }
    except Exception as e:
        logger.error(f"Site registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bulk data ingestion endpoint
@app.post("/api/data/bulk")
async def ingest_bulk_data(
    data: BulkReadings,
    api_key: str = Depends(verify_api_key)
):
    """Ingest bulk sensor readings from a site"""
    try:
        conn = get_db_connection()

        # Get site_id
        with conn.cursor() as cur:
            cur.execute("SELECT site_id FROM sites WHERE site_name = %s", (data.site_name,))
            result = cur.fetchone()
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Site '{data.site_name}' not found. Please register first."
                )
            site_id = result[0]

        # Prepare batch insert
        values = [
            (
                reading.time,
                site_id,
                data.site_name,
                reading.device_id,
                reading.device_name,
                reading.object_type,
                reading.object_instance,
                reading.haystack_name,
                reading.dis,
                reading.value,
                reading.units,
                reading.quality,
                reading.equipment_type
            )
            for reading in data.readings
        ]

        # Batch insert
        with conn.cursor() as cur:
            execute_batch(cur, """
                INSERT INTO sensor_readings (
                    time, site_id, site_name, device_id, device_name,
                    object_type, object_instance, haystack_name, dis,
                    value, units, quality, equipment_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, values)

            # Update last_sync timestamp
            cur.execute(
                "UPDATE sites SET last_sync = NOW() WHERE site_id = %s",
                (site_id,)
            )

            conn.commit()

        logger.info(f"Ingested {len(data.readings)} readings from site '{data.site_name}'")

        return {
            "success": True,
            "site_name": data.site_name,
            "readings_count": len(data.readings),
            "message": f"Successfully ingested {len(data.readings)} readings"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk data ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get site statistics
@app.get("/api/sites/stats")
async def get_site_statistics(api_key: str = Depends(verify_api_key)):
    """Get statistics for all sites"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM site_statistics ORDER BY site_name")
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in cur.fetchall()]

        return {
            "success": True,
            "sites": results,
            "total_sites": len(results)
        }
    except Exception as e:
        logger.error(f"Failed to get site statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get data quality by site
@app.get("/api/quality/by-site")
async def get_data_quality(api_key: str = Depends(verify_api_key)):
    """Get data quality statistics by site"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM data_quality_by_site ORDER BY site_name")
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in cur.fetchall()]

        return {
            "success": True,
            "quality_stats": results
        }
    except Exception as e:
        logger.error(f"Failed to get data quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/")
async def root():
    """API information"""
    return {
        "name": "BacPipes Remote API",
        "version": "1.0.0",
        "description": "Central data collection endpoint for multi-site BacPipes deployments",
        "endpoints": {
            "health": "GET /health",
            "register_site": "POST /api/sites/register",
            "ingest_bulk": "POST /api/data/bulk",
            "site_stats": "GET /api/sites/stats",
            "data_quality": "GET /api/quality/by-site"
        },
        "authentication": "Required: X-API-Key header"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

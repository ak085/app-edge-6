# BacPipes Worker Dockerfile
# Python 3.10 BACnet MQTT Publishing Service

FROM python:3.10-slim

# Install system dependencies for psycopg2 and BACnet
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 bacpipes && \
    chown -R bacpipes:bacpipes /app

USER bacpipes

# Health check - verify database connection
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run both job processor (for discovery) and MQTT publisher
CMD ["sh", "-c", "python -u job_processor.py & python -u mqtt_publisher.py"]

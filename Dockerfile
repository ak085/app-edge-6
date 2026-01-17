# BacPipes - BACnet-to-MQTT Edge Gateway
# Single Python container with Reflex app

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (required by Reflex for frontend build)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install bun (faster package manager used by Reflex)
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY rxconfig.py .
COPY bacpipes/ ./bacpipes/

# Create .web directory for Reflex
RUN mkdir -p .web

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV REFLEX_ENV_MODE=prod

# Expose ports (3000=frontend, 8000=backend API)
EXPOSE 3000 8000

# Entrypoint script to handle initialization and startup
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["reflex", "run", "--env", "prod"]

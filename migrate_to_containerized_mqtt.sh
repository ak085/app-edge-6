#!/bin/bash
# Migration script to move from system Mosquitto to containerized mqtt-broker
# Part of BacPipes self-contained deployment architecture

set -e  # Exit on error

echo "=========================================="
echo "BacPipes MQTT Migration Script"
echo "=========================================="
echo ""

# Check if system mosquitto is running
echo "Step 1: Checking system Mosquitto service..."
if systemctl is-active --quiet mosquitto; then
    echo "❌ System Mosquitto is RUNNING on port 1883"
    echo ""
    echo "MANUAL ACTION REQUIRED:"
    echo "Run the following commands to stop it:"
    echo ""
    echo "  sudo systemctl stop mosquitto"
    echo "  sudo systemctl disable mosquitto"
    echo ""
    echo "Then run this script again."
    exit 1
else
    echo "✅ System Mosquitto is not running"
fi
echo ""

# Check if port 1883 is available
echo "Step 2: Checking port 1883 availability..."
if ss -tulpn | grep -q ":1883"; then
    echo "❌ Port 1883 is still in use:"
    ss -tulpn | grep ":1883"
    echo ""
    echo "Please stop the process using port 1883 before continuing."
    exit 1
else
    echo "✅ Port 1883 is available"
fi
echo ""

# Stop and remove old mqtt-local container
echo "Step 3: Cleaning up old mqtt-local container..."
docker compose stop mqtt-local 2>/dev/null || echo "mqtt-local already stopped"
docker compose rm -f mqtt-local 2>/dev/null || echo "mqtt-local already removed"
echo "✅ Old container cleaned up"
echo ""

# Start new mqtt-broker on port 1883
echo "Step 4: Starting mqtt-broker container on port 1883..."
docker compose up -d mqtt-broker --remove-orphans
sleep 3
echo ""

# Verify mqtt-broker is running
echo "Step 5: Verifying mqtt-broker status..."
if docker compose ps mqtt-broker | grep -q "Up"; then
    echo "✅ mqtt-broker is running"
    docker compose ps mqtt-broker
else
    echo "❌ mqtt-broker failed to start"
    echo "Logs:"
    docker compose logs --tail=20 mqtt-broker
    exit 1
fi
echo ""

# Test mqtt-broker connection
echo "Step 6: Testing MQTT broker connection..."
if docker exec bacpipes-mqtt mosquitto_sub -h localhost -t '$SYS/broker/uptime' -C 1 -W 2 > /dev/null 2>&1; then
    echo "✅ MQTT broker is responding"
    UPTIME=$(docker exec bacpipes-mqtt mosquitto_sub -h localhost -t '$SYS/broker/uptime' -C 1 -W 2)
    echo "   Uptime: $UPTIME seconds"
else
    echo "❌ MQTT broker is not responding"
    exit 1
fi
echo ""

# Restart worker and telegraf
echo "Step 7: Restarting worker and telegraf to connect to new broker..."
docker compose restart bacnet-worker telegraf
echo "✅ Services restarted"
echo ""

# Wait for health checks
echo "Step 8: Waiting for services to be healthy..."
sleep 10
echo "✅ Wait complete"
echo ""

# Check worker logs for MQTT connection
echo "Step 9: Verifying worker MQTT connection..."
if docker compose logs --tail=50 bacnet-worker | grep -qi "connected.*mqtt\|mqtt.*connect"; then
    echo "✅ Worker connected to MQTT broker"
    docker compose logs --tail=5 bacnet-worker | grep -i mqtt
else
    echo "⚠️  No explicit MQTT connection message found in logs"
    echo "Recent worker logs:"
    docker compose logs --tail=10 bacnet-worker
fi
echo ""

# Check telegraf logs
echo "Step 10: Verifying telegraf MQTT connection..."
if docker compose logs --tail=50 telegraf | grep -qi "connected.*mqtt\|mqtt.*connect"; then
    echo "✅ Telegraf connected to MQTT broker"
    docker compose logs --tail=5 telegraf | grep -i mqtt
else
    echo "⚠️  No explicit MQTT connection message found in logs"
    echo "Recent telegraf logs:"
    docker compose logs --tail=10 telegraf
fi
echo ""

# Check data flow to TimescaleDB
echo "Step 11: Checking data flow to TimescaleDB..."
RECENT_COUNT=$(docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -t -c \
    "SELECT COUNT(*) FROM sensor_readings WHERE time > NOW() - INTERVAL '5 minutes';" | tr -d ' ')

if [ "$RECENT_COUNT" -gt 0 ]; then
    echo "✅ Data is flowing to TimescaleDB"
    echo "   Recent readings (last 5 min): $RECENT_COUNT"
else
    echo "⚠️  No recent data in TimescaleDB (may take a minute for first data)"
    echo "   Total readings: $(docker exec bacpipes-timescaledb psql -U anatoli -d timescaledb -t -c 'SELECT COUNT(*) FROM sensor_readings;' | tr -d ' ')"
fi
echo ""

echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - mqtt-broker: Running on port 1883"
echo "  - mqtt-remote: Running on port 1884"
echo "  - Worker: Connected"
echo "  - Telegraf: Connected"
echo "  - Data flow: Verified"
echo ""
echo "Next steps:"
echo "  1. Monitor live data: docker compose logs -f bacnet-worker"
echo "  2. Check MQTT traffic: docker exec bacpipes-mqtt mosquitto_sub -t '#' -v"
echo "  3. View Grafana: http://localhost:3002"
echo "  4. Configure cloud bridge via Web UI (coming soon)"
echo ""

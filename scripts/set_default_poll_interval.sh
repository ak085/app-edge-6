#!/bin/bash
# Script to set default poll interval for all MQTT-published points
# Usage: ./set_default_poll_interval.sh <interval_in_seconds>

INTERVAL=${1:-30}

echo "========================================="
echo "Set Default Poll Interval for All Points"
echo "========================================="
echo ""
echo "This will update ALL enabled points to use polling interval: ${INTERVAL} seconds"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Updating poll intervals in frontend database..."

# Update the points configuration (assuming it's in postgres on port 5434)
docker compose exec -T postgres psql -U anatoli -d bacpipes <<EOF
UPDATE points
SET "pollInterval" = ${INTERVAL}
WHERE "mqttPublish" = true;

SELECT COUNT(*) as updated_points FROM points WHERE "mqttPublish" = true;
EOF

echo ""
echo "✅ Poll interval updated to ${INTERVAL} seconds for all enabled points!"
echo ""
echo "Note: The MQTT worker will pick up this change on its next configuration refresh."
echo "To apply immediately, restart the worker:"
echo "  docker compose restart bacnet-worker"

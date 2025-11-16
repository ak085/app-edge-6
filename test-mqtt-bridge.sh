#!/bin/bash
# Test MQTT Bridge Functionality
# Tests message forwarding from mqtt-local to mqtt-remote

echo "=========================================="
echo "MQTT Bridge Test"
echo "=========================================="
echo ""

# Test 1: Check broker status
echo "Test 1: Checking broker status..."
echo "-------------------------------------------"
if docker compose ps mqtt-broker | grep -q "Up"; then
    echo "✅ mqtt-broker is running (port 1883)"
else
    echo "❌ mqtt-broker is NOT running"
    exit 1
fi

if docker compose ps mqtt-remote | grep -q "Up"; then
    echo "✅ mqtt-remote is running (port 1884)"
else
    echo "❌ mqtt-remote is NOT running"
    exit 1
fi
echo ""

# Test 2: Publish to local, subscribe on remote (bridge forwarding)
echo "Test 2: Testing bridge forwarding..."
echo "-------------------------------------------"
echo "Publishing test message to mqtt-broker..."

# Start subscriber on remote broker in background
docker exec bacpipes-mqtt-remote mosquitto_sub -t "klcc/#" -C 1 -W 5 > /tmp/mqtt_bridge_test.txt 2>&1 &
SUBSCRIBER_PID=$!

# Wait a moment for subscriber to connect
sleep 1

# Publish to local broker
docker exec bacpipes-mqtt mosquitto_pub -t "klcc/test" -m "Hello from mqtt-broker"

# Wait for subscriber to receive message
sleep 2

# Check if message was received
if grep -q "Hello from mqtt-broker" /tmp/mqtt_bridge_test.txt; then
    echo "✅ Message successfully bridged from mqtt-broker to mqtt-remote"
    cat /tmp/mqtt_bridge_test.txt
else
    echo "❌ Message NOT received on mqtt-remote"
    cat /tmp/mqtt_bridge_test.txt
fi
echo ""

# Test 3: Check if bacnet-worker can connect
echo "Test 3: Testing worker MQTT connection..."
echo "-------------------------------------------"
if docker compose logs bacnet-worker | grep -q "Connected to MQTT broker"; then
    echo "✅ bacnet-worker connected to MQTT broker"
elif docker compose logs bacnet-worker | grep -q "connection refused"; then
    echo "❌ bacnet-worker cannot connect to MQTT broker"
else
    echo "⚠️  bacnet-worker connection status unclear, checking logs..."
    docker compose logs bacnet-worker | tail -5
fi
echo ""

# Test 4: Check if telegraf can connect
echo "Test 4: Testing telegraf MQTT connection..."
echo "-------------------------------------------"
if docker compose logs telegraf | grep -q "Connected to MQTT broker"; then
    echo "✅ telegraf connected to MQTT broker"
elif docker compose logs telegraf | grep -q "connection refused"; then
    echo "❌ telegraf cannot connect to MQTT broker"
else
    echo "⚠️  telegraf connection status unclear, checking logs..."
    docker compose logs telegraf | tail -5
fi
echo ""

# Cleanup
rm -f /tmp/mqtt_bridge_test.txt
kill $SUBSCRIBER_PID 2>/dev/null || true

echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "Summary:"
echo "- mqtt-broker (port 1883): Local edge broker"
echo "- mqtt-remote (port 1884): Remote/cloud broker"
echo "- Bridge: Forwards klcc/# and menara/# topics"
echo ""
echo "Next steps:"
echo "1. Monitor live data: docker compose logs bacnet-worker -f"
echo "2. Subscribe to remote broker: docker exec bacpipes-mqtt-remote mosquitto_sub -t '#' -v"
echo "3. View bridge logs: docker compose logs mqtt-broker | grep bridge"
echo ""

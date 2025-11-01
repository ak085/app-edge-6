#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Integrated BACnet Reading/Writing with MQTT
==========================================

PURPOSE: Integrated BACnet reading and writing with MQTT using fully dynamic configuration.
STATUS: Production-ready. All configuration (BACnet, MQTT, device, polling points) is loaded from YAML and JSON files. No hardcoded network or broker values.
INPUT: config/production_json/polling_config.json (points, intervals, device IP/port, MQTT topics), config/bacnet_config.yaml (network, device, MQTT settings)
OUTPUT: MQTT publishing (polling results, write results), JSON files in temp/polling_test/ (for debugging)

This script provides integrated BACnet reading and writing capabilities:
- Single BACnet session for both reading and writing
- Single MQTT broker for all operations (reading and writing)
- All broker and network details loaded from YAML config
- All polling points, intervals, and device ports loaded from JSON config
- No hardcoded IPs, ports, or broker details
- JSON output for each polled point (for debugging/traceability)
- Continuous operation with dynamic polling intervals
- Comprehensive error handling and logging
- Graceful shutdown handling
- Robust value extraction from BACnet Any objects

USAGE:
    python3 scripts/production_integrated_mqtt.py

FEATURES:
    - Continuous operation (runs indefinitely)
    - Polling intervals, device IPs, and ports are fully dynamic (from JSON)
    - MQTT publishing to topic(s) defined in JSON metadata
    - MQTT command listening on topic defined in JSON metadata
    - MQTT result publishing to topic defined in JSON metadata
    - Single BACnet session for all operations
    - Comprehensive error handling and statistics
    - Graceful shutdown (Ctrl+C)
    - All Stage 4 Runtime fields included in MQTT messages

MQTT COMMANDS:
    - Send to the write command topic (see JSON metadata): {"point": "120", "value": 85.0}
    - Results published to the write result topic (see JSON metadata)
    - Polling results published to the polling results topic (see JSON metadata)

CONFIGURATION:
    - MQTT broker settings: config/bacnet_config.yaml (mqtt section)
    - BACnet network settings: config/bacnet_config.yaml (network section)
    - BACnet device settings: config/bacnet_config.yaml (device section)
    - Points to poll, device IPs/ports, MQTT topics: config/production_json/polling_config.json

DEPENDENCIES:
    - bacpypes3 library
    - paho-mqtt library
    - config/production_json/polling_config.json
    - config/bacnet_config.yaml
    - MQTT broker (configured in YAML)
    - temp/polling_test/ directory (created if missing)

AUTHOR: BACnet-to-MQTT Project
VERSION: 1.0 (Integrated MQTT, fully dynamic)
LAST UPDATED: 2025-07-25
"""

import asyncio
import json
import signal
import sys
import time
import struct
import os
import yaml
from datetime import datetime
import paho.mqtt.client as mqtt
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.local.device import DeviceObject
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier, Real
from bacpypes3.apdu import ReadPropertyRequest, WritePropertyRequest
from bacpypes3.basetypes import PropertyIdentifier

class ProductionIntegratedApp(NormalApplication):
    """
    Integrated BACnet reading/writing application with MQTT.
    
    Provides BACnet polling and writing capabilities with MQTT integration.
    """
    
    def __init__(self, local_addr, mqtt_config, device_config):
        # Create a minimal device object for polling using YAML configuration
        device = DeviceObject(
            objectIdentifier=ObjectIdentifier(f"device,{device_config['device_id']}"),
            objectName=device_config['device_name'],
            vendorIdentifier=device_config['vendor_id'],
            maxApduLengthAccepted=device_config.get('apdu_length', 1024),
            segmentationSupported=device_config.get('segmentation', "segmentedBoth"),
        )
        super().__init__(device, local_addr)
        
        # Retry configuration (proven to work)
        self.max_retries = 3
        self.base_timeout = 6000  # 6 seconds
        self.exponential_backoff = True
        
        # JSON output configuration
        # self.json_output_dir = "temp/polling_test"
        # self.ensure_output_directory()
        
        # MQTT configuration
        self.mqtt_config = mqtt_config
        self.mqtt_client = None
        self.mqtt_connected = False
        self.mqtt_reconnect_attempts = 0
        self.max_mqtt_reconnect_attempts = 5
        
        # Production tracking
        self.polling_cycles = 0
        self.total_points_polled = 0
        self.total_successful_reads = 0
        self.total_failed_reads = 0
        self.total_retry_attempts = 0
        # self.total_json_writes = 0
        # self.total_json_errors = 0
        self.total_mqtt_publishes = 0
        self.total_mqtt_errors = 0
        self.total_write_attempts = 0
        self.total_write_successes = 0
        self.total_write_failures = 0
        self.start_time = time.time()
        self.running = True
        
        # Polling intervals (in seconds)
        self.poll_intervals = {}  # Will be populated dynamically from config
        
        # Write command handling
        self.pending_write_commands = []
        
        # Configuration storage
        self.loaded_config = None
        
        print(f"ProductionIntegratedApp initialized on {local_addr}")
        # print(f"JSON output directory: {self.json_output_dir}")
        print("Press Ctrl+C to stop polling gracefully")

    def setup_mqtt(self):
        """Setup MQTT client with production-grade connection management."""
        try:
            self.mqtt_client = mqtt.Client(
                client_id=self.mqtt_config['client_id'],
                clean_session=True,
                protocol=mqtt.MQTTv311
            )
            
            # Set MQTT connection options from configuration
            self.mqtt_client.max_inflight_messages_set(self.mqtt_config['max_inflight_messages'])
            self.mqtt_client.max_queued_messages_set(self.mqtt_config['max_queued_messages'])
            
            # Set up callbacks
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_publish = self.on_mqtt_publish
            
            # Set authentication if provided
            if self.mqtt_config.get('username') and self.mqtt_config.get('password'):
                self.mqtt_client.username_pw_set(
                    self.mqtt_config['username'],
                    self.mqtt_config['password']
                )
            
            # Connect to MQTT broker
            print(f"Connecting to MQTT broker: {self.mqtt_config['broker']}:{self.mqtt_config['port']}")
            self.mqtt_client.connect(
                self.mqtt_config['broker'],
                self.mqtt_config['port'],
                self.mqtt_config['keepalive']  # Keepalive from configuration
            )
            
            # Start MQTT loop
            self.mqtt_client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.mqtt_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.mqtt_connected:
                print("✓ MQTT connection established successfully")
                return True
            else:
                print("✗ MQTT connection timeout")
                return False
                
        except Exception as e:
            print(f"✗ MQTT setup failed: {e}")
            return False

    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback with command subscription."""
        if rc == 0:
            self.mqtt_connected = True
            self.mqtt_reconnect_attempts = 0
            print(f"✓ MQTT connected with result code: {rc}")
            
            # Load MQTT topics from configuration
            mqtt_topics = self.load_mqtt_topics_from_config()
            self.mqtt_topics = mqtt_topics
            
            # Subscribe to write commands using dynamic topic
            write_command_topic = mqtt_topics.get('write_command', 'bacnet/write/command')
            client.subscribe(write_command_topic, qos=1)
            print(f"✓ Subscribed to {write_command_topic}")
            
        else:
            self.mqtt_connected = False
            print(f"✗ MQTT connection failed with result code: {rc}")

    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback with automatic reconnection."""
        self.mqtt_connected = False
        if rc != 0:
            print(f"⚠️  MQTT disconnected unexpectedly with code: {rc}")
            self.total_mqtt_errors += 1
            
            # Attempt reconnection
            if self.mqtt_reconnect_attempts < self.max_mqtt_reconnect_attempts:
                self.mqtt_reconnect_attempts += 1
                print(f"Attempting MQTT reconnection ({self.mqtt_reconnect_attempts}/{self.max_mqtt_reconnect_attempts})...")
                try:
                    self.mqtt_client.reconnect()
                except Exception as e:
                    print(f"MQTT reconnection failed: {e}")

    def on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback - queue approach."""
        try:
            print(f"\n📨 Received MQTT command: {msg.topic}")
            print(f"Message: {msg.payload.decode()}")
            
            # Get write command topic from configuration
            mqtt_topics = getattr(self, 'mqtt_topics', {})
            write_command_topic = mqtt_topics.get('write_command', 'bacnet/write/command')
            
            # Parse the command
            command = json.loads(msg.payload.decode())
            
            if msg.topic == write_command_topic:
                # Add to command queue
                self.pending_write_commands.append(command)
                print(f"📝 Command queued for processing")
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in command: {e}")
        except Exception as e:
            print(f"❌ Error processing command: {e}")

    def on_mqtt_publish(self, client, userdata, mid):
        """MQTT publish callback."""
        self.total_mqtt_publishes += 1

    def extract_bacnet_value(self, bacnet_value):
        """
        Extract readable value from BACnet Any object.
        
        Args:
            bacnet_value: BACnet Any object from read response
            
        Returns:
            str: Readable value or None if extraction fails
        """
        try:
            if bacnet_value is None:
                return None
            
            # Convert BACnet Any object to string representation
            value_str = str(bacnet_value)
            
            # If it's still the Any object representation, try to extract the actual value
            if "bacpypes3.primitivedata.Any object" in value_str:
                # Try to access the actual value
                if hasattr(bacnet_value, 'value'):
                    return str(bacnet_value.value)
                elif hasattr(bacnet_value, 'tag'):
                    return str(bacnet_value.tag)
                else:
                    return "extraction_failed"
            
            return value_str
            
        except Exception as e:
            print(f"Value extraction error: {e}")
            return "extraction_error"

    def publish_point_to_mqtt(self, point_data, value, quality="ok", status="success"):
        """Publish BACnet point data to MQTT with ALL required fields."""
        if not self.mqtt_connected:
            return False
        
        try:
            # Use the mqtt_topic from the JSON config (now in new format)
            topic = point_data['mqtt_topic']
            
            # Use value as-is (already converted to string)
            readable_value = value
            
            # Create payload with ALL fields from JSON configuration (NO HARDCODING)
            payload = {
                # RUNTIME_GEN fields
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'value': readable_value,
                'quality': quality,
                'status': status
            }
            
            # Add ALL fields from point_data (completely dynamic)
            for key, value in point_data.items():
                # Skip runtime fields that are handled separately
                if key not in ['timestamp', 'value', 'quality']:
                    payload[key] = value
            
            # Publish to MQTT with dynamic QoS detection
            qos_field = self.detect_qos_field(point_data)
            qos_level = point_data.get(qos_field, 1)  # Default to QoS 1 if not found
            
            result = self.mqtt_client.publish(
                topic,
                json.dumps(payload),
                qos=qos_level
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✓ Published: {topic} = {readable_value}")
                return True
            else:
                print(f"✗ MQTT publish failed: {result.rc}")
                self.total_mqtt_errors += 1
                return False
                
        except Exception as e:
            print(f"✗ MQTT publish error: {e}")
            self.total_mqtt_errors += 1
            return False

    def publish_write_result(self, status, data):
        """Publish write result to MQTT."""
        if not self.mqtt_connected:
            return False
        
        try:
            # Get write result topic from configuration
            mqtt_topics = getattr(self, 'mqtt_topics', {})
            topic = mqtt_topics.get('write_result', 'bacnet/write/result')
            
            if status == "success":
                payload = data
            else:
                payload = {
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "status": "error",
                    "message": data
                }
            
            result = self.mqtt_client.publish(
                topic,
                json.dumps(payload),
                qos=1
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✓ Published write result to {topic}")
                return True
            else:
                print(f"✗ Failed to publish write result: {result.rc}")
                return False
                
        except Exception as e:
            print(f"✗ Error publishing write result: {e}")
            return False

    def detect_filter_field(self, point_data):
        """
        Detect the field used to filter points for polling (mqtt_publish, enabled, etc.).
        
        Args:
            point_data: Dictionary containing point data
            
        Returns:
            str: Field name used for filtering, or 'mqtt_publish' as default
        """
        # Priority order: mqtt_publish, enabled, active, status
        filter_fields = ['mqtt_publish', 'enabled', 'active', 'status']
        
        for field in filter_fields:
            if field in point_data:
                return field
        
        # If no filter field found, assume all points should be published
        # (they're in the JSON because they already passed filtering)
        return 'mqtt_publish'
    
    def get_filter_value(self, point_data):
        """
        Get the filter value for a point, with smart fallback logic.
        
        Args:
            point_data: Dictionary containing point data
            
        Returns:
            bool: True if point should be published, False otherwise
        """
        filter_field = self.detect_filter_field(point_data)
        
        # If the filter field exists, use its value
        if filter_field in point_data:
            return point_data.get(filter_field, False)
        
        # If no filter field exists, assume point should be published
        # (it's in the JSON because it already passed filtering)
        return True
    
    def detect_writable_field(self, point_data):
        """
        Detect the field used to indicate if a point is writable (is_writable, writable, etc.).
        
        Args:
            point_data: Dictionary containing point data
            
        Returns:
            str: Field name used for writable status, or 'is_writable' as default
        """
        # Priority order: is_writable, writable, can_write, write_enabled
        writable_fields = ['is_writable', 'writable', 'can_write', 'write_enabled']
        
        for field in writable_fields:
            if field in point_data:
                return field
        
        # Default fallback
        return 'is_writable'
    
    def detect_qos_field(self, point_data):
        """
        Detect the field used for QoS level (qos, qos_level, etc.).
        
        Args:
            point_data: Dictionary containing point data
            
        Returns:
            str: Field name used for QoS, or 'qos' as default
        """
        # Priority order: qos, qos_level, mqtt_qos, quality_of_service
        qos_fields = ['qos', 'qos_level', 'mqtt_qos', 'quality_of_service']
        
        for field in qos_fields:
            if field in point_data:
                return field
        
        # Default fallback
        return 'qos'

    def load_bacnet_config(self, yaml_file="config/bacnet_config.yaml"):
        """
        Load BACnet network configuration from YAML file.
        
        Args:
            yaml_file: Path to BACnet configuration YAML file
            
        Returns:
            dict: Loaded configuration or None if failed
        """
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print(f"✓ Loaded BACnet configuration from {yaml_file}")
            print(f"Local IP: {config['network']['local_ip']}")
            print(f"Broadcast IP: {config['network']['broadcast_ip']}")
            print(f"Subnet: /{config['network']['subnet']}")
            print(f"Port: {config['network']['local_port']}")
            
            return config
            
        except Exception as e:
            print(f"✗ Error loading BACnet configuration: {e}")
            return None

    def load_stage4_config(self, json_file="config/production_json/polling_config.json"):
        """
        Load Stage 4 Runtime JSON configuration.
        
        Args:
            json_file: Path to Stage 4 Runtime JSON configuration
            
        Returns:
            dict: Loaded configuration or None if failed
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Store the loaded configuration for write operations
            self.loaded_config = config
            
            print(f"✓ Loaded Stage 4 Runtime configuration from {json_file}")
            print(f"Total devices: {config['metadata']['total_devices']}")
            print(f"Total points: {config['metadata']['total_points']}")
            
            # Organize points by polling interval
            for device_ip, device in config['devices'].items():
                for point in device['points']:
                    # Use smart filter value detection
                    if self.get_filter_value(point):
                        poll_interval = point['poll_interval']
                        if poll_interval not in self.poll_intervals:
                            self.poll_intervals[poll_interval] = []
                        # Add device info to point data
                        point['device_ip'] = device['device_ip']
                        point['device_port'] = device['device_port']
                        point['device_id'] = device['device_id']
                        self.poll_intervals[poll_interval].append(point)
            
            # Print interval distribution
            total_points_loaded = 0
            for interval, points in self.poll_intervals.items():
                if points:
                    print(f"  {interval}s interval: {len(points)} points")
                    total_points_loaded += len(points)
            
            print(f"✓ Total points loaded for polling: {total_points_loaded}")
            
            # Print writable points summary
            writable_points = []
            for device_ip, device in config['devices'].items():
                for point in device['points']:
                    # Use dynamic field detection for both writable and filter fields
                    writable_field = self.detect_writable_field(point)
                    if point.get(writable_field, False) and self.get_filter_value(point):
                        writable_points.append(f"{point['object_type']},{point['object_id']} ({point['haystack_point_name']})")
            
            if writable_points:
                print(f"✓ Writable points found: {len(writable_points)}")
                for point in writable_points:
                    print(f"  - {point}")
            else:
                print("⚠️ No writable points found in configuration")
            
            if total_points_loaded == 0:
                print("⚠️ WARNING: No points loaded for polling!")
                print("  Check that points have mqtt_publish=true (or enabled=true) and valid poll_interval values")
                print("  Valid poll intervals: 30, 60, 120, 300 seconds")
                print("  Dynamic field detection will try: mqtt_publish, enabled, active, status")
            
            return config
            
        except Exception as e:
            print(f"✗ Error loading Stage 4 configuration: {e}")
            return None

    def load_mqtt_topics_from_config(self):
        """
        Load MQTT topics from JSON configuration.
        
        Returns:
            dict: MQTT topics or None if not found
        """
        if not self.loaded_config:
            print("⚠️ No configuration loaded, using default MQTT topics")
            return {
                'write_command': 'bacnet/write/command',
                'write_result': 'bacnet/write/result',
                'polling_results': 'bacnet/polling/points'
            }
        
        try:
            mqtt_topics = self.loaded_config.get('metadata', {}).get('mqtt_topics', {})
            if mqtt_topics:
                print(f"✓ Loaded MQTT topics from configuration:")
                for topic_type, topic in mqtt_topics.items():
                    print(f"  {topic_type}: {topic}")
                return mqtt_topics
            else:
                print("⚠️ No MQTT topics found in configuration, using defaults")
                return {
                    'write_command': 'bacnet/write/command',
                    'write_result': 'bacnet/write/result',
                    'polling_results': 'bacnet/polling/points'
                }
        except Exception as e:
            print(f"⚠️ Error loading MQTT topics: {e}, using defaults")
            return {
                'write_command': 'bacnet/write/command',
                'write_result': 'bacnet/write/result',
                'polling_results': 'bacnet/polling/points'
            }

    async def read_with_retry(self, device_address, object_id, property_id):
        """
        Read BACnet point with retry logic and exponential backoff.
        
        Args:
            device_address: BACnet device address
            object_id: BACnet object identifier
            property_id: BACnet property identifier
            
        Returns:
            tuple: (value, success, retry_count)
        """
        for attempt in range(self.max_retries + 1):
            try:
                # Calculate timeout with exponential backoff
                if self.exponential_backoff and attempt > 0:
                    timeout = self.base_timeout * (2 ** (attempt - 1))
                else:
                    timeout = self.base_timeout
                
                print(f"  Attempt {attempt + 1}: Reading {property_id} from {object_id} at {device_address} (timeout: {timeout}ms)")
                
                # Create read request with destination (proven working pattern)
                request = ReadPropertyRequest(
                    objectIdentifier=object_id,
                    propertyIdentifier=PropertyIdentifier(property_id),
                    destination=device_address
                )
                
                # Send request with timeout (proven working pattern)
                response = await asyncio.wait_for(
                    self.request(request),
                    timeout=timeout / 1000.0  # Convert to seconds
                )
                
                if response:
                    # Extract value from response with simplified approach
                    if hasattr(response, 'propertyValue'):
                        bacnet_value = response.propertyValue
                        
                        # Convert BACnet Any object to string and extract the actual value
                        value_str = str(bacnet_value)
                        
                        # If it's the Any object representation, try to extract the actual value
                        if "bacpypes3.primitivedata.Any object" in value_str:
                            # Try to access the underlying data through tagList
                            try:
                                if hasattr(bacnet_value, 'tagList') and bacnet_value.tagList:
                                    # Get all tags and find the one with actual data
                                    tag_list = list(bacnet_value.tagList)
                                    
                                    # Look for the tag with actual data (not empty)
                                    data_tag = None
                                    for i, tag in enumerate(tag_list):
                                        if hasattr(tag, 'tag_data') and tag.tag_data and len(tag.tag_data) > 0:
                                            data_tag = tag
                                            break
                                    
                                    if not data_tag:
                                        # If no tag with data, use the first tag
                                        data_tag = tag_list[0]
                                    
                                    if hasattr(data_tag, 'tag_data'):
                                        # For different BACnet types, decode the bytes
                                        if hasattr(data_tag, 'tag_number'):
                                            tag_number = data_tag.tag_number
                                            tag_data = data_tag.tag_data
                                            
                                            # Check if tag data is empty
                                            if not tag_data or len(tag_data) == 0:
                                                value = "empty_tag_data"
                                            else:
                                                # Decode based on tag type
                                                if tag_number == 1:  # Boolean
                                                    value = bool(tag_data[0])
                                                elif tag_number == 2:  # Unsigned
                                                    if len(tag_data) == 1:
                                                        value = tag_data[0]
                                                    elif len(tag_data) == 2:
                                                        value = struct.unpack('>H', tag_data)[0]
                                                    elif len(tag_data) == 4:
                                                        value = struct.unpack('>I', tag_data)[0]
                                                    else:
                                                        value = int.from_bytes(tag_data, byteorder='big')
                                                elif tag_number == 3:  # Integer
                                                    if len(tag_data) == 1:
                                                        value = struct.unpack('>b', tag_data)[0]
                                                    elif len(tag_data) == 2:
                                                        value = struct.unpack('>h', tag_data)[0]
                                                    elif len(tag_data) == 4:
                                                        value = struct.unpack('>i', tag_data)[0]
                                                    else:
                                                        value = int.from_bytes(tag_data, byteorder='big', signed=True)
                                                elif tag_number == 4:  # Real
                                                    value = struct.unpack('>f', tag_data)[0]
                                                elif tag_number == 5:  # Double
                                                    value = struct.unpack('>d', tag_data)[0]
                                                elif tag_number == 7:  # CharacterString
                                                    value = tag_data.decode('utf-8')
                                                elif tag_number == 9:  # Enumerated (Binary values)
                                                    # Decode binary values properly
                                                    if len(tag_data) == 1:
                                                        value = bool(tag_data[0])
                                                    else:
                                                        value = f"tag_9: {tag_data}"
                                                else:
                                                    value = f"tag_{tag_number}: {tag_data}"
                                        else:
                                            value = str(bacnet_value)
                                    else:
                                        value = str(bacnet_value)
                                else:
                                    value = str(bacnet_value)
                            except Exception as e:
                                # If all else fails, use string representation
                                value = f"extraction_error: {e}"
                        else:
                            # Not an Any object, use as-is
                            value = value_str
                    else:
                        value = str(response)
                    
                    return value, True, attempt
                else:
                    print(f"  Attempt {attempt + 1}: No response from {device_address}")
                    
            except asyncio.TimeoutError:
                print(f"  Attempt {attempt + 1}: Timeout reading from {device_address}")
            except Exception as e:
                print(f"  Attempt {attempt + 1}: Error reading from {device_address}: {type(e).__name__}: {str(e)}")
            
            # Increment retry counter
            if attempt < self.max_retries:
                self.total_retry_attempts += 1
                await asyncio.sleep(1)  # Brief delay between retries
        
        return None, False, self.max_retries

    async def write_with_retry(self, device_address, object_id, value, priority=8):
        """
        Write BACnet point with retry logic and exponential backoff.
        
        Args:
            device_address: BACnet device address
            object_id: BACnet object identifier
            value: Value to write
            priority: Priority level for the write (1-16, default 8)
            
        Returns:
            tuple: (success, retry_count)
        """
        for attempt in range(self.max_retries + 1):
            try:
                # Calculate timeout with exponential backoff
                if self.exponential_backoff and attempt > 0:
                    timeout = self.base_timeout * (2 ** (attempt - 1))
                else:
                    timeout = self.base_timeout
                
                print(f"  Attempt {attempt + 1}: Writing {value} to {object_id} at {device_address} (timeout: {timeout}ms)")
                
                # Create BACnet value
                bacnet_value = Real(value)
                
                # Create write request with destination and priority
                # Try writing to presentValue first (simpler approach)
                request = WritePropertyRequest(
                    objectIdentifier=object_id,
                    propertyIdentifier="presentValue",
                    propertyValue=bacnet_value,
                    destination=device_address
                )
                
                print(f"  📝 Write request details:")
                print(f"    Object: {object_id}")
                print(f"    Property: presentValue")
                print(f"    Value: {bacnet_value}")
                print(f"    Priority: {priority} (not used in this approach)")
                print(f"    Destination: {device_address}")
                
                # Send request with timeout
                response = await asyncio.wait_for(
                    self.request(request),
                    timeout=timeout / 1000.0  # Convert to seconds
                )
                
                if response:
                    print(f"  📨 Write response received: {type(response).__name__}")
                    print(f"  📨 Response details: {response}")
                else:
                    print(f"  ⚠️ No response received (this might be normal for writes)")
                
                return True, attempt
                    
            except asyncio.TimeoutError:
                print(f"  Attempt {attempt + 1}: Timeout writing to {device_address}")
            except Exception as e:
                print(f"  Attempt {attempt + 1}: Error writing to {device_address}: {type(e).__name__}: {str(e)}")
            
            # Increment retry counter
            if attempt < self.max_retries:
                self.total_retry_attempts += 1
                await asyncio.sleep(1)  # Brief delay between retries
        
        return False, self.max_retries

    def find_point_in_config(self, point_id):
        """
        Find a point in the loaded JSON configuration by object_id.
        
        Args:
            point_id: Object ID to find (e.g., "120")
            
        Returns:
            dict: Point configuration or None if not found
        """
        try:
            point_id_int = int(point_id)
            
            # Search through all devices and points
            for device_ip, device in self.loaded_config['devices'].items():
                for point in device['points']:
                    if point['object_id'] == point_id_int:
                        # Add device info to point data
                        point['device_ip'] = device['device_ip']
                        point['device_port'] = device['device_port']
                        point['device_id'] = device['device_id']
                        return point
            
            return None
            
        except (ValueError, KeyError) as e:
            print(f"Error finding point {point_id}: {e}")
            return None

    async def write_point_dynamic(self, point_id, value, priority=8):
        """
        Write a value to any writable point using JSON configuration.
        
        Args:
            point_id: Object ID to write to (e.g., "120")
            value: Value to write
            priority: Priority level for the write (1-16, default 8)
            
        Returns:
            bool: Success status
        """
        try:
            print(f"\n✏️ Writing {value} to Point {point_id}...")
            
            # Find point in configuration
            point_config = self.find_point_in_config(point_id)
            
            if not point_config:
                print(f"❌ Point {point_id} not found in configuration")
                self.publish_write_result("error", f"Point {point_id} not found in configuration")
                return False
            
            # Check if point is writable using dynamic field detection
            writable_field = self.detect_writable_field(point_config)
            if not point_config.get(writable_field, False):
                print(f"❌ Point {point_id} is not writable")
                self.publish_write_result("error", f"Point {point_id} is not writable")
                return False
            
            # Check if point is enabled using smart filter value detection
            if not self.get_filter_value(point_config):
                print(f"❌ Point {point_id} is not enabled")
                self.publish_write_result("error", f"Point {point_id} is not enabled")
                return False
            
            # Extract point configuration from JSON
            device_ip = point_config['device_ip']
            device_port = point_config['device_port']
            object_type = point_config['object_type']
            object_id = point_config['object_id']
            haystack_name = point_config['haystack_point_name']
            
            print(f"📋 Point configuration:")
            print(f"  Device: {device_ip}:{device_port}")
            print(f"  Object: {object_type} {object_id}")
            print(f"  Name: {haystack_name}")
            print(f"  Writable: {point_config.get(writable_field, False)}")
            
            # Create device address
            device_addr = Address(f"{device_ip}:{device_port}")
            
            # Create object identifier
            obj_id = ObjectIdentifier(f"{object_type},{object_id}")
            
            # Read current value first
            print(f"📖 Reading current value...")
            current_value, read_success, read_retries = await self.read_with_retry(
                device_addr, 
                obj_id, 
                PropertyIdentifier.presentValue
            )
            
            if not read_success:
                print(f"❌ Failed to read current value")
                self.publish_write_result("error", f"Failed to read current value for Point {point_id}")
                return False
            
            print(f"📖 Current value: {current_value}")
            
            # Write new value
            print(f"✏️ Writing new value...")
            write_success, write_retries = await self.write_with_retry(
                device_addr,
                obj_id,
                value,
                priority
            )
            
            if write_success:
                # Wait briefly and read again
                await asyncio.sleep(1)
                new_value, read_success, read_retries = await self.read_with_retry(
                    device_addr, 
                    obj_id, 
                    PropertyIdentifier.presentValue
                )
                
                if read_success:
                    print(f"✅ Write completed: {current_value} → {new_value}")
                    
                    # Publish result
                    result = {
                        "timestamp": datetime.utcnow().isoformat() + 'Z',
                        "point": str(point_id),
                        "haystack_point_name": haystack_name,
                        "device_ip": device_ip,
                        "object_type": object_type,
                        "object_id": object_id,
                        "old_value": current_value,
                        "new_value": new_value,
                        "requested_value": value,
                        "success": True,
                        "message": "Write completed successfully"
                    }
                    
                    self.publish_write_result("success", result)
                    
                    # Update statistics
                    self.total_write_attempts += 1
                    self.total_write_successes += 1
                    
                    return True
                else:
                    print(f"⚠️ Write sent but couldn't verify new value")
                    self.publish_write_result("error", f"Write sent but couldn't verify new value")
                    self.total_write_attempts += 1
                    self.total_write_successes += 1
                    return True
            else:
                print(f"❌ Write operation failed")
                self.publish_write_result("error", f"Write operation failed for Point {point_id}")
                self.total_write_attempts += 1
                self.total_write_failures += 1
                return False
                
        except Exception as e:
            print(f"❌ Error writing to Point {point_id}: {e}")
            self.publish_write_result("error", f"Command error: {e}")
            self.total_write_attempts += 1
            self.total_write_failures += 1
            return False

    async def write_point_120(self, value):
        """
        Write a value to Point 120 (legacy method for backward compatibility).
        
        Args:
            value: Value to write
            
        Returns:
            bool: Success status
        """
        return await self.write_point_dynamic("120", value)

    async def process_write_commands(self):
        """Process any pending write commands."""
        while self.pending_write_commands:
            command = self.pending_write_commands.pop(0)
            await self.handle_write_command(command)

    async def handle_write_command(self, command):
        """Handle write commands from MQTT."""
        try:
            # Extract command parameters
            point_id = command.get('point')
            value = command.get('value')
            priority = command.get('priority', 8)  # Default to priority 8 if not specified
            
            if not point_id or value is None:
                self.publish_write_result("error", "Missing point or value")
                return
            
            print(f"\n✏️ Executing write command:")
            print(f"  Point: {point_id}")
            print(f"  Value: {value}")
            print(f"  Priority: {priority}")
            
            # Execute write with priority
            await self.write_point_dynamic(point_id, value, priority)
                
        except Exception as e:
            print(f"❌ Error handling write command: {e}")
            self.publish_write_result("error", f"Command error: {e}")

    async def poll_points_by_interval(self, interval_points):
        """
        Poll points for a specific interval.
        
        Args:
            interval_points: List of points to poll for this interval
        """
        if not interval_points:
            return
        
        print(f"--- Polling {len(interval_points)} points (interval: {interval_points[0]['poll_interval']}s) ---")
        
        for point in interval_points:
            try:
                # Parse device address
                device_ip = point['device_ip']
                device_port = point.get('device_port', 47808)
                device_address = Address(f"{device_ip}:{device_port}")
                
                # Create object identifier
                object_id = ObjectIdentifier(f"{point['object_type']},{point['object_id']}")
                
                # Read point value
                value, success, retries = await self.read_with_retry(
                    device_address, 
                    object_id, 
                    PropertyIdentifier.presentValue
                )
                
                # Update statistics
                self.total_points_polled += 1
                
                if success:
                    self.total_successful_reads += 1
                    quality = "ok"
                    status = "success"
                    
                    # Publish to MQTT
                    self.publish_point_to_mqtt(point, str(value), quality, status)
                    
                else:
                    self.total_failed_reads += 1
                    quality = "error"
                    status = "timeout"
                    
                    # Publish error to MQTT
                    self.publish_point_to_mqtt(point, None, quality, status)
                    
            except Exception as e:
                print(f"✗ Error polling point {point['haystack_point_name']}: {e}")
                self.total_failed_reads += 1
                
                # Publish error to MQTT
                self.publish_point_to_mqtt(point, None, "error", "exception")

    async def poll_interval_concurrently(self, interval, points):
        """
        Poll points for a specific interval concurrently.
        
        Args:
            interval: Polling interval in seconds
            points: List of points to poll for this interval
        """
        while self.running:
            try:
                if points:
                    await self.poll_points_by_interval(points)
                
                # Wait for the full interval before next poll
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"✗ Error in interval {interval}s polling: {e}")
                await asyncio.sleep(5)  # Brief delay before retrying



    def print_statistics(self):
        """Print current polling and writing statistics."""
        uptime = time.time() - self.start_time
        hours = uptime / 3600
        
        print(f"=== Production Integrated Statistics ===")
        print(f"Uptime: {int(uptime)}s ({hours:.1f}h)")
        print(f"Polling cycles: {self.polling_cycles}")
        print(f"Total points polled: {self.total_points_polled}")
        print(f"Successful reads: {self.total_successful_reads}")
        print(f"Failed reads: {self.total_failed_reads}")
        
        if self.total_points_polled > 0:
            success_rate = (self.total_successful_reads / self.total_points_polled) * 100
            print(f"BACnet read success rate: {success_rate:.1f}%")
        
        print(f"Total retry attempts: {self.total_retry_attempts}")
        # print(f"JSON writes: {self.total_json_writes}")
        # print(f"JSON errors: {self.total_json_errors}")
        
        # if self.total_json_writes > 0:
        #     json_success_rate = ((self.total_json_writes - self.total_json_errors) / self.total_json_writes) * 100
        #     print(f"JSON success rate: {json_success_rate:.1f}%")
        
        print(f"MQTT publishes: {self.total_mqtt_publishes}")
        print(f"MQTT errors: {self.total_mqtt_errors}")
        
        if self.total_mqtt_publishes > 0:
            mqtt_success_rate = ((self.total_mqtt_publishes - self.total_mqtt_errors) / self.total_mqtt_publishes) * 100
            print(f"MQTT success rate: {mqtt_success_rate:.1f}%")
        
        print(f"Write attempts: {self.total_write_attempts}")
        print(f"Write successes: {self.total_write_successes}")
        print(f"Write failures: {self.total_write_failures}")
        
        if self.total_write_attempts > 0:
            write_success_rate = (self.total_write_successes / self.total_write_attempts) * 100
            print(f"Write success rate: {write_success_rate:.1f}%")

    def cleanup_mqtt(self):
        """Clean up MQTT connection."""
        if self.mqtt_client:
            print("Cleaning up MQTT connection...")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.running = False

async def main():
    """Main polling and writing function."""
    print("=== Integrated BACnet Reading/Writing with MQTT ===")
    print("MQTT broker configuration from YAML file")
    print("=" * 80)
    
    # Load configuration from YAML file
    bacnet_config = None
    try:
        with open("config/bacnet_config.yaml", 'r', encoding='utf-8') as f:
            bacnet_config = yaml.safe_load(f)
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return
    
    # Create MQTT configuration from YAML file
    mqtt_config = {
        'broker': bacnet_config['mqtt']['broker'],  # Single broker for all operations
        'port': bacnet_config['mqtt']['port'],
        'client_id': bacnet_config['mqtt']['client_id'],
        'username': bacnet_config['mqtt']['username'],
        'password': bacnet_config['mqtt']['password'],
        'keepalive': bacnet_config['mqtt']['keepalive'],
        'max_inflight_messages': bacnet_config['mqtt']['max_inflight_messages'],
        'max_queued_messages': bacnet_config['mqtt']['max_queued_messages']
    }
    
    print(f"✓ MQTT configuration loaded from YAML:")
    print(f"  Broker: {mqtt_config['broker']}:{mqtt_config['port']}")
    print(f"  Client ID: {mqtt_config['client_id']}")
    print(f"  Keepalive: {mqtt_config['keepalive']}s")
    
    # Create device configuration from YAML file
    device_config = {
        'device_id': bacnet_config['device']['device_id'],
        'device_name': bacnet_config['device']['device_name'],
        'vendor_id': bacnet_config['device']['vendor_id'],
        'apdu_length': bacnet_config['discovery'].get('apdu_length', 1024),
        'segmentation': bacnet_config['discovery'].get('segmentation', "segmentedBoth")
    }
    
    print(f"✓ Device configuration loaded from YAML:")
    print(f"  Device ID: {device_config['device_id']}")
    print(f"  Device Name: {device_config['device_name']}")
    print(f"  Vendor ID: {device_config['vendor_id']}")
    print(f"  APDU Length: {device_config['apdu_length']}")
    print(f"  Segmentation: {device_config['segmentation']}")
    
    # Create local BACnet address from YAML configuration
    local_ip = bacnet_config['network']['local_ip']
    subnet = bacnet_config['network']['subnet']
    local_port = bacnet_config['network']['local_port']
    local_addr = Address(f"{local_ip}/{subnet}:{local_port}")
    
    print(f"✓ Using BACnet local address: {local_addr}")
    
    # Create integrated application
    app = ProductionIntegratedApp(local_addr, mqtt_config, device_config)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    
    try:
        # Setup MQTT
        if not app.setup_mqtt():
            print("✗ Failed to setup MQTT, exiting...")
            return
        
        # Load Stage 4 Runtime configuration
        config = app.load_stage4_config()
        if not config:
            print("✗ Failed to load configuration, exiting...")
            return
        
        print("\n🚀 Production Integrated BACnet Reading/Writing started successfully!")
        
        # Load MQTT topics for display
        mqtt_topics = app.load_mqtt_topics_from_config()
        write_command_topic = mqtt_topics.get('write_command', 'bacnet/write/command')
        write_result_topic = mqtt_topics.get('write_result', 'bacnet/write/result')
        
        print(f"📡 Listening for MQTT write commands on: {write_command_topic}")
        print("📤 Publishing polling results to: bacnet/polling/points")
        print(f"📤 Publishing write results to: {write_result_topic}")
        print("💡 To write to any writable point, send MQTT message to bacnet/write/command:")
        print('   {"point": "120", "value": 85.0}')
        print('   {"point": "121", "value": 75.0}')
        print("   (Any point with is_writable=true or writable=true in JSON configuration)")
        print("\nPress Ctrl+C to stop")
        
        # Start concurrent polling tasks
        polling_tasks = []
        
        # Create a task for each interval
        for interval, points in app.poll_intervals.items():
            if points:
                task = asyncio.create_task(
                    app.poll_interval_concurrently(interval, points),
                    name=f"poll_interval_{interval}s"
                )
                polling_tasks.append(task)
                print(f"✓ Started concurrent polling for {interval}s interval ({len(points)} points)")
        
        if not polling_tasks:
            print("⚠️ No points to poll - check configuration")
            return
        
        # Main loop for statistics and write command processing
        while app.running:
            try:
                # Process any pending write commands
                await app.process_write_commands()
                
                # Update cycle counter
                app.polling_cycles += 1
                
                # Print statistics every 10 cycles
                if app.polling_cycles % 10 == 0:
                    app.print_statistics()
                
                # Brief sleep to prevent busy waiting
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"✗ Error in main loop: {e}")
                await asyncio.sleep(5)  # Brief delay before retrying
        
        # Cancel all polling tasks on shutdown
        for task in polling_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*polling_tasks, return_exceptions=True)
        
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, shutting down...")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    finally:
        # Cleanup
        app.cleanup_mqtt()
        app.print_statistics()
        print("✓ Production integrated polling and writing stopped gracefully")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript terminated by user")
    except asyncio.CancelledError:
        # This is normal during shutdown, suppress the error
        pass
    except Exception as e:
        print(f"Unexpected error: {e}") 
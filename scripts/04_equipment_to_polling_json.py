#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
BACnet Equipment to Polling JSON Converter
==========================================

PURPOSE: Convert equipment lookup CSV directly to Stage 4 Runtime JSON for polling, with dynamic MQTT topics metadata and device port handling.
STATUS: Production-ready. All configuration (equipment, device IP/port, point details) is loaded from CSV; all output is fully dynamic and JSON-based. No hardcoded network or topic values.
INPUT: config/discovered_points.csv (from equipment lookup script)
OUTPUT: config/production_json/05_polling_config.json (Stage 4 Runtime format with MQTT topics and device ports)

This module converts equipment lookup CSV directly to Stage 4 Runtime JSON format:
- Generates Haystack point names from equipment configuration
- Filters MQTT publish points (mqtt_publish = True)
- Converts directly to JSON format optimized for polling
- Adds runtime fields for polling (timestamp, value, quality)
- Dynamically parses device IP and port for each point
- Generates MQTT topics metadata for easy reference (all topics, summary, system topics)
- Includes comprehensive validation and summary statistics

STAGE 4 RUNTIME REQUIREMENTS:
- PRESERVED: All ESSENTIAL fields from equipment configuration
- GENERATED: haystack_point_name (from equipment data)
- ADDED: timestamp (RUNTIME_GEN), value (BACNET_READ), quality (RUNTIME_GEN), device_port (parsed from CSV)
- FILTERED: Only MQTT publish points (mqtt_publish = True)
- FORMAT: JSON structure optimized for polling scripts
- METADATA: MQTT topics summary for easy access

USAGE:
    python3 scripts/05_equipment_to_polling_json.py

OUTPUT FORMAT:
    See output JSON for full structure. Each point includes device_port, and all MQTT topics are summarized in metadata.

DEPENDENCIES:
    - pandas library
    - config/discovered_points.csv (from equipment lookup script)
    - config/bacnet_config.yaml (for MQTT publishing configuration)

AUTHOR: BACnet-to-MQTT Project
VERSION: 1.0 (Stage 4 Runtime with MQTT Topics and dynamic ports)
LAST UPDATED: 2025-07-25
"""

import pandas as pd
import json
import sys
import yaml
from datetime import datetime

def load_mqtt_publishing_config(yaml_file="config/bacnet_config.yaml"):
    """
    Load MQTT publishing configuration from YAML file.
    
    This function loads the MQTT publishing configuration to understand which fields
    are required for MQTT messages and which points to publish.
    
    Args:
        yaml_file: Path to BACnet configuration YAML file
        
    Returns:
        dict: MQTT publishing configuration
    """
    try:
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
        
        mqtt_config = config.get('mqtt_publishing', {})
        if not mqtt_config:
            print("Warning: No mqtt_publishing configuration found in YAML")
            print("Using default MQTT publishing configuration...")
            return {
                'point_filter_column': 'mqtt_publish',
                'required_fields': [
                    'timestamp', 'value', 'haystack_point_name', 'object_type', 'units',
                    'site_id', 'site_timezone', 'equipment_type', 'equipment_id',
                    'point_function', 'quantity', 'subject', 'location', 'qualifier', 'dis'
                ]
            }
        
        # Convert field selection format (true/false) to list of selected fields
        if 'required_fields' in mqtt_config and isinstance(mqtt_config['required_fields'], dict):
            selected_fields = [field for field, enabled in mqtt_config['required_fields'].items() if enabled]
            mqtt_config['required_fields'] = selected_fields
        
        return mqtt_config
    except Exception as e:
        print(f"Warning: Could not load MQTT publishing configuration: {e}")
        print("Using default MQTT publishing configuration...")
        return {
            'point_filter_column': 'mqtt_publish',
            'required_fields': [
                'timestamp', 'value', 'haystack_point_name', 'object_type', 'units',
                'site_id', 'site_timezone', 'equipment_type', 'equipment_id',
                'point_function', 'quantity', 'subject', 'location', 'qualifier', 'dis'
            ]
        }

def load_mqtt_system_topics(yaml_file="config/bacnet_config.yaml"):
    """
    Load MQTT system topics configuration from YAML file.
    
    Args:
        yaml_file: Path to BACnet configuration YAML file
        
    Returns:
        dict: MQTT system topics configuration
    """
    try:
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check for mqtt_system_topics section first
        if 'mqtt_system_topics' in config:
            return config['mqtt_system_topics']
        
        # Fallback to default topics
        print("Using default MQTT system topics...")
        return {
            "write_command": "bacnet/write/command",
            "write_result": "bacnet/write/result",
            "polling_results": "bacnet/polling/points"
        }
    except Exception as e:
        print(f"Warning: Could not load MQTT system topics: {e}")
        print("Using default MQTT system topics...")
        return {
            "write_command": "bacnet/write/command",
            "write_result": "bacnet/write/result",
            "polling_results": "bacnet/polling/points"
        }

def load_default_bacnet_port(yaml_file="config/bacnet_config.yaml"):
    """
    Load default BACnet port from YAML file.
    
    Args:
        yaml_file: Path to BACnet configuration YAML file
        
    Returns:
        int: Default BACnet port
    """
    try:
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get port from network.local_port
        network_config = config.get('network', {})
        port = network_config.get('local_port', '47808')
        
        # Convert to int and validate
        port_int = int(port)
        if 1 <= port_int <= 65535:
            return port_int
        else:
            print(f"Warning: Invalid port {port_int}, using default 47808")
            return 47808
            
    except Exception as e:
        print(f"Warning: Could not load BACnet port: {e}")
        print("Using default BACnet port 47808...")
        return 47808

def load_timezone_from_yaml(yaml_file="config/bacnet_config.yaml"):
    """
    Load timezone from BACnet configuration YAML file.
    
    Args:
        yaml_file: Path to BACnet configuration YAML file
        
    Returns:
        str: Timezone string or None if not found
    """
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        timezone = config.get('timezone')
        if timezone:
            print(f"✓ Loaded timezone from {yaml_file}: {timezone}")
            return timezone
        else:
            print(f"⚠ No timezone found in {yaml_file}")
            return None
            
    except Exception as e:
        print(f"⚠ Error loading timezone from {yaml_file}: {e}")
        return None

def generate_haystack_point_name(row):
    """
    Generate Haystack point name from equipment configuration data.
    
    Args:
        row: DataFrame row containing equipment configuration
        
    Returns:
        str: Generated Haystack point name
    """
    # Extract components for Haystack naming
    site_id = str(row.get('site_id', '')).strip()
    equipment_type = str(row.get('equipment_type', '')).strip()
    
    # Handle NaN values for equipment_id
    equipment_id_raw = row.get('equipment_id', 0)
    if pd.isna(equipment_id_raw) or equipment_id_raw == '':
        equipment_id = '0'
    else:
        equipment_id = str(int(float(equipment_id_raw)))  # Convert to int to remove .0
    
    point_function = str(row.get('point_function', '')).strip()
    quantity = str(row.get('quantity', '')).strip()
    subject = str(row.get('subject', '')).strip()
    location = str(row.get('location', '')).strip()
    qualifier = str(row.get('qualifier', '')).strip()
    
    # Build Haystack point name components
    components = []
    
    # Add site if available
    if site_id:
        components.append(site_id)
    
    # Add equipment type
    if equipment_type:
        components.append(equipment_type)
    
    # Add equipment ID
    if equipment_id:
        components.append(equipment_id)
    
    # Add point function
    if point_function:
        components.append(point_function)
    
    # Add quantity
    if quantity:
        components.append(quantity)
    
    # Add subject
    if subject:
        components.append(subject)
    
    # Add location
    if location:
        components.append(location)
    
    # Add qualifier
    if qualifier:
        components.append(qualifier)
    
    # If no meaningful components, use device and object info
    if not components:
        device_id = str(row.get('device_id', ''))
        object_type = str(row.get('object_type', ''))
        object_id = str(row.get('object_id', ''))
        components = [device_id, object_type, object_id]
    
    # Object ID is not included in Haystack point names per user requirement
    
    # Join components with dots and clean up
    haystack_name = '.'.join(components)
    
    # Clean up the name (remove special characters, normalize)
    haystack_name = haystack_name.replace(' ', '_')
    haystack_name = haystack_name.replace('-', '_')
    haystack_name = haystack_name.replace('/', '_')
    haystack_name = haystack_name.replace('\\', '_')
    
    # Remove multiple consecutive underscores
    while '__' in haystack_name:
        haystack_name = haystack_name.replace('__', '_')
    
    # Remove leading/trailing underscores
    haystack_name = haystack_name.strip('_')
    
    # Ensure it's not empty
    if not haystack_name:
        haystack_name = f"point_{row.get('device_id', 'unknown')}_{row.get('object_id', 'unknown')}"
    
    return haystack_name.lower()

def generate_mqtt_topic(row):
    """
    Generate MQTT topic in format: site_id/equipment_type_equipment_id/abbreviated_object_type_object_id/present_value
    
    Args:
        row: DataFrame row containing equipment configuration
        
    Returns:
        str: Generated MQTT topic
    """
    def clean(val):
        return str(val).strip().replace(' ', '_').replace('-', '_').replace('\\', '_')
    
    # Object type abbreviations
    object_type_abbrev = {
        'analog-input': 'ai',
        'analog-output': 'ao', 
        'analog-value': 'av',
        'binary-input': 'bi',
        'binary-output': 'bo',
        'binary-value': 'bv',
        'multi-state-input': 'msi',
        'multi-state-output': 'mso',
        'multi-state-value': 'msv',
        'trend-log': 'tl',
        'schedule': 'sch',
        'calendar': 'cal',
        'command': 'cmd',
        'device': 'dev',
        'file': 'file',
        'group': 'grp',
        'loop': 'loop',
        'program': 'prog',
        'notification-class': 'nc',
        'alarm-summary': 'as',
        'event-enrollment': 'ee',
        'life-safety-point': 'lsp',
        'life-safety-zone': 'lsz',
        'accumulator': 'acc',
        'pulse-converter': 'pc',
        'network-security': 'ns',
        'bitstring-value': 'bsv',
        'characterstring-value': 'csv',
        'date-pattern-value': 'dpv',
        'date-value': 'dv',
        'datetime-pattern-value': 'dtpv',
        'datetime-value': 'dtv',
        'integer-value': 'iv',
        'large-analog-value': 'lav',
        'octetstring-value': 'osv',
        'positive-integer-value': 'piv',
        'time-pattern-value': 'tpv',
        'time-value': 'tv',
        'lighting-output': 'lo'
    }
    
    site_id = clean(row.get('site_id', 'unknown_site'))
    equipment_type = clean(row.get('equipment_type', 'unknown_equipment'))
    
    # Handle NaN values for equipment_id
    equipment_id_raw = row.get('equipment_id', 0)
    if pd.isna(equipment_id_raw) or equipment_id_raw == '':
        equipment_id = '0'
    else:
        equipment_id = clean(str(int(float(equipment_id_raw))))  # Convert to int to remove .0
    
    object_type = clean(row.get('object_type', 'unknown_object'))
    object_id = clean(row.get('object_id', 'unknown'))
    
    # Get abbreviated object type
    object_type_abbrev_key = object_type.lower().replace('_', '-')
    abbreviated_type = object_type_abbrev.get(object_type_abbrev_key, object_type[:3])  # Fallback to first 3 chars
    
    equipment = f"{equipment_type}_{equipment_id}" if equipment_type and equipment_id else equipment_type or equipment_id or 'unknown_equipment'
    object_part = f"{abbreviated_type}{object_id}" if abbreviated_type and object_id else abbreviated_type or object_id or 'unknown_object'
    topic = f"{site_id}/{equipment}/{object_part}/present_value".lower()
    while '__' in topic:
        topic = topic.replace('__', '_')
    topic = topic.strip('_')
    return topic

def convert_equipment_to_polling_json(csv_file="config/discovered_points.csv", 
                                    json_file="config/production_json/polling_config.json"):
    """
    Convert equipment lookup CSV directly to Stage 4 Runtime JSON for polling.
    
    This function processes equipment lookup data and generates a comprehensive
    JSON configuration optimized for BACnet polling with integrated MQTT topics
    metadata for easy reference and management.
    
    Args:
        csv_file: Input CSV file path (equipment lookup configuration)
        json_file: Output JSON file path (Stage 4 Runtime configuration)
        
    Returns:
        dict: Generated JSON configuration with MQTT topics metadata
    """
    print(f"Converting {csv_file} directly to Stage 4 Runtime JSON format...")
    
    # Load MQTT publishing configuration
    mqtt_config = load_mqtt_publishing_config()
    
    # Load MQTT system topics configuration
    mqtt_system_topics = load_mqtt_system_topics()
    
    # Load default BACnet port
    default_bacnet_port = load_default_bacnet_port()
    
    # Load timezone from YAML configuration
    site_timezone = load_timezone_from_yaml()
    
    # Load equipment lookup CSV
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} points from {csv_file}")
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return None
    
    # Filter out non-MQTT publish points (mqtt_publish = FALSE) - from script 04
    print("\nFiltering MQTT publish points...")
    filter_column = mqtt_config.get('point_filter_column', 'mqtt_publish')
    enabled_df = df[df[filter_column] == True].copy()
    disabled_count = len(df) - len(enabled_df)
    print(f"Removed {disabled_count} non-MQTT publish points ({filter_column} = FALSE)")
    print(f"Remaining MQTT publish points: {len(enabled_df)}")
    
    # Initialize JSON structure
    polling_config = {
        "metadata": {
            "conversion_timestamp": datetime.now().isoformat(),
            "source_csv": csv_file,
            "stage": "Stage 4 Runtime",
            "version": "1.0",
            "description": "Stage 4 Runtime JSON configuration for BACnet polling (direct conversion)",
            "site_timezone": site_timezone
        },
        "devices": {}
    }
    
    # Initialize MQTT topics collection
    mqtt_topics = {
        "system_topics": mqtt_system_topics,
        "point_topics": [],
        "summary": {
            "total_topics": 0,
            "writable_topics": 0,
            "devices": set(),
            "equipment": set()
        }
    }
    
    # Process each enabled point
    for index, row in enabled_df.iterrows():
        # Parse device_ip:port format
        device_ip_port = row['device_ip']
        if ':' in device_ip_port:
            device_ip, device_port = device_ip_port.split(':')
            device_port = int(device_port)
        else:
            device_ip = device_ip_port
            device_port = default_bacnet_port  # Use YAML configuration
        
        # Create device entry if it doesn't exist
        if device_ip_port not in polling_config['devices']:
            polling_config['devices'][device_ip_port] = {
                "device_ip": device_ip,
                "device_port": device_port,
                "device_id": int(row['device_id']),
                "points": []
            }
        
        # Generate Haystack point name (from script 04)
        # Check if equipment configuration is complete
        equipment_fields = ['site_id', 'equipment_type', 'equipment_id', 'point_function', 
                           'quantity', 'subject', 'location', 'qualifier']
        equipment_complete = all(pd.notna(row[field]) and str(row[field]).strip() != '' 
                               for field in equipment_fields)
        
        if equipment_complete:
            haystack_point_name = generate_haystack_point_name(row)
        else:
            # Generate fallback name using available data
            device_id = row['device_id']
            object_id = row['object_id']
            object_type = row['object_type']
            haystack_point_name = f"fallback.{device_id}.{object_type}.{object_id}"
        
        # Generate MQTT topic (from script 05)
        mqtt_topic = generate_mqtt_topic(row)
        
        # Check if point is writable (use is_writable from analysis)
        is_writable = bool(row.get('is_writable', False)) if isinstance(row.get('is_writable', False), bool) else str(row.get('is_writable', 'false')).lower() == 'true'
        
        # Add to MQTT topics collection
        topic_entry = {
            "topic": mqtt_topic,
            "point_name": haystack_point_name,
            "device_ip": device_ip,
            "object_type": row['object_type'],
            "object_id": int(row['object_id']),
            "writable": is_writable,
            "equipment_type": row['equipment_type'],
            "equipment_id": int(float(row['equipment_id'])) if pd.notna(row['equipment_id']) and str(row['equipment_id']).strip() != '' else 0  # Convert to int via float to handle "12.0"
        }
        mqtt_topics["point_topics"].append(topic_entry)
        
        # Update summary statistics
        mqtt_topics["summary"]["total_topics"] += 1
        if is_writable:
            mqtt_topics["summary"]["writable_topics"] += 1
        mqtt_topics["summary"]["devices"].add(device_ip)
        mqtt_topics["summary"]["equipment"].add(f"{row['equipment_type']}_{row['equipment_id']}")
        
        # Create point entry with ALL fields from equipment CSV plus RUNTIME_GEN fields
        # Create point entry with only required fields from MQTT configuration
        required_fields = mqtt_config.get('required_fields', [])
        point_entry = {}
        
        # Add required fields from MQTT configuration
        for field in required_fields:
            if field == 'timestamp':
                point_entry[field] = datetime.now().isoformat() + 'Z'
            elif field == 'value':
                point_entry[field] = None  # Will be filled during polling
            elif field == 'haystack_point_name':
                point_entry[field] = haystack_point_name
            elif field == 'mqtt_topic':
                point_entry[field] = mqtt_topic
            elif field in row and pd.notna(row[field]) and row[field] != '':
                if field in ['equipment_id', 'qos', 'poll_interval', 'priority']:
                    if pd.notna(row[field]) and str(row[field]).strip() != '':
                        point_entry[field] = int(float(row[field]))  # Convert to int via float to handle "12.0"
                    else:
                        point_entry[field] = 0 if field == 'equipment_id' else 1  # Default values
                else:
                    point_entry[field] = row[field]
            else:
                # Set default values for missing required fields
                if field == 'units':
                    point_entry[field] = "no-units"
                elif field == 'site_timezone':
                    point_entry[field] = site_timezone
                else:
                    point_entry[field] = ""
        
        # Add essential BACnet fields for polling (always include these regardless of required_fields)
        essential_fields = {
            "object_type": row['object_type'],
            "object_id": int(row['object_id']),
            "poll_interval": int(float(row['poll_interval'])),  # Convert to int via float to handle "30.0"
            "priority": int(float(row['priority'])),  # Convert to int via float to handle "1.0"
            "mqtt_publish": bool(row[filter_column]) if isinstance(row[filter_column], bool) else str(row[filter_column]).lower() == 'true',
            "is_writable": is_writable,
            "out_of_service": bool(row['out_of_service']) if pd.notna(row['out_of_service']) and str(row['out_of_service']).strip() != '' else None,
            "device_ip": device_ip,
            "device_port": device_port,
            "device_id": int(row['device_id']),
            "site_timezone": site_timezone,
            # RUNTIME_GEN fields (added for Stage 4)
            "timestamp": None,
            "value": None,
            "quality": None
        }
        
        # Always add essential fields (required for polling functionality)
        for field, value in essential_fields.items():
            point_entry[field] = value
        
        polling_config['devices'][device_ip_port]['points'].append(point_entry)
    
    # Add summary statistics
    total_devices = len(polling_config['devices'])
    total_points = sum(len(device['points']) for device in polling_config['devices'].values())
    
    polling_config['metadata']['total_points'] = total_points
    polling_config['metadata']['total_devices'] = total_devices
    
    # Convert sets to lists for JSON serialization and add MQTT topics to metadata
    mqtt_topics["summary"]["devices"] = sorted(list(mqtt_topics["summary"]["devices"]))
    mqtt_topics["summary"]["equipment"] = sorted(list(mqtt_topics["summary"]["equipment"]))
    polling_config['metadata']['mqtt_topics'] = mqtt_topics
    
    # Save JSON configuration
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(polling_config, f, indent=2, default=str)
        
        print(f"✓ Direct conversion completed successfully!")
        print(f"Output file: {json_file}")
        print(f"Devices: {total_devices}")
        print(f"Total points: {total_points}")
        print(f"MQTT topics: {mqtt_topics['summary']['total_topics']}")
        print(f"Writable topics: {mqtt_topics['summary']['writable_topics']}")
        
        return polling_config
        
    except Exception as e:
        print(f"✗ Error saving JSON file: {e}")
        return None

def validate_polling_config(json_config):
    """
    Validate the polling configuration for Stage 4 Runtime requirements.
    
    This function performs comprehensive validation of the generated JSON configuration,
    including essential fields, runtime fields, MQTT topics metadata, and data integrity.
    
    Args:
        json_config: Generated JSON configuration
        
    Returns:
        dict: Validation results with detailed status information
    """
    validation_results = {
        'total_points': 0,
        'missing_essential': [],
        'missing_runtime_fields': [],
        'devices_with_points': 0,
        'empty_haystack_names': 0,
        'duplicate_haystack_names': 0,
        'mqtt_topics_validation': {
            'has_mqtt_topics': False,
            'total_topics': 0,
            'writable_topics': 0,
            'system_topics': [],
            'missing_system_topics': []
        }
    }
    
    if not json_config or 'devices' not in json_config:
        return validation_results
    
    # Validate MQTT topics metadata
    if 'metadata' in json_config and 'mqtt_topics' in json_config['metadata']:
        validation_results['mqtt_topics_validation']['has_mqtt_topics'] = True
        mqtt_topics = json_config['metadata']['mqtt_topics']
        
        # Check system topics
        expected_system_topics = ['write_command', 'write_result', 'polling_results']
        for topic in expected_system_topics:
            if topic in mqtt_topics.get('system_topics', {}):
                validation_results['mqtt_topics_validation']['system_topics'].append(topic)
            else:
                validation_results['mqtt_topics_validation']['missing_system_topics'].append(topic)
        
        # Check point topics summary
        if 'summary' in mqtt_topics:
            validation_results['mqtt_topics_validation']['total_topics'] = mqtt_topics['summary'].get('total_topics', 0)
            validation_results['mqtt_topics_validation']['writable_topics'] = mqtt_topics['summary'].get('writable_topics', 0)
    
    # Count total points and collect Haystack names for validation
    total_points = 0
    devices_with_points = 0
    haystack_names = []
    
    for device_ip, device in json_config['devices'].items():
        if 'points' in device and device['points']:
            devices_with_points += 1
            total_points += len(device['points'])
            
            # Validate each point
            for point in device['points']:
                # Check essential fields
                essential_fields = ['haystack_point_name', 'object_type', 'object_id', 'mqtt_topic', 'mqtt_publish', 'is_writable']
                for field in essential_fields:
                    if field not in point:
                        validation_results['missing_essential'].append(f"Point {point.get('haystack_point_name', 'unknown')} missing {field}")
                
                # Check runtime fields
                runtime_fields = ['timestamp', 'value']
                for field in runtime_fields:
                    if field not in point:
                        validation_results['missing_runtime_fields'].append(f"Point {point.get('haystack_point_name', 'unknown')} missing {field}")
                
                # Collect Haystack names for validation
                haystack_name = point.get('haystack_point_name', '')
                if haystack_name:
                    haystack_names.append(haystack_name)
                else:
                    validation_results['empty_haystack_names'] += 1
    
    # Check for duplicate Haystack names
    if haystack_names:
        unique_names = set(haystack_names)
        validation_results['duplicate_haystack_names'] = len(haystack_names) - len(unique_names)
    
    validation_results['total_points'] = total_points
    validation_results['devices_with_points'] = devices_with_points
    
    return validation_results

def main():
    """Main conversion function."""
    print("=== BACnet Equipment to Polling JSON Converter ===")
    print("Converting equipment lookup CSV to Stage 4 Runtime JSON with MQTT topics")
    print("=" * 70)
    
    # Convert equipment CSV directly to polling JSON
    polling_config = convert_equipment_to_polling_json()
    
    if polling_config:
        # Validate the converted configuration
        print("\n=== Configuration Validation ===")
        validation = validate_polling_config(polling_config)
        
        print(f"Total points: {validation['total_points']}")
        print(f"Devices with points: {validation['devices_with_points']}")
        
        if validation['missing_essential']:
            print("Missing essential fields:")
            for missing in validation['missing_essential']:
                print(f"  - {missing}")
        else:
            print("✓ All essential fields present")
        
        if validation['missing_runtime_fields']:
            print("Missing runtime fields:")
            for missing in validation['missing_runtime_fields']:
                print(f"  - {missing}")
        else:
            print("✓ All runtime fields present")
        
        if validation['empty_haystack_names'] > 0:
            print(f"⚠ Empty Haystack names: {validation['empty_haystack_names']} points")
        else:
            print("✓ All Haystack names generated")
        
        if validation['duplicate_haystack_names'] > 0:
            print(f"⚠ Duplicate Haystack names: {validation['duplicate_haystack_names']} points")
        else:
            print("✓ All Haystack names unique")
        
        # Show MQTT topics validation
        print(f"\n=== MQTT Topics Validation ===")
        mqtt_validation = validation['mqtt_topics_validation']
        if mqtt_validation['has_mqtt_topics']:
            print("✓ MQTT topics metadata present")
            print(f"Total point topics: {mqtt_validation['total_topics']}")
            print(f"Writable topics: {mqtt_validation['writable_topics']}")
            
            if mqtt_validation['system_topics']:
                print(f"System topics: {', '.join(mqtt_validation['system_topics'])}")
            else:
                print("⚠ No system topics found")
            
            if mqtt_validation['missing_system_topics']:
                print(f"Missing system topics: {', '.join(mqtt_validation['missing_system_topics'])}")
        else:
            print("⚠ MQTT topics metadata missing")
        
        # Show sample configuration
        print(f"\n=== Sample Configuration ===")
        if polling_config['devices']:
            first_device = list(polling_config['devices'].keys())[0]
            first_point = polling_config['devices'][first_device]['points'][0]
            print(f"Device: {first_device}")
            print(f"Sample point: {first_point['haystack_point_name']}")
            print(f"MQTT topic: {first_point['mqtt_topic']}")
            print(f"Object: {first_point['object_type']} {first_point['object_id']}")
            print(f"Writable: {first_point['is_writable']}")
            print(f"Runtime fields: timestamp={first_point['timestamp']}, value={first_point['value']}")
            
            # Show MQTT topics summary
            if 'mqtt_topics' in polling_config['metadata']:
                mqtt_topics = polling_config['metadata']['mqtt_topics']
                print(f"\n=== MQTT Topics Summary ===")
                print(f"System topics: {len(mqtt_topics['system_topics'])}")
                print(f"Point topics: {mqtt_topics['summary']['total_topics']}")
                print(f"Writable topics: {mqtt_topics['summary']['writable_topics']}")
                print(f"Devices: {', '.join(mqtt_topics['summary']['devices'])}")
                print(f"Equipment: {', '.join(mqtt_topics['summary']['equipment'])}")
                
                # Show sample point topics
                print(f"\nSample point topics:")
                for i, topic_entry in enumerate(mqtt_topics['point_topics'][:3]):
                    print(f"  {i+1}. {topic_entry['topic']} -> {topic_entry['point_name']} (writable: {topic_entry['writable']})")
                if len(mqtt_topics['point_topics']) > 3:
                    print(f"  ... and {len(mqtt_topics['point_topics']) - 3} more topics")
            
            # Show writable points summary
            writable_points = []
            for device_ip, device in polling_config['devices'].items():
                for point in device['points']:
                    if point.get('is_writable', False):
                        writable_points.append(f"{point['object_type']},{point['object_id']} - {point['haystack_point_name']}")
            
            if writable_points:
                print(f"\nWritable points found: {len(writable_points)}")
                for point in writable_points:
                    print(f"  - {point}")
            else:
                print(f"\nNo writable points found")
        
        print(f"\n=== Next Steps ===")
        print(f"1. Review config/production_json/polling_config.json")
        print(f"2. Check MQTT topics in metadata section (no scrolling needed)")
        print(f"3. Verify all points are present with writable field")
        print(f"4. Check MQTT topics are correctly generated")
        print(f"5. Confirm runtime fields and writable field are added")
        print(f"6. Use this JSON for Stage 4 Runtime polling with write capabilities")
        print(f"7. Easy MQTT topics access: jq '.metadata.mqtt_topics' config/production_json/polling_config.json")
        
    else:
        print(f"✗ Conversion failed. Please check the CSV file format.")
        sys.exit(1)

if __name__ == "__main__":
    main() 
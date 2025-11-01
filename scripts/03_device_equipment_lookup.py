#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
BACnet Device Equipment Lookup Module - Process 03 (Simplified - Appends to Enhanced CSV)
=========================================================================================

PURPOSE: Process enhanced discovered points and append configuration columns
STATUS: Stage 2 Configuration - Prepare for manual equipment mapping
INPUT: config/discovered_points.csv (enhanced with analysis columns)
OUTPUT: config/discovered_points.csv (enhanced with analysis + config columns)

This module processes the enhanced discovered BACnet points (with analysis columns)
and appends configuration columns for manual equipment mapping. It keeps ALL original
discovery data and analysis data, simply adding new configuration fields to the right.

SIMPLIFIED APPROACH:
- KEEPS ALL: All original discovery columns (no renaming, no dropping)
- KEEPS ALL: All analysis columns from script 02
- ADDS: New configuration columns for manual input and defaults

USAGE:
    python3 scripts/03_device_equipment_lookup_enhanced.py

OUTPUT FORMAT:
    [All original discovery columns] + [All analysis columns] + [New config columns]
    Original: device_id, device_name, device_ip, object_type, object_id, raw_point_name, description, units, present_value, status_flags, reliability, out_of_service, event_state, high_limit, low_limit, deadband, limit_enable, event_enable, acked_transitions, notify_type, profile_name, tags, audit_level, priority_array, cov_increment, time_delay, state_text, active_text, inactive_text, min_pres_value, max_pres_value, resolution, number_of_states, vendor_name, model_name, firmware_revision, protocol_version, protocol_services_supported, object_types_supported
    Analysis: is_readable, is_writable, access_type, priority_array_present, priority_levels_available, priority_override_recommendation, priority_analysis_summary, reasoning
    Config: site_id, equipment_type, equipment_id, point_function, quantity, subject, location, qualifier, qos, poll_interval, priority, mqtt_publish, writable, dis

DEPENDENCIES:
    - pandas library
    - config/discovered_points.csv (enhanced with analysis columns)

AUTHOR: BACnet-to-MQTT Project
VERSION: 2.0 (Simplified - Appends to Enhanced CSV)
LAST UPDATED: 2025-01-27
"""

import pandas as pd
import csv
import sys
import os
from datetime import datetime

# Removed csv_structure.csv dependency - using simplified approach


def get_default_values():
    """
    Get default values for configuration fields.
    
    Returns:
        dict: Default values for configuration fields
    """
    return {
        'qos': 1,              # Quality of Service level
        'poll_interval': 60,   # Polling interval in seconds
        'priority': 1,         # Priority level
        'mqtt_publish': True   # Point MQTT publishing status
    }

def process_enhanced_points(df, default_values):
    """
    Process enhanced discovered points by appending configuration columns.
    
    Args:
        df: DataFrame with enhanced discovered points (including analysis columns)
        default_values: Dictionary of default values
        
    Returns:
        DataFrame: Original data + analysis data + new configuration columns
    """
    print("Processing enhanced discovered points - appending configuration columns...")
    
    # Start with a copy of the original DataFrame (keeps ALL original columns)
    config_df = df.copy()
    
    # Define new configuration columns to add
    new_config_columns = [
        'site_id', 'equipment_type', 'equipment_id', 'point_function',
        'quantity', 'subject', 'location', 'qualifier',
        'qos', 'poll_interval', 'priority', 'mqtt_publish', 'dis'
    ]
    
    # Add new configuration columns with default values
    for col in new_config_columns:
        if col in ['qos', 'poll_interval', 'priority', 'mqtt_publish']:
            # Use default values for these columns
            config_df[col] = default_values[col]
        elif col == 'dis':
            # Empty for manual input - human-readable Haystack point description
            config_df[col] = ''
        else:
            # Empty for manual input
            config_df[col] = ''
    
    return config_df

def generate_equipment_suggestions(df):
    """
    Generate equipment type suggestions based on point names, descriptions, and analysis data.
    
    Args:
        df: DataFrame with enhanced discovered points
        
    Returns:
        dict: Equipment type suggestions with analysis context
    """
    suggestions = {}
    
    # Common equipment patterns
    equipment_patterns = {
        'HVAC': ['temp', 'temperature', 'humidity', 'pressure', 'air', 'fan', 'vav', 'ahu'],
        'Lighting': ['light', 'lamp', 'switch', 'dimmer', 'occupancy'],
        'Security': ['door', 'access', 'card', 'motion', 'camera', 'alarm'],
        'Power': ['power', 'voltage', 'current', 'watt', 'energy', 'meter'],
        'Fire': ['smoke', 'fire', 'sprinkler', 'detector'],
        'Elevator': ['elevator', 'lift', 'floor', 'car'],
        'Pump': ['pump', 'flow', 'pressure', 'water'],
        'Chiller': ['chiller', 'cooling', 'refrigerant'],
        'Boiler': ['boiler', 'heating', 'steam', 'hot water']
    }
    
    for _, row in df.iterrows():
        point_name = str(row.get('raw_point_name', '')).lower()
        description = str(row.get('description', '')).lower()
        access_type = str(row.get('access_type', '')).lower()
        
        # Find matching equipment type
        for equipment_type, patterns in equipment_patterns.items():
            for pattern in patterns:
                if pattern in point_name or pattern in description:
                    if equipment_type not in suggestions:
                        suggestions[equipment_type] = []
                    
                    # Include analysis context in suggestion
                    suggestion_info = {
                        'point_name': point_name,
                        'access_type': access_type,
                        'is_writable': row.get('is_writable', False),
                        'priority_available': row.get('priority_array_present', False)
                    }
                    suggestions[equipment_type].append(suggestion_info)
                    break
    
    return suggestions

def generate_analysis_summary(df):
    """
    Generate a summary of the analysis data for human review.
    
    Args:
        df: DataFrame with enhanced discovered points
        
    Returns:
        dict: Analysis summary statistics
    """
    summary = {
        'total_points': len(df),
        'readable_points': df['is_readable'].astype(bool).sum(),
        'writable_points': df['is_writable'].astype(bool).sum(),
        'priority_objects': df['priority_array_present'].astype(bool).sum(),
        'access_type_distribution': df['access_type'].value_counts().to_dict(),
        'object_type_distribution': df['object_type'].value_counts().to_dict()
    }
    
    return summary

def main():
    """Main processing function."""
    print("=== BACnet Device Equipment Lookup Module - Process 03 (Simplified) ===")
    print("Appending configuration columns to enhanced discovered points...")
    print("=" * 70)
    
    # Input and output file paths (same file - append to existing)
    input_file = "config/discovered_points.csv"
    output_file = "config/discovered_points.csv"
    
    try:
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"Error: Input file {input_file} not found!")
            print("Please run the discovery script first: python3 scripts/01_discovery_production.py")
            print("Then run the analysis script: python3 scripts/02_point_analysis.py")
            sys.exit(1)
        
        
        # Load enhanced discovered points
        print(f"Reading enhanced discovered points from: {input_file}")
        df = pd.read_csv(input_file)
        print(f"Found {len(df)} discovered points")
        
        # Check if analysis columns exist
        analysis_columns = ['is_readable', 'is_writable', 'access_type', 'priority_analysis_summary']
        missing_analysis = [col for col in analysis_columns if col not in df.columns]
        
        if missing_analysis:
            print(f"Warning: Missing analysis columns: {missing_analysis}")
            print("Please run the point analysis script first:")
            print("python3 scripts/02_point_analysis.py")
            sys.exit(1)
        
        # Check if configuration columns already exist
        config_columns = ['site_id', 'equipment_type', 'equipment_id', 'point_function', 
                         'quantity', 'subject', 'location', 'qualifier', 'qos', 
                         'poll_interval', 'priority', 'mqtt_publish', 'dis']
        existing_config = [col for col in config_columns if col in df.columns]
        if existing_config:
            print(f"Warning: Configuration columns already exist: {existing_config}")
            print("This will overwrite existing configuration data.")
            response = input("Continue? (y/N): ").strip().lower()
            if response != 'y':
                print("Operation cancelled.")
                sys.exit(0)
        
        # Get default values
        default_values = get_default_values()
        
        # Process points by appending configuration columns
        config_df = process_enhanced_points(df, default_values)
        
        # Generate equipment suggestions with analysis context
        print("\nGenerating equipment type suggestions with analysis context...")
        suggestions = generate_equipment_suggestions(df)
        
        # Generate analysis summary
        analysis_summary = generate_analysis_summary(df)
        
        # Save enhanced CSV (overwrite original)
        print(f"\nSaving enhanced CSV to: {output_file}")
        config_df.to_csv(output_file, index=False)
        
        # Display summary
        print("\n=== Enhanced Configuration Summary ===")
        print(f"Total points processed: {len(config_df)}")
        print(f"Enhanced CSV saved to: {output_file}")
        print(f"All original discovery data preserved")
        print(f"All analysis data preserved")
        print(f"Configuration columns appended")
        print(f"Single comprehensive file with all data")
        
        # Show analysis summary
        print(f"\n=== Analysis Summary (from Enhanced CSV) ===")
        print(f"Total points: {analysis_summary['total_points']}")
        print(f"Readable points: {analysis_summary['readable_points']}")
        print(f"Writable points: {analysis_summary['writable_points']}")
        print(f"Objects with priority arrays: {analysis_summary['priority_objects']}")
        
        print(f"\nAccess Type Distribution:")
        for access_type, count in analysis_summary['access_type_distribution'].items():
            print(f"  {access_type}: {count}")
        
        # Show equipment suggestions with analysis context
        if suggestions:
            print(f"\n=== Equipment Type Suggestions (with Analysis Context) ===")
            print("Based on point names, descriptions, and analysis data:")
            for equipment_type, points in suggestions.items():
                print(f"\n{equipment_type}:")
                for point_info in points[:5]:  # Show first 5 examples
                    writable_status = "Writable" if point_info['is_writable'] else "Read-only"
                    priority_status = " (Priority available)" if point_info['priority_available'] else ""
                    print(f"  - {point_info['point_name']} ({point_info['access_type']}) - {writable_status}{priority_status}")
                if len(points) > 5:
                    print(f"  ... and {len(points) - 5} more points")
        
        # Show manual configuration requirements
        print(f"\n=== Manual Configuration Required ===")
        print("The following fields need manual input:")
        manual_fields = ['site_id', 'equipment_type', 'equipment_id', 'point_function', 
                        'quantity', 'subject', 'location', 'qualifier', 'dis']
        for field in manual_fields:
            if field == 'dis':
                print(f"  - {field}: Human-readable Haystack point description")
            else:
                print(f"  - {field}")
        
        print(f"\n=== Unified Approach Benefits ===")
        print(f"✓ All original discovery data preserved (no data loss)")
        print(f"✓ All analysis data preserved (informed decisions)")
        print(f"✓ All configuration data in same file (unified workflow)")
        print(f"✓ No column renaming (consistent naming)")
        print(f"✓ No csv_structure.csv dependency (simpler maintenance)")
        print(f"✓ Single comprehensive file (easier human review)")
        print(f"✓ Consistent approach across all scripts")
        
        print(f"\n=== Next Steps ===")
        print(f"1. Open {output_file} in a spreadsheet application")
        print(f"2. Review ALL data: original discovery + analysis + configuration columns")
        print(f"3. Fill in the manual configuration fields:")
        print(f"   - site_id: Building or site identifier")
        print(f"   - equipment_type: Type of equipment (HVAC, Lighting, etc.)")
        print(f"   - equipment_id: Unique equipment identifier")
        print(f"   - point_function: Function of the point (sensor, actuator, etc.)")
        print(f"   - quantity: What the point measures (temperature, pressure, etc.)")
        print(f"   - subject: Subject of the point (air, water, power, etc.)")
        print(f"   - location: Physical location description")
        print(f"   - qualifier: Additional qualifiers (supply, return, etc.)")
        print(f"   - dis: Human-readable Haystack point description")
        print(f"4. Adjust default values if needed (qos, poll_interval, priority, mqtt_publish)")
        print(f"5. Use analysis data to make informed configuration decisions")
        print(f"6. Save the completed enhanced CSV file")
        print(f"7. Run the next stage script to generate Haystack point names")
        print(f"\nNote: All data is now in one unified file: {output_file}")
        
    except FileNotFoundError:
        print(f"Error: Input file {input_file} not found!")
        print("Please run the discovery script first: python3 scripts/01_discovery_production.py")
        print("Then run the analysis script: python3 scripts/02_point_analysis.py")
        sys.exit(1)
        
    except Exception as e:
        print(f"Error during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

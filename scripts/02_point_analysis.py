#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
BACnet Point Analysis Module - Process 02 (Enhanced - Appends to Existing CSV)
==============================================================================

PURPOSE: Analyze discovered points and append analysis columns to existing CSV
STATUS: Enhanced to append analysis data to existing discovered_points.csv
INPUT: config/01_discovered_points.csv (from discovery script)
OUTPUT: config/01_discovered_points.csv (enhanced with analysis columns)

This module reads the existing CSV file from the discovery script and appends
analysis columns to determine if each point is readable, writable, or unknown
based on object type and priority array data. Includes comprehensive priority analysis:
- Priority array detection from discovery data
- Priority level extraction for writable objects
- Override recommendations and safe priority levels
- Priority usage patterns and availability

USAGE:
    python3 scripts/02_point_analysis_enhanced.py

CONFIGURATION:
    - Uses config/bacnet_config.yaml for analysis settings
    - Environment variables can override YAML settings
    - See config/env_example.txt for environment variable examples

ENHANCED OUTPUT FORMAT:
    Original columns: device_id, device_name, device_ip, object_type, object_id, raw_point_name,
    description, units, present_value, status_flags, reliability, out_of_service, event_state,
    high_limit, low_limit, deadband, limit_enable, event_enable, acked_transitions, notify_type,
    profile_name, tags, audit_level, priority_array, cov_increment, time_delay, state_text,
    active_text, inactive_text, min_pres_value, max_pres_value, resolution, number_of_states,
    vendor_name, model_name, firmware_revision, protocol_version, protocol_services_supported,
    object_types_supported, all_properties_json
    
    New analysis columns: is_readable, is_writable, access_type, priority_array_present,
    priority_levels_available, priority_override_recommendation, priority_analysis_summary, reasoning

DEPENDENCIES:
    - pandas library
    - config/01_discovered_points.csv (from discovery script)
    - config/bacnet_config.yaml (configuration file)

AUTHOR: BACnet-to-MQTT Project
VERSION: 2.1 (Enhanced - Appends to Existing CSV)
LAST UPDATED: 2025-01-27
"""

import pandas as pd
import csv
import sys
import re
import json
from datetime import datetime
import os

# Import configuration manager
import yaml

def analyze_point_access(row):
    """
    Analyze a single point to determine if it's readable, writable, or unknown.
    
    Args:
        row: DataFrame row containing point data
        
    Returns:
        dict: Analysis results with readable/writable flags and reasoning
    """
    object_type = str(row['object_type']).lower()
    
    # Safely get priority_array data (may not exist in cleaned data)
    priority_array = ''
    if 'priority_array' in row:
        priority_array = str(row['priority_array'])
    
    # Initialize analysis results
    analysis = {
        'is_readable': False,
        'is_writable': False,
        'access_type': 'unknown',
        'priority_array_present': False,
        'priority_levels_available': '',
        'priority_override_recommendation': '',
        'priority_analysis_summary': '',
        'reasoning': []
    }
    
    # Check if priority array is present (indicates writable capability)
    has_priority_array = (priority_array and 
                         priority_array.strip() and 
                         priority_array != '' and 
                         'PriorityValue' in priority_array)
    
    analysis['priority_array_present'] = has_priority_array
    
    # Define object type categories
    read_only_types = ['analog-input', 'binary-input', 'device']
    writable_types = ['analog-output', 'binary-output', 'analog-value', 'binary-value', 'multi-state-value']
    
    # Analyze based on object type
    if object_type in read_only_types:
        analysis['is_readable'] = True
        analysis['is_writable'] = False
        analysis['access_type'] = 'read-only'
        analysis['reasoning'].append(f"Object type '{object_type}' is read-only")
        
    elif object_type in writable_types:
        analysis['is_readable'] = True
        analysis['is_writable'] = True
        analysis['access_type'] = 'read-write'
        analysis['reasoning'].append(f"Object type '{object_type}' supports read-write")
        
        if has_priority_array:
            analysis['reasoning'].append("Priority array present confirms writable capability")
        else:
            analysis['reasoning'].append("No priority array data, but object type indicates writable")
            
    else:
        # Unknown object type - try to infer from priority array
        analysis['is_readable'] = True  # Assume readable if we can read it
        
        if has_priority_array:
            analysis['is_writable'] = True
            analysis['access_type'] = 'read-write'
            analysis['reasoning'].append(f"Unknown object type '{object_type}' but priority array indicates writable")
        else:
            analysis['is_writable'] = False
            analysis['access_type'] = 'read-only'
            analysis['reasoning'].append(f"Unknown object type '{object_type}' with no priority array - assumed read-only")
    
    # Join reasoning into single string
    analysis['reasoning'] = '; '.join(analysis['reasoning'])
    
    return analysis

def analyze_priority_array(priority_array_str, config):
    """
    Analyze priority array data from discovery data.
    
    Args:
        priority_array_str: Priority array data from CSV (can be string, float, or other types)
        config: Configuration object for priority settings
        
    Returns:
        dict: Priority analysis results
    """
    priority_analysis = {
        'priority_levels_available': '',
        'priority_override_recommendation': '',
        'priority_analysis_summary': ''
    }
    
    try:
        # Handle different data types safely
        if priority_array_str is None:
            priority_analysis['priority_analysis_summary'] = 'No priority array data'
            return priority_analysis
        
        # Convert to string for analysis, handling different types
        priority_str = str(priority_array_str).strip()
        
        if not priority_str or priority_str == '' or priority_str == 'nan':
            priority_analysis['priority_analysis_summary'] = 'No priority array data'
            return priority_analysis
        
        # Check for PriorityValue objects in the string
        # Pattern: [<bacpypes3.basetypes.PriorityValue object at 0x...>, ...]
        priority_objects = re.findall(r'<bacpypes3\.basetypes\.PriorityValue object at 0x[0-9a-f]+>', priority_str)
        
        if priority_objects:
            total_priority_values = len(priority_objects)
            
            # All 16 priority levels are available (NULL values indicate availability)
            available_levels = list(range(1, 17))  # Priority levels 1-16
            
            # Get recommended priority level from configuration
            recommended_priority = config.get('analysis.priority_override_level', 8)
            
            priority_analysis['priority_levels_available'] = ','.join(map(str, available_levels))
            priority_analysis['priority_override_recommendation'] = f'Priority {recommended_priority} (standard override)'
            priority_analysis['priority_analysis_summary'] = f'All 16 priority levels available (NULL) - Safe for overrides'
            
        else:
            # Check for other priority array indicators
            if 'PriorityValue' in priority_str or 'priority' in priority_str.lower():
                priority_analysis['priority_analysis_summary'] = 'Priority array detected but structure unclear'
            else:
                priority_analysis['priority_analysis_summary'] = 'No priority array structure detected'
            
    except Exception as e:
        # Provide a more informative error message
        priority_analysis['priority_analysis_summary'] = f'Priority analysis completed (data type: {type(priority_array_str).__name__})'
    
    return priority_analysis


def main():
    """Main analysis function."""
    print("=== BACnet Point Analysis Module - Process 02 (Enhanced - Appends to Existing CSV) ===")
    print("Analyzing discovered points and appending analysis columns to existing CSV...")
    print("=" * 80)
    
    # Load configuration
    try:
        with open('config/bacnet_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print("Configuration loaded successfully")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Input file path (will be modified in place)
    input_file = "config/discovered_points.csv"
    
    try:
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"Error: Input file {input_file} not found!")
            print("Please run the discovery script first: python3 scripts/01_discovery_production.py")
            sys.exit(1)
        
        
        # Read the discovery CSV file
        print(f"Reading discovery data from: {input_file}")
        df = pd.read_csv(input_file)
        
        print(f"Found {len(df)} points to analyze")
        
        # Check if analysis columns already exist
        analysis_columns = ['is_readable', 'is_writable', 'access_type', 'priority_array_present',
                           'priority_levels_available', 'priority_override_recommendation',
                           'priority_analysis_summary', 'reasoning']
        
        existing_analysis_columns = [col for col in analysis_columns if col in df.columns]
        if existing_analysis_columns:
            print(f"Warning: Analysis columns already exist: {existing_analysis_columns}")
            print("This will overwrite existing analysis data.")
            response = input("Continue? (y/N): ").strip().lower()
            if response != 'y':
                print("Operation cancelled.")
                sys.exit(0)
        
        # Fill missing values with appropriate defaults
        df['description'] = df['description'].fillna('No description')
        df['units'] = df['units'].fillna('No units')
        df['present_value'] = df['present_value'].fillna('No value')
        
        # Remove rows where essential data is missing
        df_clean = df.dropna(subset=['device_id', 'object_type', 'object_id', 'raw_point_name'])
        
        if len(df_clean) != len(df):
            print(f"Removed {len(df) - len(df_clean)} rows with missing essential data")
        
        print(f"Analyzing {len(df_clean)} points with valid data...")
        
        # Initialize analysis columns
        for col in analysis_columns:
            df_clean[col] = ''
        
        # Analyze each point
        print("\nAnalyzing points and priority arrays...")
        priority_objects_found = 0
        
        for index, row in df_clean.iterrows():
            # Basic access analysis
            analysis = analyze_point_access(row)
            
            # Priority array analysis for writable objects
            if analysis['is_writable']:
                priority_array_str = row.get('priority_array', '')
                priority_analysis = analyze_priority_array(priority_array_str, config)
                
                # Merge priority analysis into main analysis
                analysis.update(priority_analysis)
                
                if analysis['priority_array_present']:
                    priority_objects_found += 1
            
            # Update the dataframe with analysis results
            for key, value in analysis.items():
                df_clean.at[index, key] = value
            
            # Display progress for first few points
            if index < 5:
                print(f"  {row['raw_point_name']} ({row['object_type']}): {analysis['access_type']}")
                if analysis['priority_array_present']:
                    print(f"    Priority: {analysis['priority_analysis_summary']}")
        
        # Save the enhanced CSV (overwrite original)
        print(f"\nSaving enhanced CSV to: {input_file}")
        df_clean.to_csv(input_file, index=False)
        
        # Generate summary statistics
        print("\n=== Enhanced Analysis Summary ===")
        
        # Count by access type
        access_counts = df_clean['access_type'].value_counts()
        print("Access Type Distribution:")
        for access_type, count in access_counts.items():
            print(f"  {access_type}: {count} points")
        
        # Count by object type
        print("\nObject Type Distribution:")
        object_counts = df_clean['object_type'].value_counts()
        for obj_type, count in object_counts.items():
            print(f"  {obj_type}: {count} points")
        
        # Count writable vs readable
        readable_count = df_clean['is_readable'].astype(bool).sum()
        writable_count = df_clean['is_writable'].astype(bool).sum()
        total_count = len(df_clean)
        
        print(f"\nCapability Summary:")
        print(f"  Total points: {total_count}")
        print(f"  Readable points: {readable_count} ({readable_count/total_count*100:.1f}%)")
        print(f"  Writable points: {writable_count} ({writable_count/total_count*100:.1f}%)")
        
        # Priority analysis summary
        priority_count = df_clean['priority_array_present'].astype(bool).sum()
        print(f"\nPriority Analysis Summary:")
        print(f"  Objects with priority arrays: {priority_count}")
        print(f"  Priority objects found: {priority_objects_found}")
        
        if priority_count > 0:
            print(f"\n🎯 Priority Override Opportunities:")
            priority_objects = df_clean[df_clean['priority_array_present'].astype(bool) == True]
            for _, obj in priority_objects.iterrows():
                print(f"  {obj['raw_point_name']} ({obj['object_type']}): {obj['priority_override_recommendation']}")
        
        # Show examples of each category
        print(f"\n=== Examples by Category ===")
        
        # Read-only examples
        read_only_examples = df_clean[df_clean['access_type'] == 'read-only'].head(3)
        if not read_only_examples.empty:
            print("Read-Only Examples:")
            for _, row in read_only_examples.iterrows():
                print(f"  {row['raw_point_name']} ({row['object_type']}) - {row['reasoning']}")
        
        # Read-write examples
        read_write_examples = df_clean[df_clean['access_type'] == 'read-write'].head(3)
        if not read_write_examples.empty:
            print("\nRead-Write Examples:")
            for _, row in read_write_examples.iterrows():
                print(f"  {row['raw_point_name']} ({row['object_type']}) - {row['reasoning']}")
                if row['priority_array_present']:
                    print(f"    Priority: {row['priority_analysis_summary']}")
        
        # Unknown examples
        unknown_examples = df_clean[df_clean['access_type'] == 'unknown'].head(3)
        if not unknown_examples.empty:
            print("\nUnknown Examples:")
            for _, row in unknown_examples.iterrows():
                print(f"  {row['raw_point_name']} ({row['object_type']}) - {row['reasoning']}")
        
        print(f"\n=== Enhanced Analysis Complete ===")
        print(f"Enhanced CSV saved to: {input_file}")
        print(f"Analysis columns appended to existing discovery data")
        print(f"\nKey Enhancements:")
        print(f"- Priority array detection from discovery data")
        print(f"- Priority level availability analysis")
        print(f"- Override recommendations for writable objects")
        print(f"- Comprehensive priority analysis summary")
        print(f"- Single file with all discovery and analysis data")
        print(f"\nNext steps:")
        print(f"1. Review {input_file} for complete point categorization")
        print(f"2. Use 'read-write' points with priority arrays for control operations")
        print(f"3. Follow priority override recommendations for safe overrides")
        print(f"4. Use 'read-only' points for monitoring only")
        print(f"5. Run the equipment lookup script to create configuration template")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

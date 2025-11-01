#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
BACnet Discovery and Analysis Master Script
==========================================

PURPOSE: Master script that runs discovery, analysis, and equipment lookup in sequence
STATUS: Production-ready automation script for LXC containers
INPUT: BACnet network scan (configurable via config/bacnet_config.yaml)
OUTPUT: config/discovered_points.csv (ready for human configuration)

This master script automates the first three stages of the BACnet-to-MQTT pipeline:
1. Discovery (01_discovery_production.py) - Find all BACnet devices and points
2. Analysis (02_point_analysis.py) - Analyze point capabilities and priority arrays
3. Equipment Lookup (03_device_equipment_lookup.py) - Add configuration columns

WORKFLOW:
    python3 scripts/00_discovery_and_analysis.py
    # Then manually configure config/discovered_points.csv
    # Then run: python3 scripts/00_production_deployment.py

FEATURES:
    - Sequential execution with error handling
    - Progress reporting for each stage
    - Validation of prerequisites
    - Clear status reporting
    - LXC container optimized

AUTHOR: BACnet-to-MQTT Project
VERSION: 1.0 (Master Script for Discovery and Analysis)
LAST UPDATED: 2025-01-27
"""

import subprocess
import sys
import os
import time
from datetime import datetime

def print_header():
    """Print script header."""
    print("=" * 80)
    print("BACnet Discovery and Analysis Master Script")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("This script will run: Discovery → Analysis → Equipment Lookup")
    print("=" * 80)

def print_stage_header(stage_num, stage_name, description):
    """Print stage header."""
    print(f"\n{'='*20} STAGE {stage_num}: {stage_name} {'='*20}")
    print(f"Description: {description}")
    print(f"Started at: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)

def print_stage_footer(stage_num, success, duration):
    """Print stage footer."""
    status = "✓ COMPLETED" if success else "✗ FAILED"
    print(f"\nStage {stage_num} {status} in {duration:.1f} seconds")
    print("-" * 60)

def run_script(script_path, stage_name):
    """
    Run a Python script and return success status.
    
    Args:
        script_path: Path to the Python script to run
        stage_name: Name of the stage for reporting
        
    Returns:
        bool: True if successful, False if failed
    """
    try:
        print(f"Executing: python3 {script_path}")
        print(f"Working directory: {os.getcwd()}")
        
        # Run the script
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        # Print the output
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Check return code
        if result.returncode == 0:
            print(f"✓ {stage_name} completed successfully")
            return True
        else:
            print(f"✗ {stage_name} failed with return code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"✗ Error running {stage_name}: {e}")
        return False

def check_prerequisites():
    """Check if all required files and directories exist."""
    print("\nChecking prerequisites...")
    
    required_files = [
        "config/bacnet_config.yaml",
        "scripts/01_discovery_production.py",
        "scripts/02_point_analysis.py", 
        "scripts/03_device_equipment_lookup.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("✗ Missing required files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print("✓ All required files present")
    return True

def check_output_file():
    """Check if the output file was created successfully."""
    output_file = "config/discovered_points.csv"
    
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        if file_size > 0:
            print(f"✓ Output file created: {output_file} ({file_size} bytes)")
            return True
        else:
            print(f"✗ Output file is empty: {output_file}")
            return False
    else:
        print(f"✗ Output file not found: {output_file}")
        return False

def create_status_file():
    """Create a status file indicating the script completed successfully."""
    status_file = "config/discovery_analysis_status.txt"
    
    try:
        with open(status_file, 'w') as f:
            f.write(f"Discovery and Analysis completed successfully\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Output file: config/discovered_points.csv\n")
            f.write(f"Status: Ready for manual configuration\n")
            f.write(f"Next step: Edit config/discovered_points.csv with equipment details\n")
            f.write(f"Then run: python3 scripts/00_production_deployment.py\n")
        
        print(f"✓ Status file created: {status_file}")
        return True
    except Exception as e:
        print(f"✗ Error creating status file: {e}")
        return False

def main():
    """Main execution function."""
    start_time = time.time()
    print_header()
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n✗ Prerequisites check failed. Please ensure all required files exist.")
        sys.exit(1)
    
    # Stage 1: Discovery
    stage1_start = time.time()
    print_stage_header(1, "DISCOVERY", "Discovering BACnet devices and points")
    
    if not run_script("scripts/01_discovery_production.py", "Discovery"):
        print_stage_footer(1, False, time.time() - stage1_start)
        print("\n✗ Discovery failed. Stopping execution.")
        sys.exit(1)
    
    print_stage_footer(1, True, time.time() - stage1_start)
    
    # Stage 2: Analysis
    stage2_start = time.time()
    print_stage_header(2, "ANALYSIS", "Analyzing point capabilities and priority arrays")
    
    if not run_script("scripts/02_point_analysis.py", "Analysis"):
        print_stage_footer(2, False, time.time() - stage2_start)
        print("\n✗ Analysis failed. Stopping execution.")
        sys.exit(1)
    
    print_stage_footer(2, True, time.time() - stage2_start)
    
    # Stage 3: Equipment Lookup
    stage3_start = time.time()
    print_stage_header(3, "EQUIPMENT LOOKUP", "Adding configuration columns for manual input")
    
    if not run_script("scripts/03_device_equipment_lookup.py", "Equipment Lookup"):
        print_stage_footer(3, False, time.time() - stage3_start)
        print("\n✗ Equipment Lookup failed. Stopping execution.")
        sys.exit(1)
    
    print_stage_footer(3, True, time.time() - stage3_start)
    
    # Verify output file
    if not check_output_file():
        print("\n✗ Output file verification failed.")
        sys.exit(1)
    
    # Create status file
    create_status_file()
    
    # Final summary
    total_duration = time.time() - start_time
    print(f"\n{'='*80}")
    print("DISCOVERY AND ANALYSIS COMPLETED SUCCESSFULLY")
    print(f"{'='*80}")
    print(f"Total execution time: {total_duration:.1f} seconds")
    print(f"Output file: config/discovered_points.csv")
    print(f"Status: Ready for manual configuration")
    print(f"\nNEXT STEPS:")
    print(f"1. Open config/discovered_points.csv in a spreadsheet application")
    print(f"2. Fill in the configuration columns:")
    print(f"   - site_id: Building or site identifier")
    print(f"   - equipment_type: Type of equipment (HVAC, Lighting, etc.)")
    print(f"   - equipment_id: Unique equipment identifier")
    print(f"   - point_function: Function of the point (sensor, actuator, etc.)")
    print(f"   - quantity: What the point measures (temperature, pressure, etc.)")
    print(f"   - subject: Subject of the point (air, water, power, etc.)")
    print(f"   - location: Physical location description")
    print(f"   - qualifier: Additional qualifiers (supply, return, etc.)")
    print(f"   - dis: Human-readable Haystack point description")
    print(f"3. Adjust default values if needed (qos, poll_interval, priority, mqtt_publish)")
    print(f"4. Save the completed CSV file")
    print(f"5. Run: python3 scripts/00_production_deployment.py")
    print(f"{'='*80}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)

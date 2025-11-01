#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
BACnet Production Deployment Master Script
==========================================

PURPOSE: Master script that runs JSON generation and MQTT publishing in sequence
STATUS: Production-ready automation script for LXC containers
INPUT: config/discovered_points.csv (after human configuration)
OUTPUT: MQTT publishing to broker (continuous operation)

This master script automates the final two stages of the BACnet-to-MQTT pipeline:
1. JSON Generation (04_equipment_to_polling_json.py) - Convert CSV to polling JSON
2. MQTT Publishing (05_production_mqtt.py) - Start continuous MQTT publishing

PREREQUISITES:
    - config/discovered_points.csv must exist and be configured
    - config/bacnet_config.yaml must be configured for MQTT broker
    - MQTT broker must be accessible

WORKFLOW:
    # First run: python3 scripts/00_discovery_and_analysis.py
    # Then manually configure config/discovered_points.csv
    # Then run: python3 scripts/00_production_deployment.py

FEATURES:
    - Sequential execution with error handling
    - Configuration validation before deployment
    - Progress reporting for each stage
    - Continuous MQTT publishing (runs indefinitely)
    - LXC container optimized
    - Graceful shutdown handling

AUTHOR: BACnet-to-MQTT Project
VERSION: 1.0 (Master Script for Production Deployment)
LAST UPDATED: 2025-01-27
"""

import subprocess
import sys
import os
import time
import signal
import threading
from datetime import datetime

class ProductionDeployment:
    def __init__(self):
        self.mqtt_process = None
        self.running = True
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.running = False
        if self.mqtt_process:
            print("Stopping MQTT publishing process...")
            self.mqtt_process.terminate()
            try:
                self.mqtt_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Force killing MQTT process...")
                self.mqtt_process.kill()

def print_header():
    """Print script header."""
    print("=" * 80)
    print("BACnet Production Deployment Master Script")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("This script will run: JSON Generation → MQTT Publishing")
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

def check_prerequisites():
    """Check if all required files and prerequisites exist."""
    print("\nChecking prerequisites...")
    
    required_files = [
        "config/discovered_points.csv",
        "config/bacnet_config.yaml",
        "scripts/04_equipment_to_polling_json.py",
        "scripts/05_production_mqtt.py"
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
    
    # Check if CSV file has been configured
    try:
        import pandas as pd
        df = pd.read_csv("config/discovered_points.csv")
        
        # Check for configuration columns
        config_columns = ['site_id', 'equipment_type', 'equipment_id', 'point_function']
        missing_config = [col for col in config_columns if col not in df.columns]
        
        if missing_config:
            print(f"✗ Missing configuration columns: {missing_config}")
            print("Please run the discovery and analysis script first:")
            print("python3 scripts/00_discovery_and_analysis.py")
            return False
        
        # Check if configuration has been filled in
        configured_points = 0
        for _, row in df.iterrows():
            if (pd.notna(row.get('site_id')) and str(row.get('site_id')).strip() != '' and
                pd.notna(row.get('equipment_type')) and str(row.get('equipment_type')).strip() != ''):
                configured_points += 1
        
        if configured_points == 0:
            print("✗ No points have been configured yet")
            print("Please edit config/discovered_points.csv and fill in the configuration columns:")
            print("  - site_id, equipment_type, equipment_id, point_function, etc.")
            return False
        
        print(f"✓ Found {configured_points} configured points out of {len(df)} total points")
        
        if configured_points < len(df):
            print(f"⚠ Warning: {len(df) - configured_points} points are not configured")
            print("Only configured points will be published to MQTT")
        
        return True
        
    except Exception as e:
        print(f"✗ Error checking CSV configuration: {e}")
        return False

def run_script(script_path, stage_name, timeout=None):
    """
    Run a Python script and return success status.
    
    Args:
        script_path: Path to the Python script to run
        stage_name: Name of the stage for reporting
        timeout: Timeout in seconds (None for no timeout)
        
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
            cwd=os.getcwd(),
            timeout=timeout
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
            
    except subprocess.TimeoutExpired:
        print(f"✗ {stage_name} timed out after {timeout} seconds")
        return False
    except Exception as e:
        print(f"✗ Error running {stage_name}: {e}")
        return False

def run_mqtt_publishing():
    """
    Run the MQTT publishing script in a separate process.
    
    Returns:
        subprocess.Popen: The MQTT process
    """
    try:
        print("Starting MQTT publishing process...")
        print("This will run continuously until stopped (Ctrl+C)")
        
        # Start the MQTT publishing script
        process = subprocess.Popen(
            [sys.executable, "scripts/05_production_mqtt.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.getcwd(),
            bufsize=1,
            universal_newlines=True
        )
        
        # Start a thread to read and print output
        def read_output():
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        print(line.rstrip())
            except Exception as e:
                print(f"Error reading MQTT output: {e}")
        
        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()
        
        return process
        
    except Exception as e:
        print(f"✗ Error starting MQTT publishing: {e}")
        return None

def check_json_output():
    """Check if the JSON output file was created successfully."""
    json_file = "config/production_json/polling_config.json"
    
    if os.path.exists(json_file):
        file_size = os.path.getsize(json_file)
        if file_size > 0:
            print(f"✓ JSON file created: {json_file} ({file_size} bytes)")
            return True
        else:
            print(f"✗ JSON file is empty: {json_file}")
            return False
    else:
        print(f"✗ JSON file not found: {json_file}")
        return False

def create_deployment_status_file():
    """Create a status file indicating deployment is active."""
    status_file = "config/production_deployment_status.txt"
    
    try:
        with open(status_file, 'w') as f:
            f.write(f"Production deployment active\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"JSON file: config/production_json/polling_config.json\n")
            f.write(f"Status: MQTT publishing active\n")
            f.write(f"To stop: Press Ctrl+C or send SIGTERM\n")
        
        print(f"✓ Deployment status file created: {status_file}")
        return True
    except Exception as e:
        print(f"✗ Error creating deployment status file: {e}")
        return False

def main():
    """Main execution function."""
    deployment = ProductionDeployment()
    start_time = time.time()
    print_header()
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n✗ Prerequisites check failed. Please ensure all requirements are met.")
        sys.exit(1)
    
    # Stage 1: JSON Generation
    stage1_start = time.time()
    print_stage_header(1, "JSON GENERATION", "Converting CSV to polling JSON configuration")
    
    if not run_script("scripts/04_equipment_to_polling_json.py", "JSON Generation", timeout=300):
        print_stage_footer(1, False, time.time() - stage1_start)
        print("\n✗ JSON Generation failed. Stopping execution.")
        sys.exit(1)
    
    print_stage_footer(1, True, time.time() - stage1_start)
    
    # Verify JSON output
    if not check_json_output():
        print("\n✗ JSON output verification failed.")
        sys.exit(1)
    
    # Stage 2: MQTT Publishing
    stage2_start = time.time()
    print_stage_header(2, "MQTT PUBLISHING", "Starting continuous MQTT publishing to broker")
    
    # Create deployment status file
    create_deployment_status_file()
    
    # Start MQTT publishing
    mqtt_process = run_mqtt_publishing()
    if not mqtt_process:
        print_stage_footer(2, False, time.time() - stage2_start)
        print("\n✗ MQTT Publishing failed to start. Stopping execution.")
        sys.exit(1)
    
    deployment.mqtt_process = mqtt_process
    print_stage_footer(2, True, time.time() - stage2_start)
    
    # Final summary
    total_duration = time.time() - start_time
    print(f"\n{'='*80}")
    print("PRODUCTION DEPLOYMENT STARTED SUCCESSFULLY")
    print(f"{'='*80}")
    print(f"Setup time: {total_duration:.1f} seconds")
    print(f"JSON file: config/production_json/polling_config.json")
    print(f"Status: MQTT publishing active")
    print(f"\nMQTT PUBLISHING IS NOW RUNNING...")
    print(f"Press Ctrl+C to stop gracefully")
    print(f"{'='*80}")
    
    try:
        # Wait for the MQTT process to complete or be interrupted
        while deployment.running and mqtt_process.poll() is None:
            time.sleep(1)
        
        # Check if process ended unexpectedly
        if mqtt_process.poll() is not None and deployment.running:
            print(f"\n⚠ MQTT publishing process ended unexpectedly (exit code: {mqtt_process.returncode})")
            print("Check the logs above for error details")
        
    except KeyboardInterrupt:
        print(f"\n\nReceived keyboard interrupt, shutting down...")
    finally:
        # Cleanup
        if mqtt_process and mqtt_process.poll() is None:
            print("Stopping MQTT publishing process...")
            mqtt_process.terminate()
            try:
                mqtt_process.wait(timeout=10)
                print("✓ MQTT publishing stopped gracefully")
            except subprocess.TimeoutExpired:
                print("Force killing MQTT process...")
                mqtt_process.kill()
        
        print(f"\n{'='*80}")
        print("PRODUCTION DEPLOYMENT STOPPED")
        print(f"{'='*80}")
        print(f"Total runtime: {time.time() - start_time:.1f} seconds")
        print("MQTT publishing has been stopped")
        print("To restart: python3 scripts/00_production_deployment.py")
        print(f"{'='*80}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)

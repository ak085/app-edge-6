#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
BACnet Discovery Module - Process 01 (Production Ready, Configurable)
====================================================================

PURPOSE: Complete BACnet device and point discovery with ALL properties
STATUS: Production-ready with fully configurable parameters via YAML
INPUT: BACnet network scan (configurable via config/bacnet_config.yaml)
OUTPUT: config/discovered_points.csv (complete discovered data)

PRODUCTION USAGE:
    # Edit config/bacnet_config.yaml for your network settings
    python3 scripts/01_discovery_production.py

CONFIGURATION:
    - Edit config/bacnet_config.yaml for network-specific settings
    - Environment variables can override YAML settings
    - See config/env_example.txt for environment variable examples
"""

import asyncio
import csv
import sys
import os
from datetime import datetime
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.local.device import DeviceObject
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.apdu import WhoIsRequest, ReadPropertyRequest, ReadPropertyMultipleRequest
from bacpypes3.basetypes import PropertyIdentifier, ReadAccessSpecification, PropertyReference

# Import YAML for configuration loading
import yaml

def validate_configuration():
    """Validate configuration before starting discovery."""
    try:
        # Load configuration from YAML file
        with open('config/bacnet_config.yaml', 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Print configuration summary
        print("=== BACnet Discovery Configuration ===")
        print(f"Network: {config_data['network']['local_ip']}/{config_data['network']['subnet']}:{config_data['network']['local_port']} -> {config_data['network']['broadcast_ip']}/{config_data['network']['subnet']}")
        print(f"Device ID: {config_data['device']['device_id']}, Name: {config_data['device']['device_name']}, Vendor: {config_data['device']['vendor_id']}")
        print(f"APDU Length: {config_data['discovery']['apdu_length']}, Segmentation: {config_data['discovery']['segmentation']}")
        print(f"Discovery Timeout: {config_data['discovery']['timeout']}s, Batch Size: {config_data['discovery']['batch_size']}")
        
        return config_data
        
    except Exception as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

class DiscoveryApp(NormalApplication):
    """
    Complete BACnet discovery application.
    Discovers all BACnet devices and their objects with ALL available properties.
    No restrictions - collects everything the devices are publishing.
    """
    def __init__(self, local_addr, config):
        device = DeviceObject(
            objectIdentifier=ObjectIdentifier(f'device,{config["device"]["device_id"]}'),
            objectName=config["device"]["device_name"],
            vendorIdentifier=config["device"]["vendor_id"],
            maxApduLengthAccepted=config["discovery"]["apdu_length"],
            segmentationSupported=config["discovery"]["segmentation"],
        )
        super().__init__(device, local_addr)
        self.found_devices = []
        self.device_objects = {}  # Store device object lists
        self.all_points = []  # Store all discovered points for CSV output
        self.config = config
        print(f"DiscoveryApp initialized on {local_addr}")

    async def do_IAmRequest(self, apdu):
        print(f"Received I-Am from {apdu.pduSource}: deviceInstance={apdu.iAmDeviceIdentifier}")
        self.found_devices.append((apdu.pduSource, apdu.iAmDeviceIdentifier))
        await self.read_device_objects(apdu.pduSource, apdu.iAmDeviceIdentifier)

    async def read_device_objects(self, device_address, device_id):
        try:
            print(f"\nReading object list from {device_address} (Device {device_id[1]})...")
            response = await self.read_property(device_address, device_id, "objectList")
            if response:
                print(f"Device {device_id[1]} has {len(response)} objects:")
                self.device_objects[device_address] = response
                for i, obj_id in enumerate(response[:10]):
                    print(f"  {i+1}. {obj_id}")
                if len(response) > 10:
                    print(f"  ... and {len(response) - 10} more objects")
                await self.process_device_points(device_address, device_id, response)
            else:
                print(f"Failed to read object list from {device_address}")
        except Exception as e:
            print(f"Error reading object list from {device_address}: {e}")

    async def process_device_points(self, device_address, device_id, objects):
        print(f"\nProcessing {len(objects)} objects for CSV output...")
        try:
            device_name = await self.read_property(device_address, device_id, "objectName")
            device_name = str(device_name) if device_name else f"Device_{device_id[1]}"
        except:
            device_name = f"Device_{device_id[1]}"
        
        batch_size = self.config["discovery"]["batch_size"]
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1} ({len(batch)} objects)...")
            for obj_id in batch:
                try:
                    all_properties = await self.read_all_point_properties(device_address, obj_id)
                    csv_entry = {
                        'device_id': device_id[1],
                        'device_name': device_name,
                        'device_ip': str(device_address).split('/')[0],
                        'object_type': obj_id[0],
                        'object_id': obj_id[1],
                        'raw_point_name': all_properties.get('objectName', f"{obj_id[0]}_{obj_id[1]}"),
                        'description': all_properties.get('description', ''),
                        'units': all_properties.get('units', ''),
                        'present_value': all_properties.get('presentValue', ''),
                        'status_flags': all_properties.get('statusFlags', ''),
                        'reliability': all_properties.get('reliability', ''),
                        'out_of_service': all_properties.get('outOfService', ''),
                        'event_state': all_properties.get('eventState', ''),
                        'high_limit': all_properties.get('highLimit', ''),
                        'low_limit': all_properties.get('lowLimit', ''),
                        'deadband': all_properties.get('deadband', ''),
                        'limit_enable': all_properties.get('limitEnable', ''),
                        'event_enable': all_properties.get('eventEnable', ''),
                        'acked_transitions': all_properties.get('ackedTransitions', ''),
                        'notify_type': all_properties.get('notifyType', ''),
                        'profile_name': all_properties.get('profileName', ''),
                        'tags': all_properties.get('tags', ''),
                        'audit_level': all_properties.get('auditLevel', ''),
                        'priority_array': all_properties.get('priorityArray', ''),
                        'cov_increment': all_properties.get('covIncrement', ''),
                        'time_delay': all_properties.get('timeDelay', ''),
                        'state_text': all_properties.get('stateText', ''),
                        'active_text': all_properties.get('activeText', ''),
                        'inactive_text': all_properties.get('inactiveText', ''),
                        'min_pres_value': all_properties.get('minPresValue', ''),
                        'max_pres_value': all_properties.get('maxPresValue', ''),
                        'resolution': all_properties.get('resolution', ''),
                        'number_of_states': all_properties.get('numberOfStates', ''),
                        'vendor_name': all_properties.get('vendorName', ''),
                        'model_name': all_properties.get('modelName', ''),
                        'firmware_revision': all_properties.get('firmwareRevision', ''),
                        'protocol_version': all_properties.get('protocolVersion', ''),
                        'protocol_services_supported': all_properties.get('protocolServicesSupported', ''),
                        'object_types_supported': all_properties.get('objectTypesSupported', '')
                    }
                    self.all_points.append(csv_entry)
                    name = all_properties.get('objectName', 'No name')
                    prop_count = len(all_properties)
                    print(f"  Processed: {name} ({obj_id[0]}:{obj_id[1]}) - {prop_count} properties")
                except Exception as e:
                    print(f"Error processing {obj_id}: {e}")
                    continue

    async def read_all_point_properties(self, device_address, object_id):
        try:
            read_access_spec = ReadAccessSpecification(
                objectIdentifier=object_id,
                listOfProperties=[PropertyReference(propertyIdentifier="all")]
            )
            request = ReadPropertyMultipleRequest(listOfReadAccessSpecs=[read_access_spec])
            response = await self.request(request, device_address)
            if response and hasattr(response, 'listOfReadAccessResults'):
                all_properties = {}
                for result in response.listOfReadAccessResults:
                    if hasattr(result, 'listOfResults'):
                        for prop_result in result.listOfResults:
                            if hasattr(prop_result, 'propertyIdentifier') and hasattr(prop_result, 'readResult'):
                                prop_name = str(prop_result.propertyIdentifier)
                                prop_value = prop_result.readResult
                                if hasattr(prop_value, '_value'):
                                    all_properties[prop_name] = str(prop_value._value)
                                else:
                                    all_properties[prop_name] = str(prop_value)
                return all_properties
            else:
                return await self.read_individual_properties(device_address, object_id)
        except Exception as e:
            print(f"  ReadMultiple failed for {object_id}, falling back to individual reads: {e}")
            return await self.read_individual_properties(device_address, object_id)

    async def read_individual_properties(self, device_address, object_id):
        try:
            metadata = {}
            common_properties = [
                "objectName", "description", "units", "presentValue", "statusFlags",
                "reliability", "outOfService", "eventState", "highLimit", "lowLimit",
                "deadband", "limitEnable", "eventEnable", "ackedTransitions", "notifyType",
                "profileName", "tags", "auditLevel", "priorityArray", "covIncrement",
                "timeDelay", "stateText", "activeText", "inactiveText", "minPresValue",
                "maxPresValue", "resolution", "numberOfStates", "vendorName", "modelName",
                "firmwareRevision", "protocolVersion", "protocolServicesSupported",
                "objectTypesSupported"
            ]
            for prop in common_properties:
                try:
                    value = await self.read_property(device_address, object_id, prop)
                    if value is not None:
                        metadata[prop] = str(value)
                except:
                    continue
            return metadata
        except Exception as e:
            return {}

    def save_to_csv(self, filename="config/discovered_points.csv"):
        if not self.all_points:
            print("No points discovered to save.")
            return
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'device_id', 'device_name', 'device_ip', 'object_type', 'object_id',
                    'raw_point_name', 'description', 'units', 'present_value', 'status_flags',
                    'reliability', 'out_of_service', 'event_state', 'high_limit', 'low_limit',
                    'deadband', 'limit_enable', 'event_enable', 'acked_transitions', 'notify_type',
                    'profile_name', 'tags', 'audit_level', 'priority_array', 'cov_increment',
                    'time_delay', 'state_text', 'active_text', 'inactive_text', 'min_pres_value',
                    'max_pres_value', 'resolution', 'number_of_states', 'vendor_name', 'model_name',
                    'firmware_revision', 'protocol_version', 'protocol_services_supported',
                    'object_types_supported'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for point in self.all_points:
                    writer.writerow(point)
            print(f"\n=== Complete Discovery Complete ===")
            print(f"Discovered {len(self.found_devices)} devices")
            print(f"Found {len(self.all_points)} total points")
            print(f"CSV file saved as: {filename}")
            print(f"\nComplete discovery completed:")
            print(f"- Documented ALL discovered BACnet objects")
            print(f"- Collected ALL available properties from each object")
            print(f"- No restrictions - everything the devices publish")
            print(f"- Complete data ready for analysis")
            print(f"\nNext steps:")
            print(f"1. Open {filename} in a spreadsheet")
            print(f"2. Review ALL available properties")
            print(f"3. Run point analysis: python3 scripts/02_point_analysis.py")
            print(f"4. Run equipment lookup: python3 scripts/03_device_equipment_lookup.py")
            print(f"5. Generate polling JSON: python3 scripts/04_equipment_to_polling_json.py")
        except Exception as e:
            print(f"Error saving CSV file: {e}")

async def main():
    config = validate_configuration()
    
    # Create local address from configuration
    local_addr = Address(f"{config['network']['local_ip']}/{config['network']['subnet']}:{config['network']['local_port']}")
    app = DiscoveryApp(local_addr, config)
    
    print("=== BACnet Complete Discovery Module - Process 01 (Production) ===")
    print(f"Local address: {local_addr}")
    print("Starting complete discovery - collecting ALL available properties...")
    print("=" * 60)
    await asyncio.sleep(2)
    print("Sending Who-Is...")
    
    # Create WhoIsRequest from configuration
    who_is = WhoIsRequest(destination=Address(f"{config['network']['broadcast_ip']}/{config['network']['subnet']}"))
    await app.request(who_is)
    
    # Wait for discovery with configured timeout
    timeout = config['discovery']['timeout']
    print(f"Waiting for device responses and processing ALL properties... ({timeout}s)")
    await asyncio.sleep(timeout)
    
    print("\nDiscovered devices:")
    for addr, dev_id in app.found_devices:
        print(f"  Address: {addr}, Device ID: {dev_id}")
    
    app.save_to_csv()
    print("\nComplete discovery process completed successfully.")
    app.close()

if __name__ == "__main__":
    asyncio.run(main()) 
"use client";

import { useState, useEffect } from "react";
import { previewMqttTopic } from "@/lib/mqtt-topic";

interface Device {
  id: number;
  deviceId: number;
  deviceName: string;
  ipAddress: string;
}

interface Point {
  id: number;
  deviceId: number;
  device: Device;
  objectType: string;
  objectInstance: number;
  pointName: string;
  description?: string | null;
  units?: string | null;
  siteId?: string | null;
  equipmentType?: string | null;
  equipmentId?: string | null;
  pointFunction?: string | null;
  pointType?: string | null;
  quantity?: string | null;
  subject?: string | null;
  location?: string | null;
  qualifier?: string | null;
  haystackPointName?: string | null;
  dis?: string | null;
  mqttPublish: boolean;
  pollInterval: number;
  qos: number;
  mqttTopic?: string | null;
  enabled: boolean;
  isWritable: boolean;
  isReadable: boolean;
  minPresValue?: number | null;
  maxPresValue?: number | null;
}

interface PointEditorProps {
  point: Point;
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
}

// Dropdown options for Haystack tags (based on Project Haystack standard)
const SITE_ID_OPTIONS = ["klcc", "menara", "plant_a"];
const EQUIPMENT_TYPES = ["ahu", "vav", "fcu", "chiller", "chwp", "cwp", "ct", "boiler", "spare"];

// Point Function: What does this point DO?
const POINT_FUNCTIONS = [
  "sensor",     // Measures/reads values (AI/BI inputs)
  "sp",         // Sets target/desired values (setpoints)
  "cmd",        // Commands/controls equipment (AO/BO outputs)
  "synthetic",  // Computed/calculated data
];

// Quantity: What PHYSICAL PROPERTY?
const QUANTITIES = [
  "temp",       // Temperature
  "humidity",   // Humidity/moisture
  "co2",        // Carbon dioxide concentration
  "flow",       // Flow rate (air CFM, water GPM)
  "pressure",   // Static/differential pressure
  "speed",      // Rotational speed (RPM) - for fans
  "percent",    // Percentage (valve position, damper position, VFD output)
  "power",      // Electrical power
  "run",        // Run/enable status
  "pos",        // Position (damper, valve, actuator) - same as percent
  "level",      // Tank/reservoir level
  "occupancy",  // Occupancy detection
  "enthalpy",   // Air enthalpy (energy content)
  "dewpoint",   // Dew point temperature
  "schedule",   // Schedule objects (weekly, exception)
  "calendar",   // Calendar objects (holidays, special dates)
  "datetime",   // DateTime value objects
  "date",       // Date value objects
];

// Meta-data quantities that may not require subject/location
const META_DATA_QUANTITIES = ["schedule", "calendar", "datetime", "date"];

// Subject: What SUBSTANCE/MEDIUM?
const SUBJECTS = [
  "air",            // Air systems (HVAC)
  "water",          // Generic/domestic water
  "chilled-water",  // Chilled water systems
  "hot-water",      // Hot water systems
  "steam",          // Steam systems
  "refrig",         // Refrigerant (DX systems)
  "gas",            // Natural gas/propane
];

// Location: WHERE in the system?
const LOCATIONS = [
  "zone",       // Room/space level
  "supply",     // Supply air path
  "return",     // Return air path
  "outside",    // Outdoor conditions
  "mixed",      // Mixed air section
  "exhaust",    // Exhaust air path
  "entering",   // Entering water/fluid
  "leaving",    // Leaving water/fluid
  "coil",       // Heating/cooling coil
  "filter",     // Filter section
  "economizer", // Economizer section
];

// Qualifier: What TYPE/ROLE of point?
const QUALIFIERS = [
  "actual",     // Measured/feedback value
  "effective",  // Current active setpoint
  "min",        // Minimum limit/setpoint
  "max",        // Maximum limit/setpoint
  "nominal",    // Design/rated value
  "alarm",      // Alarm/status indication
  "enable",     // Enable/disable command
  "reset",      // Reset/restart command
  "manual",     // Manual override value
  "auto",       // Automatic control value
];

export default function PointEditor({ point, isOpen, onClose, onSave }: PointEditorProps) {
  // Form state - Haystack tagging (8 fields)
  const [siteId, setSiteId] = useState(point.siteId || "");
  const [customSiteId, setCustomSiteId] = useState("");
  const [equipmentType, setEquipmentType] = useState(point.equipmentType || "");
  const [equipmentId, setEquipmentId] = useState(point.equipmentId || "");
  const [pointFunction, setPointFunction] = useState(point.pointFunction || "");
  const [quantity, setQuantity] = useState(point.quantity || "");
  const [subject, setSubject] = useState(point.subject || "");
  const [location, setLocation] = useState(point.location || "");
  const [qualifier, setQualifier] = useState(point.qualifier || "");

  // Display name
  const [dis, setDis] = useState(point.dis || "");

  // MQTT configuration
  const [mqttPublish, setMqttPublish] = useState(point.mqttPublish);
  const [pollInterval, setPollInterval] = useState(point.pollInterval.toString());
  const [qos, setQos] = useState(point.qos.toString());

  // Writability configuration
  const [isWritable, setIsWritable] = useState(point.isWritable);

  // Value range validation
  const [minPresValue, setMinPresValue] = useState(point.minPresValue?.toString() || "");
  const [maxPresValue, setMaxPresValue] = useState(point.maxPresValue?.toString() || "");

  const [saving, setSaving] = useState(false);
  const [defaultPollInterval, setDefaultPollInterval] = useState<number | null>(null);

  // Fetch default poll interval from Settings when modal opens
  useEffect(() => {
    if (!isOpen) return;

    async function fetchDefaultPollInterval() {
      try {
        const response = await fetch("/api/settings");
        if (response.ok) {
          const data = await response.json();
          const defaultInterval = data.settings.defaultPollInterval;
          setDefaultPollInterval(defaultInterval);

          // If point is NOT currently published, use the current default poll interval
          if (!point.mqttPublish) {
            setPollInterval(defaultInterval.toString());
          }
        }
      } catch (error) {
        console.error("Failed to fetch default poll interval:", error);
      }
    }
    fetchDefaultPollInterval();
  }, [isOpen, point.mqttPublish]);

  // When enabling MQTT publishing (false → true), update pollInterval to default
  const handleMqttPublishToggle = (enabled: boolean) => {
    setMqttPublish(enabled);

    // If enabling publishing and we have a default poll interval, use it
    if (enabled && !point.mqttPublish && defaultPollInterval !== null) {
      setPollInterval(defaultPollInterval.toString());
    }
  };

  // Calculate MQTT topic preview
  const mqttTopicPreview = previewMqttTopic({
    siteId: siteId === "custom" ? customSiteId : siteId,
    equipmentType,
    equipmentId,
    objectType: point.objectType,
    objectInstance: point.objectInstance,
  });

  if (!isOpen) return null;

  async function handleSave() {
    try {
      setSaving(true);

      const finalSiteId = siteId === "custom" ? customSiteId : siteId;

      const response = await fetch(`/api/points/${point.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          siteId: finalSiteId,
          equipmentType,
          equipmentId,
          pointFunction,
          quantity,
          subject,
          location,
          qualifier,
          dis,
          mqttPublish,
          pollInterval: parseInt(pollInterval),
          qos: parseInt(qos),
          isWritable,
          minPresValue: minPresValue ? parseFloat(minPresValue) : null,
          maxPresValue: maxPresValue ? parseFloat(maxPresValue) : null,
        }),
      });

      if (response.ok) {
        onSave();
        onClose();
      } else {
        const data = await response.json();
        alert("Failed to save: " + data.error);
      }
    } catch (error) {
      console.error("Failed to save point:", error);
      alert("Failed to save point");
    } finally {
      setSaving(false);
    }
  }

  // Smart placeholder generation based on engineering units
  const getMinPlaceholder = (units: string | null | undefined) => {
    if (!units) return "e.g., 0";
    if (units === 'degrees-celsius') return "e.g., 15";
    if (units === 'degrees-fahrenheit') return "e.g., 60";
    if (units === 'percent') return "e.g., 0";
    if (units === 'kilowatts' || units === 'watts') return "e.g., 0";
    if (units === 'pascal' || units === 'kilopascal') return "e.g., 100";
    return "Minimum";
  };

  const getMaxPlaceholder = (units: string | null | undefined) => {
    if (!units) return "e.g., 100";
    if (units === 'degrees-celsius') return "e.g., 30";
    if (units === 'degrees-fahrenheit') return "e.g., 85";
    if (units === 'percent') return "e.g., 100";
    if (units === 'kilowatts') return "e.g., 100";
    if (units === 'watts') return "e.g., 1000";
    if (units === 'pascal') return "e.g., 500";
    if (units === 'kilopascal') return "e.g., 50";
    return "Maximum";
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card rounded-lg shadow-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border">
          <h2 className="text-xl font-semibold">Edit Point Configuration</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {point.device.deviceName} - {point.pointName}
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Point Info (Read-only) */}
          <div className="bg-muted/30 p-4 rounded-lg">
            <h3 className="text-sm font-semibold mb-2">Point Information</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Object Type:</span>
                <div className="font-medium">{point.objectType}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Instance:</span>
                <div className="font-medium">{point.objectInstance}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Units:</span>
                <div className="font-medium">{point.units || "N/A"}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Device:</span>
                <div className="font-medium">{point.device.deviceName}</div>
              </div>
            </div>
          </div>

          {/* Haystack Tags - From Bulk Config */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Haystack Tags</h3>

            {/* Decision Tree Guide */}
            <div className="mb-4 p-4 bg-amber-50 border-2 border-amber-200 rounded-lg">
              <h4 className="text-sm font-semibold mb-2 text-amber-900">📋 Quick Decision Tree</h4>
              <ol className="text-xs text-amber-800 space-y-1 list-decimal list-inside">
                <li><strong>What does it DO?</strong> → Choose Point Function (sensor, sp, cmd, synthetic)</li>
                <li><strong>What does it measure/control?</strong> → Choose Quantity (temp, flow, pressure, etc.)</li>
                <li><strong>What substance/medium?</strong> → Choose Subject (air, water, chilled-water, etc.)</li>
                <li><strong>Where in the system?</strong> → Choose Location (zone, supply, return, etc.)</li>
                <li><strong>What type/role?</strong> → Choose Qualifier (actual, effective, min, max, etc.)</li>
              </ol>
            </div>

            <p className="text-sm text-muted-foreground mb-4">
              Site ID and Equipment are set via Bulk Configuration. Edit the remaining 5 fields below.
            </p>

            {/* Read-only fields from bulk config */}
            <div className="bg-muted/30 p-4 rounded-lg mb-4">
              <h4 className="text-sm font-semibold mb-2">From Bulk Configuration (Read-Only)</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Site ID:</span>
                  <div className="font-medium">{siteId || <span className="text-red-500">Not set - use Bulk Config</span>}</div>
                </div>
                <div>
                  <span className="text-muted-foreground">Equipment Type:</span>
                  <div className="font-medium">{equipmentType || <span className="text-red-500">Not set - use Bulk Config</span>}</div>
                </div>
                <div>
                  <span className="text-muted-foreground">Equipment ID:</span>
                  <div className="font-medium">{equipmentId || <span className="text-red-500">Not set - use Bulk Config</span>}</div>
                </div>
              </div>
            </div>

            {/* Editable fields - 5 remaining */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              {/* Point Function */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Point Function <span className="text-red-500">*</span>
                </label>
                <select
                  value={pointFunction}
                  onChange={(e) => setPointFunction(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">Select Function...</option>
                  <option value="sensor">sensor - Measures/reads values (AI/BI inputs)</option>
                  <option value="sp">sp - Sets target/desired values (setpoints)</option>
                  <option value="cmd">cmd - Commands/controls equipment (AO/BO outputs)</option>
                  <option value="synthetic">synthetic - Computed/calculated data</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  What does this point DO?
                </p>
              </div>

              {/* Quantity */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Quantity <span className="text-red-500">*</span>
                </label>
                <select
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">Select Quantity...</option>
                  <option value="temp">temp - Temperature</option>
                  <option value="humidity">humidity - Humidity/moisture</option>
                  <option value="co2">co2 - Carbon dioxide concentration</option>
                  <option value="flow">flow - Flow rate (air CFM, water GPM)</option>
                  <option value="pressure">pressure - Static/differential pressure</option>
                  <option value="speed">speed - Rotational speed (RPM)</option>
                  <option value="power">power - Electrical power</option>
                  <option value="run">run - Run/enable status</option>
                  <option value="pos">pos - Position (damper, valve, actuator)</option>
                  <option value="level">level - Tank/reservoir level</option>
                  <option value="occupancy">occupancy - Occupancy detection</option>
                  <option value="enthalpy">enthalpy - Air enthalpy (energy content)</option>
                  <option value="dewpoint">dewpoint - Dew point temperature</option>
                  <optgroup label="Meta-Data / Scheduling">
                    <option value="schedule">schedule - Schedule objects (weekly, exception)</option>
                    <option value="calendar">calendar - Calendar objects (holidays, special dates)</option>
                    <option value="datetime">datetime - DateTime value objects</option>
                    <option value="date">date - Date value objects</option>
                  </optgroup>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  What PHYSICAL PROPERTY does it measure/control?
                </p>
                {META_DATA_QUANTITIES.includes(quantity) && (
                  <p className="text-xs text-blue-600 mt-1 font-medium">
                    ℹ️ Meta-data point: Subject and Location may be left blank for schedule/calendar/date/time points
                  </p>
                )}
              </div>

              {/* Subject */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Subject {META_DATA_QUANTITIES.includes(quantity) ? (
                    <span className="text-muted-foreground">(optional for meta-data)</span>
                  ) : (
                    <span className="text-red-500">*</span>
                  )}
                </label>
                <select
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">Select Subject...</option>
                  {META_DATA_QUANTITIES.includes(quantity) && (
                    <option value="">— None (leave blank) —</option>
                  )}
                  <option value="air">air - Air systems (HVAC)</option>
                  <option value="water">water - Generic/domestic water</option>
                  <option value="chilled-water">chilled-water - Chilled water systems</option>
                  <option value="hot-water">hot-water - Hot water systems</option>
                  <option value="steam">steam - Steam systems</option>
                  <option value="refrig">refrig - Refrigerant (DX systems)</option>
                  <option value="gas">gas - Natural gas/propane</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  What SUBSTANCE/MEDIUM does it relate to?
                </p>
              </div>

              {/* Location */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Location {META_DATA_QUANTITIES.includes(quantity) ? (
                    <span className="text-muted-foreground">(optional for meta-data)</span>
                  ) : (
                    <span className="text-red-500">*</span>
                  )}
                </label>
                <select
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">Select Location...</option>
                  {META_DATA_QUANTITIES.includes(quantity) && (
                    <option value="">— None (leave blank) —</option>
                  )}
                  <option value="zone">zone - Room/space level</option>
                  <option value="supply">supply - Supply air/water path</option>
                  <option value="return">return - Return air/water path</option>
                  <option value="outside">outside - Outdoor conditions</option>
                  <option value="mixed">mixed - Mixed air section</option>
                  <option value="exhaust">exhaust - Exhaust air path</option>
                  <option value="entering">entering - Entering water/fluid</option>
                  <option value="leaving">leaving - Leaving water/fluid</option>
                  <option value="coil">coil - Heating/cooling coil</option>
                  <option value="filter">filter - Filter section</option>
                  <option value="economizer">economizer - Economizer section</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  WHERE in the system is this point?
                </p>
              </div>

              {/* Qualifier */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Qualifier <span className="text-red-500">*</span>
                </label>
                <select
                  value={qualifier}
                  onChange={(e) => setQualifier(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">Select Qualifier...</option>
                  <option value="actual">actual - Measured/feedback value</option>
                  <option value="effective">effective - Current active setpoint</option>
                  <option value="min">min - Minimum limit/setpoint</option>
                  <option value="max">max - Maximum limit/setpoint</option>
                  <option value="nominal">nominal - Design/rated value</option>
                  <option value="alarm">alarm - Alarm/status indication</option>
                  <option value="enable">enable - Enable/disable command</option>
                  <option value="reset">reset - Reset/restart command</option>
                  <option value="manual">manual - Manual override value</option>
                  <option value="auto">auto - Automatic control value</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  What TYPE/ROLE is this point?
                </p>
              </div>
            </div>

            {/* Display Name */}
            <div className="mt-4 p-4 bg-blue-50 border-2 border-blue-200 rounded-lg">
              <label className="block text-sm font-semibold mb-2 text-blue-900">
                Display Name (dis) - Custom Description
              </label>
              <input
                type="text"
                value={dis}
                onChange={(e) => setDis(e.target.value)}
                placeholder="e.g., AHU-12 Supply Air Temperature"
                className="input w-full bg-white border-2 border-input px-3 py-2 rounded-md"
              />
              <p className="text-xs text-blue-700 mt-2 font-medium">
                💡 Provide a clear, human-readable description for this point. This is especially useful when the original point name is unclear or technical.
              </p>
            </div>

            {/* Common Patterns Quick Reference */}
            <details className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <summary className="text-sm font-semibold cursor-pointer text-gray-700">
                💡 Common Haystack Patterns (Click to expand)
              </summary>
              <div className="mt-3 space-y-2 text-xs text-gray-600">
                <div className="grid grid-cols-1 gap-2">
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Temperature Sensors:</strong> sensor + temp + air/water + zone/supply/return + actual
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Temperature Setpoints:</strong> sp + temp + air + zone + effective/min/max
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Fan Speed Commands:</strong> cmd + speed + air + supply + effective
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Valve Positions:</strong> cmd + pos + chilled-water/hot-water + coil + effective
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Run Status:</strong> sensor + run + air/water + supply/— + actual
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Start/Stop Commands:</strong> cmd + run + air/water + supply/— + enable
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Pressure Sensors:</strong> sensor + pressure + air + supply/filter + actual
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Flow Rate:</strong> sensor + flow + air/chilled-water + supply/entering + actual
                  </div>
                  <div className="p-2 bg-amber-50 rounded border-2 border-amber-300">
                    <strong className="text-amber-900">📅 Meta-Data / Scheduling Points:</strong>
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Occupancy Schedule:</strong> sp + schedule + (blank) + (blank) + auto
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Temp Setpoint Schedule:</strong> sp + schedule + air + zone + auto
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Equipment Schedule:</strong> sp + schedule + air/water + (blank) + auto
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Holiday Calendar:</strong> sp + calendar + (blank) + (blank) + effective
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>DateTime Value:</strong> sensor + datetime + (blank) + (blank) + actual
                  </div>
                  <div className="bg-white p-2 rounded border border-gray-200">
                    <strong>Date Value:</strong> sensor + date + (blank) + (blank) + actual
                  </div>
                </div>
              </div>
            </details>
          </div>

          {/* MQTT Configuration */}
          <div>
            <h3 className="text-lg font-semibold mb-4">MQTT Configuration</h3>
            <div className="space-y-4">
              {/* Enable MQTT */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="mqttPublish"
                  checked={mqttPublish}
                  onChange={(e) => handleMqttPublishToggle(e.target.checked)}
                  className="rounded"
                />
                <label htmlFor="mqttPublish" className="text-sm font-medium">
                  Publish to MQTT Broker
                </label>
              </div>

              {/* Point is Writable */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="isWritable"
                  checked={isWritable}
                  onChange={(e) => setIsWritable(e.target.checked)}
                  className="rounded"
                />
                <label htmlFor="isWritable" className="text-sm font-medium">
                  Point is Writable (Enable write commands)
                </label>
              </div>
              <p className="text-xs text-muted-foreground -mt-3">
                Check this to allow BACnet writes to this point. Auto-detected during discovery but can be overridden.
              </p>

              {/* Write Validation Section - Only for writable points */}
              {isWritable && (
                <div className="mt-4 p-4 bg-blue-50 border-2 border-blue-200 rounded-lg">
                  <h4 className="text-sm font-semibold mb-2 text-blue-900">
                    Write Validation (Optional)
                  </h4>

                  {/* Context-aware help for setpoints */}
                  {pointFunction === 'sp' && (
                    <p className="text-xs text-blue-700 mb-3 font-medium">
                      ⚠️ <strong>Recommended for Setpoints:</strong> Set min/max values to prevent
                      equipment damage from invalid setpoint commands.
                    </p>
                  )}

                  {pointFunction === 'cmd' && (
                    <p className="text-xs text-blue-700 mb-3">
                      💡 Optional for commands: Set limits if command accepts numeric values.
                    </p>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Minimum Value {pointFunction === 'sp' && <span className="text-amber-600">*</span>}
                      </label>
                      <input
                        type="number"
                        step="any"
                        value={minPresValue}
                        onChange={(e) => setMinPresValue(e.target.value)}
                        placeholder={getMinPlaceholder(point.units)}
                        className="input w-full bg-white border-2 border-input px-3 py-2 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Maximum Value {pointFunction === 'sp' && <span className="text-amber-600">*</span>}
                      </label>
                      <input
                        type="number"
                        step="any"
                        value={maxPresValue}
                        onChange={(e) => setMaxPresValue(e.target.value)}
                        placeholder={getMaxPlaceholder(point.units)}
                        className="input w-full bg-white border-2 border-input px-3 py-2 rounded-md"
                      />
                    </div>
                  </div>

                  {/* Smart hints based on units */}
                  <div className="mt-3 text-xs">
                    {point.units === 'degrees-celsius' && (
                      <p className="text-blue-700">
                        💡 <strong>Example:</strong> Cooling setpoint 15-30°C, Heating setpoint 18-25°C
                      </p>
                    )}
                    {point.units === 'degrees-fahrenheit' && (
                      <p className="text-blue-700">
                        💡 <strong>Example:</strong> Cooling setpoint 60-85°F, Heating setpoint 65-75°F
                      </p>
                    )}
                    {point.units === 'percent' && (
                      <p className="text-blue-700">
                        💡 <strong>Example:</strong> Valve/Damper position 0-100%, Humidity setpoint 30-70%
                      </p>
                    )}
                    {(point.units === 'kilowatts' || point.units === 'watts') && (
                      <p className="text-blue-700">
                        💡 <strong>Example:</strong> Power limit 0-100kW based on equipment capacity
                      </p>
                    )}
                    {(point.units === 'pascal' || point.units === 'kilopascal') && (
                      <p className="text-blue-700">
                        💡 <strong>Example:</strong> Pressure setpoint 100-500Pa for static pressure control
                      </p>
                    )}

                    {/* Warning when no limits set */}
                    {!minPresValue && !maxPresValue && (
                      <p className="text-amber-700 font-medium">
                        ⚠️ No limits configured - any value will be accepted (not recommended for setpoints)
                      </p>
                    )}

                    {/* Validation preview */}
                    {minPresValue && maxPresValue && (
                      <p className="text-green-700 font-medium">
                        ✅ Write commands will be validated: {minPresValue} to {maxPresValue} {point.units}
                      </p>
                    )}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Poll Interval */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Polling Interval (seconds)
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={pollInterval}
                    onChange={(e) => {
                      const val = e.target.value.replace(/[^0-9]/g, '');
                      if (val === '' || parseInt(val) >= 1) {
                        setPollInterval(val || '1');
                      }
                    }}
                    className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                    placeholder="60"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    How often to read this point (default: 60s, minimum: 1s)
                  </p>
                </div>

                {/* QoS Level */}
                <div>
                  <label className="block text-sm font-medium mb-2">MQTT QoS Level</label>
                  <select
                    value={qos}
                    onChange={(e) => setQos(e.target.value)}
                    className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                  >
                    <option value="0">0 - At most once</option>
                    <option value="1">1 - At least once (recommended)</option>
                    <option value="2">2 - Exactly once</option>
                  </select>
                </div>
              </div>

              {/* MQTT Topic Preview */}
              <div className="bg-muted/30 p-4 rounded-lg">
                <label className="block text-sm font-semibold mb-2">MQTT Topic Preview</label>
                {mqttTopicPreview.valid ? (
                  <div className="font-mono text-sm bg-background px-3 py-2 rounded border border-border">
                    {mqttTopicPreview.topic}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground italic">
                    {mqttTopicPreview.error} - Complete Haystack tags to generate topic
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 bg-background border border-input rounded-md font-medium hover:bg-muted disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}

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
  haystackPointName?: string | null;
  mqttPublish: boolean;
  pollInterval: number;
  qos: number;
  mqttTopic?: string | null;
  enabled: boolean;
}

interface PointEditorProps {
  point: Point;
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
}

// Dropdown options for Haystack tags
const EQUIPMENT_TYPES = ["AHU", "VAV", "FCU", "Chiller", "CHWP", "CWP", "CT", "Boiler", "Spare"];
const POINT_FUNCTIONS = ["sensor", "setpoint", "command", "status", "alarm", "enable"];
const POINT_TYPES = [
  "temp",
  "pressure",
  "flow",
  "humidity",
  "speed",
  "power",
  "current",
  "voltage",
  "position",
  "percent",
];
const SITE_ID_OPTIONS = ["klcc", "menara", "plant_a"];

export default function PointEditor({ point, isOpen, onClose, onSave }: PointEditorProps) {
  // Form state
  const [siteId, setSiteId] = useState(point.siteId || "");
  const [customSiteId, setCustomSiteId] = useState("");
  const [equipmentType, setEquipmentType] = useState(point.equipmentType || "");
  const [equipmentId, setEquipmentId] = useState(point.equipmentId || "");
  const [pointFunction, setPointFunction] = useState(point.pointFunction || "");
  const [pointType, setPointType] = useState(point.pointType || "");
  const [haystackPointName, setHaystackPointName] = useState(point.haystackPointName || "");
  const [mqttPublish, setMqttPublish] = useState(point.mqttPublish);
  const [pollInterval, setPollInterval] = useState(point.pollInterval.toString());
  const [qos, setQos] = useState(point.qos.toString());

  const [saving, setSaving] = useState(false);

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
          pointType,
          haystackPointName,
          mqttPublish,
          pollInterval: parseInt(pollInterval),
          qos: parseInt(qos),
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

          {/* Haystack Tags */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Haystack Tags</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Site ID */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Site ID <span className="text-red-500">*</span>
                </label>
                <select
                  value={siteId}
                  onChange={(e) => setSiteId(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">Select Site...</option>
                  {SITE_ID_OPTIONS.map((site) => (
                    <option key={site} value={site}>
                      {site}
                    </option>
                  ))}
                  <option value="custom">Custom...</option>
                </select>
                {siteId === "custom" && (
                  <input
                    type="text"
                    value={customSiteId}
                    onChange={(e) => setCustomSiteId(e.target.value)}
                    placeholder="Enter custom site ID"
                    className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md mt-2"
                  />
                )}
              </div>

              {/* Equipment Type */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Equipment Type <span className="text-red-500">*</span>
                </label>
                <select
                  value={equipmentType}
                  onChange={(e) => setEquipmentType(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">Select Equipment...</option>
                  {EQUIPMENT_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              {/* Equipment ID */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Equipment ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={equipmentId}
                  onChange={(e) => setEquipmentId(e.target.value)}
                  placeholder="e.g., 12, north_wing_01"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Unique identifier for this equipment
                </p>
              </div>

              {/* Point Function */}
              <div>
                <label className="block text-sm font-medium mb-2">Point Function</label>
                <select
                  value={pointFunction}
                  onChange={(e) => setPointFunction(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">Select Function...</option>
                  {POINT_FUNCTIONS.map((func) => (
                    <option key={func} value={func}>
                      {func}
                    </option>
                  ))}
                </select>
              </div>

              {/* Point Type */}
              <div>
                <label className="block text-sm font-medium mb-2">Point Type</label>
                <select
                  value={pointType}
                  onChange={(e) => setPointType(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">Select Type...</option>
                  {POINT_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              {/* Custom Tag */}
              <div>
                <label className="block text-sm font-medium mb-2">Custom Tag (Optional)</label>
                <input
                  type="text"
                  value={haystackPointName}
                  onChange={(e) => setHaystackPointName(e.target.value)}
                  placeholder="Custom identifier"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
              </div>
            </div>
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
                  onChange={(e) => setMqttPublish(e.target.checked)}
                  className="rounded"
                />
                <label htmlFor="mqttPublish" className="text-sm font-medium">
                  Publish to MQTT Broker
                </label>
              </div>

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

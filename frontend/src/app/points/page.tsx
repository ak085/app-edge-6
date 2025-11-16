"use client";

import { useState, useEffect } from "react";
import PointEditor from "@/components/PointEditor";
import {
  Copy, Download, FileText, Check, Database, Settings,
  Filter as FilterIcon, CheckSquare, X, Search, Edit
} from "lucide-react";

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
  isReadable: boolean;
  isWritable: boolean;
  lastValue?: string | null;
  lastPollTime?: string | null;
}

export default function PointsPage() {
  const [points, setPoints] = useState<Point[]>([]);
  const [filteredPoints, setFilteredPoints] = useState<Point[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPoints, setSelectedPoints] = useState<Set<number>>(new Set());

  // Point editor modal
  const [selectedPoint, setSelectedPoint] = useState<Point | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);

  // Bulk configuration
  const [globalSiteId, setGlobalSiteId] = useState("");
  const [deviceMappings, setDeviceMappings] = useState<Record<number, { equipmentType: string; customEquipmentType: string; equipmentId: string }>>({});
  const [savingBulkConfig, setSavingBulkConfig] = useState(false);

  // Filters (with localStorage persistence)
  const [deviceFilter, setDeviceFilter] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('pointsDeviceFilter') || "";
    }
    return "";
  });
  const [objectTypeFilter, setObjectTypeFilter] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('pointsObjectTypeFilter') || "";
    }
    return "";
  });
  const [mqttFilter, setMqttFilter] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('pointsMqttFilter') || "";
    }
    return "";
  });
  const [searchQuery, setSearchQuery] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('pointsSearchQuery') || "";
    }
    return "";
  });

  // Copy feedback
  const [copiedTopic, setCopiedTopic] = useState<string | null>(null);

  // Toast notification
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Load points on mount
  useEffect(() => {
    loadPoints();
  }, []);

  // Auto-dismiss toast after 3 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Helper function to show toast
  function showToast(message: string, type: 'success' | 'error') {
    setToast({ message, type });
  }

  // Save filters to localStorage when they change
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('pointsDeviceFilter', deviceFilter);
    }
  }, [deviceFilter]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('pointsObjectTypeFilter', objectTypeFilter);
    }
  }, [objectTypeFilter]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('pointsMqttFilter', mqttFilter);
    }
  }, [mqttFilter]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('pointsSearchQuery', searchQuery);
    }
  }, [searchQuery]);

  // Apply filters whenever they change
  useEffect(() => {
    applyFilters();
  }, [points, deviceFilter, objectTypeFilter, mqttFilter, searchQuery]);

  async function loadPoints() {
    try {
      setLoading(true);
      const response = await fetch("/api/points");
      const data = await response.json();

      if (data.success) {
        setPoints(data.points);

        // Restore bulk configuration from database
        const loadedPoints: Point[] = data.points;

        // Extract most common siteId (or first non-null siteId)
        const siteIds = loadedPoints
          .map(p => p.siteId)
          .filter(Boolean);

        if (siteIds.length > 0) {
          // Use the most common siteId
          const siteIdCounts = siteIds.reduce((acc, id) => {
            acc[id!] = (acc[id!] || 0) + 1;
            return acc;
          }, {} as Record<string, number>);

          const mostCommonSiteId = Object.entries(siteIdCounts)
            .sort(([, a], [, b]) => b - a)[0][0];

          setGlobalSiteId(mostCommonSiteId);
        }

        // Extract device mappings (equipmentType and equipmentId per device)
        const mappings: Record<number, { equipmentType: string; customEquipmentType: string; equipmentId: string }> = {};

        loadedPoints.forEach(point => {
          if (!mappings[point.deviceId] && point.equipmentType && point.equipmentId) {
            mappings[point.deviceId] = {
              equipmentType: point.equipmentType,
              customEquipmentType: "",
              equipmentId: point.equipmentId
            };
          }
        });

        setDeviceMappings(mappings);
      }
    } catch (error) {
      console.error("Failed to load points:", error);
    } finally {
      setLoading(false);
    }
  }

  function applyFilters() {
    let filtered = [...points];

    if (deviceFilter) {
      filtered = filtered.filter((p) => p.device.deviceName === deviceFilter);
    }

    if (objectTypeFilter) {
      filtered = filtered.filter((p) => p.objectType === objectTypeFilter);
    }

    if (mqttFilter === "enabled") {
      filtered = filtered.filter((p) => p.mqttPublish);
    } else if (mqttFilter === "disabled") {
      filtered = filtered.filter((p) => !p.mqttPublish);
    }

    if (searchQuery) {
      filtered = filtered.filter((p) =>
        p.pointName.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    setFilteredPoints(filtered);
  }

  function toggleSelectAll() {
    if (selectedPoints.size === filteredPoints.length) {
      setSelectedPoints(new Set());
    } else {
      setSelectedPoints(new Set(filteredPoints.map((p) => p.id)));
    }
  }

  function toggleSelectPoint(pointId: number) {
    const newSelected = new Set(selectedPoints);
    if (newSelected.has(pointId)) {
      newSelected.delete(pointId);
    } else {
      newSelected.add(pointId);
    }
    setSelectedPoints(newSelected);
  }

  async function bulkEnableMqtt() {
    if (selectedPoints.size === 0) return;

    try {
      const response = await fetch("/api/points/bulk-update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pointIds: Array.from(selectedPoints),
          updates: { mqttPublish: true },
        }),
      });

      if (response.ok) {
        await loadPoints();
        setSelectedPoints(new Set());
        showToast(`MQTT enabled for ${selectedPoints.size} point${selectedPoints.size > 1 ? 's' : ''}`, "success");
      } else {
        showToast("Failed to enable MQTT", "error");
      }
    } catch (error) {
      console.error("Failed to enable MQTT:", error);
      showToast("Failed to enable MQTT", "error");
    }
  }

  async function bulkDisableMqtt() {
    if (selectedPoints.size === 0) return;

    try {
      const response = await fetch("/api/points/bulk-update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pointIds: Array.from(selectedPoints),
          updates: { mqttPublish: false },
        }),
      });

      if (response.ok) {
        await loadPoints();
        setSelectedPoints(new Set());
        showToast(`MQTT disabled for ${selectedPoints.size} point${selectedPoints.size > 1 ? 's' : ''}`, "success");
      } else {
        showToast("Failed to disable MQTT", "error");
      }
    } catch (error) {
      console.error("Failed to disable MQTT:", error);
      showToast("Failed to disable MQTT", "error");
    }
  }

  function handleEditPoint(point: Point) {
    setSelectedPoint(point);
    setIsEditorOpen(true);
  }

  function handleCloseEditor() {
    setIsEditorOpen(false);
    setSelectedPoint(null);
  }

  async function handleSavePoint() {
    await loadPoints();
  }

  // Copy MQTT topic to clipboard
  async function copyToClipboard(topic: string) {
    try {
      // Try modern Clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(topic);
        setCopiedTopic(topic);
        setTimeout(() => setCopiedTopic(null), 2000);
        showToast("Topic copied to clipboard", "success");
      } else {
        // Fallback to older method
        const textArea = document.createElement("textarea");
        textArea.value = topic;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);

        if (successful) {
          setCopiedTopic(topic);
          setTimeout(() => setCopiedTopic(null), 2000);
          showToast("Topic copied to clipboard", "success");
        } else {
          throw new Error("Copy command failed");
        }
      }
    } catch (error) {
      console.error("Failed to copy:", error);
      showToast("Failed to copy topic", "error");
    }
  }

  // Export topics as TXT
  function exportTopicsTxt() {
    const enabledPoints = points.filter((p) => p.mqttPublish && p.mqttTopic);

    let content = "# MQTT Topics Reference\n";
    content += `# Generated: ${new Date().toISOString()}\n`;
    content += `# Total Topics: ${enabledPoints.length}\n\n`;

    enabledPoints.forEach((point) => {
      const description = point.description || point.pointName;
      const units = point.units ? ` (${point.units})` : "";
      content += `${point.mqttTopic}    # ${description}${units}\n`;
    });

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mqtt_topics_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // Export subscriber guide as JSON
  function exportSubscriberGuideJson() {
    const enabledPoints = points.filter((p) => p.mqttPublish && p.mqttTopic);

    const guide = {
      broker: "10.0.60.2:1883",
      generatedAt: new Date().toISOString(),
      site: globalSiteId || "unknown",
      totalTopics: enabledPoints.length,
      topics: enabledPoints.map((point) => ({
        topic: point.mqttTopic,
        description: point.description || point.pointName,
        units: point.units || null,
        haystackName: point.haystackPointName || null,
        objectType: point.objectType,
        objectInstance: point.objectInstance,
        deviceIp: point.device.ipAddress,
        deviceId: point.device.deviceId,
        updateInterval: point.pollInterval,
        qos: point.qos,
        isWritable: point.isWritable,
      })),
    };

    const blob = new Blob([JSON.stringify(guide, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mqtt_subscriber_guide_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function handleSaveBulkConfig() {
    setSavingBulkConfig(true);
    try {
      if (!globalSiteId) {
        showToast("Please enter a Site ID", "error");
        setSavingBulkConfig(false);
        return;
      }

      // For each device, update all its points
      for (const [deviceIdStr, mapping] of Object.entries(deviceMappings)) {
        const deviceId = parseInt(deviceIdStr);
        const pointsForDevice = points.filter((p) => p.deviceId === deviceId);
        const pointIds = pointsForDevice.map((p) => p.id);

        // Determine final equipment type (use custom if "custom" is selected)
        const finalEquipmentType = mapping.equipmentType === "custom"
          ? mapping.customEquipmentType
          : mapping.equipmentType;

        if (pointIds.length > 0 && globalSiteId && finalEquipmentType && mapping.equipmentId) {
          await fetch("/api/points/bulk-update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              pointIds,
              updates: {
                siteId: globalSiteId,
                equipmentType: finalEquipmentType,
                equipmentId: mapping.equipmentId,
              },
            }),
          });
        }
      }

      await loadPoints();
      showToast("Bulk configuration saved successfully!", "success");
    } catch (error) {
      console.error("Failed to save bulk config:", error);
      showToast("Failed to save bulk configuration", "error");
    } finally {
      setSavingBulkConfig(false);
    }
  }

  // Get unique devices and object types for filters
  const devices = Array.from(new Set(points.map((p) => p.device.deviceName)));
  const objectTypes = Array.from(new Set(points.map((p) => p.objectType)));

  // Get unique device objects for bulk config
  const uniqueDevices = Array.from(
    new Map(points.map((p) => [p.device.id, p.device])).values()
  );

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Database className="w-8 h-8 text-cyan-500" />
          <h1 className="text-3xl font-bold">Points Configuration</h1>
        </div>
        <p className="text-muted-foreground">
          Configure Haystack tags, MQTT publishing, and polling intervals for discovered BACnet points
        </p>
      </div>

      <div className="space-y-6">
          {/* Bulk Configuration Card */}
          <div className="card bg-card p-6 rounded-lg border-2 border-blue-200 border-l-4 border-l-blue-500">
            <div className="flex items-center gap-2 mb-2">
              <Settings className="w-5 h-5 text-blue-500" />
              <h2 className="text-lg font-semibold text-blue-700">Bulk Configuration</h2>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              Set Site ID and map each BACnet device (DDC) to equipment. This applies to all points from each device.
            </p>

            <div className="space-y-4">
              {/* Global Site ID */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Site ID (applies to all points) <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={globalSiteId}
                  onChange={(e) => setGlobalSiteId(e.target.value)}
                  placeholder="Enter site ID (e.g., klcc, menara, plant_a)"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Unique identifier for this site/location
                </p>
              </div>

              {/* Device to Equipment Mapping */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Device to Equipment Mapping ({uniqueDevices.length} devices discovered)
                </label>
                <div className="border border-border rounded-md overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-muted">
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Device ID</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Device Name</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">IP Address</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Points Count</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Equipment Type</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Equipment ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {uniqueDevices.map((device) => {
                        const pointCount = points.filter((p) => p.deviceId === device.id).length;
                        return (
                          <tr key={device.id} className="border-t border-border">
                            <td className="px-4 py-2 text-sm">{device.deviceId}</td>
                            <td className="px-4 py-2 text-sm font-medium">{device.deviceName}</td>
                            <td className="px-4 py-2 text-sm text-muted-foreground">{device.ipAddress}</td>
                            <td className="px-4 py-2 text-sm text-muted-foreground">{pointCount} points</td>
                            <td className="px-4 py-2">
                              <div className="space-y-1">
                                <select
                                  value={deviceMappings[device.id]?.equipmentType || ""}
                                  onChange={(e) =>
                                    setDeviceMappings({
                                      ...deviceMappings,
                                      [device.id]: {
                                        ...deviceMappings[device.id],
                                        equipmentType: e.target.value,
                                      },
                                    })
                                  }
                                  className="input w-full bg-background border border-input px-2 py-1 rounded text-sm"
                                >
                                  <option value="">Select...</option>
                                  <option value="ahu">AHU</option>
                                  <option value="vav">VAV</option>
                                  <option value="fcu">FCU</option>
                                  <option value="chiller">Chiller</option>
                                  <option value="chwp">CHWP</option>
                                  <option value="cwp">CWP</option>
                                  <option value="ct">CT</option>
                                  <option value="boiler">Boiler</option>
                                  <option value="custom">Custom...</option>
                                </select>
                                {deviceMappings[device.id]?.equipmentType === "custom" && (
                                  <input
                                    type="text"
                                    value={deviceMappings[device.id]?.customEquipmentType || ""}
                                    onChange={(e) =>
                                      setDeviceMappings({
                                        ...deviceMappings,
                                        [device.id]: {
                                          ...deviceMappings[device.id],
                                          customEquipmentType: e.target.value,
                                        },
                                      })
                                    }
                                    placeholder="Enter custom equipment type"
                                    className="input w-full bg-background border border-input px-2 py-1 rounded text-sm"
                                  />
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-2">
                              <input
                                type="text"
                                value={deviceMappings[device.id]?.equipmentId || ""}
                                onChange={(e) =>
                                  setDeviceMappings({
                                    ...deviceMappings,
                                    [device.id]: {
                                      ...deviceMappings[device.id],
                                      equipmentId: e.target.value,
                                    },
                                  })
                                }
                                placeholder="e.g., 12"
                                className="input w-full bg-background border border-input px-2 py-1 rounded text-sm"
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Save Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleSaveBulkConfig}
                  disabled={savingBulkConfig || !globalSiteId}
                  className="px-6 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
                >
                  {savingBulkConfig ? "Saving..." : "Apply to All Points"}
                </button>
              </div>
            </div>
          </div>

          {/* MQTT Topic Export Card */}
          <div className="card bg-gradient-to-r from-blue-50 to-cyan-50 p-6 rounded-lg border-2 border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-blue-900 mb-1">MQTT Topic Documentation</h2>
                <p className="text-sm text-blue-700">
                  Export topic references for MQTT subscribers ({points.filter((p) => p.mqttPublish && p.mqttTopic).length} topics enabled)
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={exportTopicsTxt}
                  className="flex items-center gap-2 px-4 py-2 bg-white text-blue-700 rounded-lg border-2 border-blue-300 hover:bg-blue-50 transition-colors shadow-sm"
                >
                  <FileText className="w-4 h-4" />
                  <span className="font-medium">Export TXT</span>
                </button>
                <button
                  onClick={exportSubscriberGuideJson}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md"
                >
                  <Download className="w-4 h-4" />
                  <span className="font-medium">Export JSON</span>
                </button>
              </div>
            </div>
          </div>

          {/* Filters Card */}
          <div className="card bg-card p-6 rounded-lg border border-gray-200">
            <div className="flex items-center gap-2 mb-4">
              <FilterIcon className="w-5 h-5 text-purple-500" />
              <h2 className="text-lg font-semibold">Filters</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Device Filter */}
              <div>
                <label className="block text-sm font-medium mb-2">Device</label>
                <select
                  value={deviceFilter}
                  onChange={(e) => setDeviceFilter(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">All Devices</option>
                  {devices.map((device) => (
                    <option key={device} value={device}>
                      {device}
                    </option>
                  ))}
                </select>
              </div>

              {/* Object Type Filter */}
              <div>
                <label className="block text-sm font-medium mb-2">Object Type</label>
                <select
                  value={objectTypeFilter}
                  onChange={(e) => setObjectTypeFilter(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">All Types</option>
                  {objectTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              {/* MQTT Filter */}
              <div>
                <label className="block text-sm font-medium mb-2">MQTT Status</label>
                <select
                  value={mqttFilter}
                  onChange={(e) => setMqttFilter(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <option value="">All</option>
                  <option value="enabled">MQTT Enabled</option>
                  <option value="disabled">MQTT Disabled</option>
                </select>
              </div>

              {/* Search */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium mb-2">
                  <Search className="w-4 h-4 text-purple-500" />
                  Search
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search point name..."
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
              </div>
            </div>

            {/* Clear Filters */}
            {(deviceFilter || objectTypeFilter || mqttFilter || searchQuery) && (
              <button
                onClick={() => {
                  setDeviceFilter("");
                  setObjectTypeFilter("");
                  setMqttFilter("");
                  setSearchQuery("");
                }}
                className="mt-4 px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
              >
                Clear all filters
              </button>
            )}
          </div>

          {/* Bulk Operations */}
          {selectedPoints.size > 0 && (
            <div className="card bg-blue-50 border-2 border-blue-200 border-l-4 border-l-blue-500 p-4 rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckSquare className="w-5 h-5 text-blue-600" />
                <div className="text-sm font-medium text-blue-800">
                  {selectedPoints.size} point{selectedPoints.size > 1 ? "s" : ""} selected
                </div>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={bulkEnableMqtt}
                  className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90"
                >
                  <CheckSquare className="w-4 h-4" />
                  Enable MQTT
                </button>
                <button
                  onClick={bulkDisableMqtt}
                  className="flex items-center gap-2 px-4 py-2 bg-muted text-muted-foreground rounded-md font-medium hover:opacity-90 border-2 border-border"
                >
                  <X className="w-4 h-4" />
                  Disable MQTT
                </button>
                <button
                  onClick={() => setSelectedPoints(new Set())}
                  className="flex items-center gap-2 px-4 py-2 bg-background border border-input rounded-md font-medium hover:bg-muted"
                >
                  <X className="w-4 h-4" />
                  Clear Selection
                </button>
              </div>
            </div>
          )}

          {/* Points Table */}
          <div className="card bg-card rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              {loading ? (
                <div className="p-8 text-center text-muted-foreground">Loading points...</div>
              ) : filteredPoints.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  No points found. Try adjusting your filters or run discovery first.
                </div>
              ) : (
                <table className="w-full table-auto">
                  <thead className="bg-muted">
                    <tr>
                      <th className="px-2 py-3 text-left w-10">
                        <input
                          type="checkbox"
                          checked={
                            filteredPoints.length > 0 &&
                            selectedPoints.size === filteredPoints.length
                          }
                          onChange={toggleSelectAll}
                          className="rounded"
                        />
                      </th>
                      <th className="px-3 py-3 text-left text-sm font-semibold">Point Name</th>
                      <th className="px-3 py-3 text-left text-sm font-semibold">Current Value</th>
                      <th className="px-3 py-3 text-left text-sm font-semibold">Type</th>
                      <th className="px-3 py-3 text-left text-sm font-semibold">MQTT Topic</th>
                      <th className="px-3 py-3 text-left text-sm font-semibold">Status</th>
                      <th className="px-3 py-3 text-left text-sm font-semibold w-24">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPoints.map((point) => (
                      <tr key={point.id} className="border-t border-border hover:bg-muted/50">
                        <td className="px-2 py-3">
                          <input
                            type="checkbox"
                            checked={selectedPoints.has(point.id)}
                            onChange={() => toggleSelectPoint(point.id)}
                            className="rounded"
                          />
                        </td>
                        <td className="px-3 py-3">
                          <div className="text-sm font-semibold text-slate-900">
                            {point.dis || point.pointName}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            <span className="font-mono">{point.objectType.replace('analog-', 'A').replace('binary-', 'B').replace('-input', 'I').replace('-output', 'O').replace('-value', 'V').toUpperCase()}:{point.objectInstance}</span>
                            <span className="ml-1">• {point.pointName.split('_')[0]}</span>
                          </div>
                        </td>
                        <td className="px-3 py-3 text-sm font-mono">
                          {point.lastValue || "-"}
                          {point.lastValue && point.units && (
                            <span className="text-muted-foreground ml-1">{point.units}</span>
                          )}
                        </td>
                        <td className="px-3 py-3">
                          <div className="text-sm text-muted-foreground">{point.objectType}</div>
                          <div className="text-xs">
                            {point.isWritable ? (
                              <span className="text-orange-600">R/W</span>
                            ) : (
                              <span className="text-muted-foreground">Read-only</span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-3">
                          {point.mqttTopic ? (
                            <div className="flex items-center gap-2">
                              <code className="text-xs bg-slate-100 px-2 py-1 rounded border border-slate-200 font-mono text-slate-700">
                                {point.mqttTopic}
                              </code>
                              <button
                                onClick={() => copyToClipboard(point.mqttTopic!)}
                                className="p-1 rounded hover:bg-slate-200 transition-colors"
                                title="Copy topic"
                              >
                                {copiedTopic === point.mqttTopic ? (
                                  <Check className="w-4 h-4 text-green-600" />
                                ) : (
                                  <Copy className="w-4 h-4 text-slate-600" />
                                )}
                              </button>
                            </div>
                          ) : (
                            <span className="text-xs text-slate-400 italic">Not configured</span>
                          )}
                        </td>
                        <td className="px-3 py-3">
                          {point.mqttPublish ? (
                            <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                              Enabled
                            </span>
                          ) : (
                            <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                              Disabled
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-3">
                          <button
                            onClick={() => handleEditPoint(point)}
                            className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90"
                          >
                            <Edit className="w-3 h-3" />
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Summary Footer */}
            {filteredPoints.length > 0 && (
              <div className="px-4 py-3 border-t border-border bg-muted/30 text-sm text-muted-foreground">
                Showing {filteredPoints.length} of {points.length} points
              </div>
            )}
          </div>
        </div>

      {/* Point Editor Modal */}
      {selectedPoint && (
        <PointEditor
          point={selectedPoint}
          isOpen={isEditorOpen}
          onClose={handleCloseEditor}
          onSave={handleSavePoint}
        />
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-5 duration-300">
          <div
            className={`px-6 py-3 rounded-lg shadow-lg border-2 flex items-center gap-3 min-w-[300px] ${
              toast.type === 'success'
                ? 'bg-green-50 border-green-500 text-green-900'
                : 'bg-red-50 border-red-500 text-red-900'
            }`}
          >
            <div className="flex-shrink-0">
              {toast.type === 'success' ? (
                <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <p className="font-medium">{toast.message}</p>
          </div>
        </div>
      )}
    </div>
  );
}

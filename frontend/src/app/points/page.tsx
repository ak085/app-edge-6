"use client";

import { useState, useEffect } from "react";
import PointEditor from "@/components/PointEditor";

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

  // Filters
  const [deviceFilter, setDeviceFilter] = useState("");
  const [objectTypeFilter, setObjectTypeFilter] = useState("");
  const [mqttFilter, setMqttFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // Load points on mount
  useEffect(() => {
    loadPoints();
  }, []);

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
      }
    } catch (error) {
      console.error("Failed to enable MQTT:", error);
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
      }
    } catch (error) {
      console.error("Failed to disable MQTT:", error);
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

  // Get unique devices and object types for filters
  const devices = Array.from(new Set(points.map((p) => p.device.deviceName)));
  const objectTypes = Array.from(new Set(points.map((p) => p.objectType)));

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-foreground">BACnet Points</h1>
          <p className="text-sm text-muted-foreground">
            View and configure discovered BACnet points
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Filters Card */}
          <div className="card bg-card p-6 rounded-lg">
            <h2 className="text-lg font-semibold mb-4">Filters</h2>

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
                <label className="block text-sm font-medium mb-2">Search</label>
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
            <div className="card bg-blue-50 border-blue-200 p-4 rounded-lg flex items-center justify-between">
              <div className="text-sm font-medium">
                {selectedPoints.size} point{selectedPoints.size > 1 ? "s" : ""} selected
              </div>
              <div className="flex gap-3">
                <button
                  onClick={bulkEnableMqtt}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90"
                >
                  Enable MQTT
                </button>
                <button
                  onClick={bulkDisableMqtt}
                  className="px-4 py-2 bg-muted text-muted-foreground rounded-md font-medium hover:opacity-90"
                >
                  Disable MQTT
                </button>
                <button
                  onClick={() => setSelectedPoints(new Set())}
                  className="px-4 py-2 bg-background border border-input rounded-md font-medium hover:bg-muted"
                >
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
                <table className="w-full">
                  <thead className="bg-muted">
                    <tr>
                      <th className="px-4 py-3 text-left">
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
                      <th className="px-4 py-3 text-left text-sm font-semibold">Device</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold">Point Name</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold">Description</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold">Current Value</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold">Type</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold">Access</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold">MQTT</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPoints.map((point) => (
                      <tr key={point.id} className="border-t border-border hover:bg-muted/50">
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={selectedPoints.has(point.id)}
                            onChange={() => toggleSelectPoint(point.id)}
                            className="rounded"
                          />
                        </td>
                        <td className="px-4 py-3 text-sm">{point.device.deviceName}</td>
                        <td className="px-4 py-3 text-sm font-medium">{point.pointName}</td>
                        <td className="px-4 py-3 text-sm text-muted-foreground max-w-xs truncate">
                          {point.description || "-"}
                        </td>
                        <td className="px-4 py-3 text-sm font-mono">
                          {point.lastValue || "-"}
                          {point.lastValue && point.units && (
                            <span className="text-muted-foreground ml-1">{point.units}</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">
                          {point.objectType}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {point.isWritable ? (
                            <span className="text-orange-600">R/W</span>
                          ) : (
                            <span className="text-muted-foreground">R</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
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
                        <td className="px-4 py-3">
                          <button
                            onClick={() => handleEditPoint(point)}
                            className="px-3 py-1 text-sm text-primary hover:bg-primary/10 rounded-md"
                          >
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
      </main>

      {/* Point Editor Modal */}
      {selectedPoint && (
        <PointEditor
          point={selectedPoint}
          isOpen={isEditorOpen}
          onClose={handleCloseEditor}
          onSave={handleSavePoint}
        />
      )}
    </div>
  );
}

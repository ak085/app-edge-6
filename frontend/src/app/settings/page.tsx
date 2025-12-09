"use client";

import { useState, useEffect } from "react";
import { Save } from "lucide-react";

interface Settings {
  bacnetIp: string;
  bacnetPort: number;
  mqttBroker: string;
  mqttPort: number;
  timezone: string;
  defaultPollInterval: number;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    bacnetIp: "",
    bacnetPort: 47808,
    mqttBroker: "",
    mqttPort: 1883,
    timezone: "Asia/Kuala_Lumpur",
    defaultPollInterval: 60,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Bulk poll interval state
  const [bulkPollInterval, setBulkPollInterval] = useState(60);
  const [applyingBulkInterval, setApplyingBulkInterval] = useState(false);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
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

  async function loadSettings() {
    try {
      setLoading(true);
      const response = await fetch("/api/settings");
      const data = await response.json();

      if (data.success && data.settings) {
        const loadedSettings = {
          bacnetIp: data.settings.bacnetIp || "",
          bacnetPort: data.settings.bacnetPort || 47808,
          mqttBroker: data.settings.mqttBroker || "",
          mqttPort: data.settings.mqttPort || 1883,
          timezone: data.settings.timezone || "Asia/Kuala_Lumpur",
          defaultPollInterval: data.settings.defaultPollInterval || 60,
        };
        setSettings(loadedSettings);
        setBulkPollInterval(loadedSettings.defaultPollInterval);
      }
    } catch (error) {
      console.error("Failed to load settings:", error);
      setToast({ message: "Failed to load settings", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  async function saveSettings() {
    try {
      setSaving(true);
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });

      const data = await response.json();

      if (data.success) {
        setToast({ message: "Settings saved successfully!", type: "success" });
      } else {
        setToast({ message: "Failed to save settings", type: "error" });
      }
    } catch (error) {
      console.error("Failed to save settings:", error);
      setToast({ message: "Failed to save settings", type: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function applyBulkPollInterval() {
    try {
      setApplyingBulkInterval(true);

      // First, save the default poll interval to settings
      const settingsResponse = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...settings,
          defaultPollInterval: bulkPollInterval,
        }),
      });

      if (!settingsResponse.ok) {
        throw new Error("Failed to save default poll interval");
      }

      // Then, apply the interval to all MQTT-enabled points
      const response = await fetch("/api/points/bulk-poll-interval", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pollInterval: bulkPollInterval }),
      });

      const data = await response.json();

      if (data.success) {
        // Update local settings state to reflect saved value
        setSettings({ ...settings, defaultPollInterval: bulkPollInterval });
        setToast({
          message: `${data.message} Default poll interval saved. Worker will apply changes on next refresh.`,
          type: "success"
        });
      } else {
        setToast({ message: data.error || "Failed to update poll intervals", type: "error" });
      }
    } catch (error) {
      console.error("Failed to apply bulk poll interval:", error);
      setToast({ message: "Failed to apply bulk poll interval", type: "error" });
    } finally {
      setApplyingBulkInterval(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted-foreground">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-foreground">System Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure BACnet and MQTT connection parameters
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* BACnet Configuration */}
          <div className="card bg-card p-6 rounded-lg border-2 border-border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span className="text-2xl">🔌</span>
              BACnet Network Configuration
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Configure the local IP address for BACnet discovery and communication
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* BACnet IP */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  BACnet IP Address <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={settings.bacnetIp}
                  onChange={(e) => setSettings({ ...settings, bacnetIp: e.target.value })}
                  placeholder="192.168.1.35"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Local IP address on BACnet network
                </p>
              </div>

              {/* BACnet Port */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  BACnet Port
                </label>
                <input
                  type="number"
                  value={settings.bacnetPort}
                  onChange={(e) => setSettings({ ...settings, bacnetPort: parseInt(e.target.value) })}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Standard BACnet/IP port (default: 47808)
                </p>
              </div>
            </div>
          </div>

          {/* MQTT Configuration */}
          <div className="card bg-card p-6 rounded-lg border-2 border-border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span className="text-2xl">📡</span>
              MQTT Broker Configuration
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Configure the MQTT broker for publishing BACnet data
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* MQTT Broker */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  MQTT Broker IP <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={settings.mqttBroker}
                  onChange={(e) => setSettings({ ...settings, mqttBroker: e.target.value })}
                  placeholder="10.0.60.2"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  IP address of MQTT broker
                </p>
              </div>

              {/* MQTT Port */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  MQTT Port
                </label>
                <input
                  type="number"
                  value={settings.mqttPort}
                  onChange={(e) => setSettings({ ...settings, mqttPort: parseInt(e.target.value) })}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Standard MQTT port (default: 1883)
                </p>
              </div>
            </div>
          </div>

          {/* System Configuration */}
          <div className="card bg-card p-6 rounded-lg border-2 border-border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span className="text-2xl">⚙️</span>
              System Configuration
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Configure system settings including timezone for MQTT timestamps
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Timezone */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Timezone <span className="text-red-500">*</span>
                </label>
                <select
                  value={settings.timezone}
                  onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  <optgroup label="UTC">
                    <option value="UTC">UTC (Universal Time)</option>
                  </optgroup>
                  <optgroup label="Asia">
                    <option value="Asia/Kuala_Lumpur">Asia/Kuala Lumpur (UTC+8)</option>
                    <option value="Asia/Singapore">Asia/Singapore (UTC+8)</option>
                    <option value="Asia/Hong_Kong">Asia/Hong Kong (UTC+8)</option>
                    <option value="Asia/Tokyo">Asia/Tokyo (UTC+9)</option>
                    <option value="Asia/Seoul">Asia/Seoul (UTC+9)</option>
                    <option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</option>
                    <option value="Asia/Bangkok">Asia/Bangkok (UTC+7)</option>
                    <option value="Asia/Jakarta">Asia/Jakarta (UTC+7)</option>
                    <option value="Asia/Dubai">Asia/Dubai (UTC+4)</option>
                  </optgroup>
                  <optgroup label="Europe">
                    <option value="Europe/London">Europe/London (UTC+0/+1)</option>
                    <option value="Europe/Paris">Europe/Paris (UTC+1/+2)</option>
                    <option value="Europe/Berlin">Europe/Berlin (UTC+1/+2)</option>
                    <option value="Europe/Amsterdam">Europe/Amsterdam (UTC+1/+2)</option>
                    <option value="Europe/Moscow">Europe/Moscow (UTC+3)</option>
                  </optgroup>
                  <optgroup label="Americas">
                    <option value="America/New_York">America/New York (UTC-5/-4)</option>
                    <option value="America/Chicago">America/Chicago (UTC-6/-5)</option>
                    <option value="America/Denver">America/Denver (UTC-7/-6)</option>
                    <option value="America/Los_Angeles">America/Los Angeles (UTC-8/-7)</option>
                    <option value="America/Toronto">America/Toronto (UTC-5/-4)</option>
                    <option value="America/Sao_Paulo">America/Sao Paulo (UTC-3)</option>
                    <option value="America/Mexico_City">America/Mexico City (UTC-6/-5)</option>
                  </optgroup>
                  <optgroup label="Australia & Pacific">
                    <option value="Australia/Sydney">Australia/Sydney (UTC+10/+11)</option>
                    <option value="Australia/Melbourne">Australia/Melbourne (UTC+10/+11)</option>
                    <option value="Australia/Brisbane">Australia/Brisbane (UTC+10)</option>
                    <option value="Australia/Perth">Australia/Perth (UTC+8)</option>
                    <option value="Pacific/Auckland">Pacific/Auckland (UTC+12/+13)</option>
                  </optgroup>
                  <optgroup label="Middle East & Africa">
                    <option value="Africa/Johannesburg">Africa/Johannesburg (UTC+2)</option>
                    <option value="Africa/Cairo">Africa/Cairo (UTC+2)</option>
                    <option value="Africa/Lagos">Africa/Lagos (UTC+1)</option>
                  </optgroup>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  Timezone for MQTT message timestamps
                </p>
              </div>

              {/* Current Time Display */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Current Time in Selected Timezone
                </label>
                <div className="input w-full bg-muted/50 border-2 border-input px-3 py-2 rounded-md">
                  <span className="text-lg font-mono">
                    {new Date().toLocaleString('en-US', {
                      timeZone: settings.timezone,
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                      hour12: false
                    })}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Live preview of current time
                </p>
              </div>
            </div>

            {/* Timezone Info */}
            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-900">
                <strong>💡 Important:</strong> All MQTT timestamps will use this timezone.
                For multi-site deployments across different regions, consider using UTC to avoid confusion.
                Worker restart is required for changes to take effect.
              </p>
            </div>
          </div>

          {/* Point Publishing Settings */}
          <div className="card bg-card p-6 rounded-lg border-2 border-border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span className="text-2xl">⏱️</span>
              Point Publishing Settings
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Configure default polling interval for all MQTT-enabled points
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
              {/* Poll Interval Input */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Default Poll Interval (seconds) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  min="1"
                  max="3600"
                  value={bulkPollInterval}
                  onChange={(e) => {
                    const newValue = parseInt(e.target.value) || 60;
                    setBulkPollInterval(newValue);
                    setSettings({ ...settings, defaultPollInterval: newValue });
                  }}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  How often to poll each point (1-3600 seconds)
                </p>
              </div>

              {/* Apply Button */}
              <div>
                <button
                  onClick={applyBulkPollInterval}
                  disabled={applyingBulkInterval || bulkPollInterval < 1 || bulkPollInterval > 3600}
                  className="w-full px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
                >
                  {applyingBulkInterval ? "Applying..." : "Apply to All MQTT Points"}
                </button>
                <p className="text-xs text-muted-foreground mt-1">
                  Updates all points currently enabled for MQTT publishing
                </p>
              </div>
            </div>

            {/* Info Box */}
            <div className="mt-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-sm text-orange-900">
                <strong>⚠️ Note:</strong> This will update the poll interval for ALL points that have MQTT publishing enabled.
                Individual point intervals can still be changed on the Points page.
                The BACnet worker will pick up changes on its next configuration refresh (typically within 60 seconds).
              </p>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button
              onClick={saveSettings}
              disabled={saving}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
            >
              <Save className="w-5 h-5" />
              <span>{saving ? "Saving..." : "Save Settings"}</span>
            </button>
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <strong>💡 Note:</strong> After changing the BACnet IP address, the Discovery page will automatically use the new IP as the default selection. The MQTT worker will need to be restarted to use the new MQTT broker address.
            </p>
          </div>
        </div>
      </main>

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

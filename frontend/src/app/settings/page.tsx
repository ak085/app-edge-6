"use client";

import { useState, useEffect, useRef } from "react";
import { Save, Upload, Trash2, Lock, Shield, Radio, Key } from "lucide-react";

interface Settings {
  // Authentication
  hasMasterPin: boolean;
  // BACnet
  bacnetIp: string;
  bacnetPort: number;
  timezone: string;
  defaultPollInterval: number;
  // MQTT Connection
  mqttBroker: string;
  mqttPort: number;
  mqttClientId: string;
  // MQTT Authentication
  mqttUsername: string;
  mqttPassword: string;
  // MQTT TLS
  mqttTlsEnabled: boolean;
  mqttTlsInsecure: boolean;
  mqttCaCertPath: string | null;
  mqttClientCertPath: string | null;
  mqttClientKeyPath: string | null;
  // MQTT Subscription
  mqttSubscribeEnabled: boolean;
  mqttSubscribeTopicPattern: string;
  mqttSubscribeQos: number;
}

interface CertificateStatus {
  ca: { configured: boolean; path: string | null; exists: boolean };
  client: { configured: boolean; path: string | null; exists: boolean };
  key: { configured: boolean; path: string | null; exists: boolean };
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    // Authentication
    hasMasterPin: false,
    // BACnet
    bacnetIp: "",
    bacnetPort: 47808,
    timezone: "Asia/Kuala_Lumpur",
    defaultPollInterval: 60,
    // MQTT Connection
    mqttBroker: "",
    mqttPort: 1883,
    mqttClientId: "bacpipes_worker",
    // MQTT Authentication
    mqttUsername: "",
    mqttPassword: "",
    // MQTT TLS
    mqttTlsEnabled: false,
    mqttTlsInsecure: false,
    mqttCaCertPath: null,
    mqttClientCertPath: null,
    mqttClientKeyPath: null,
    // MQTT Subscription
    mqttSubscribeEnabled: false,
    mqttSubscribeTopicPattern: "override/#",
    mqttSubscribeQos: 1,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Certificate status
  const [certStatus, setCertStatus] = useState<CertificateStatus | null>(null);
  const [uploadingCert, setUploadingCert] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pendingCertType, setPendingCertType] = useState<'ca' | 'client' | 'key' | null>(null);

  // Bulk poll interval state
  const [bulkPollInterval, setBulkPollInterval] = useState(60);
  const [applyingBulkInterval, setApplyingBulkInterval] = useState(false);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [masterPinForPassword, setMasterPinForPassword] = useState("");

  // Master PIN management state
  const [currentPin, setCurrentPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [changingPin, setChangingPin] = useState(false);

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
        const loadedSettings: Settings = {
          // Authentication
          hasMasterPin: data.settings.hasMasterPin ?? false,
          // BACnet
          bacnetIp: data.settings.bacnetIp || "",
          bacnetPort: data.settings.bacnetPort || 47808,
          timezone: data.settings.timezone || "Asia/Kuala_Lumpur",
          defaultPollInterval: data.settings.defaultPollInterval || 60,
          // MQTT Connection
          mqttBroker: data.settings.mqttBroker || "",
          mqttPort: data.settings.mqttPort || 1883,
          mqttClientId: data.settings.mqttClientId || "bacpipes_worker",
          // MQTT Authentication
          mqttUsername: data.settings.mqttUsername || "",
          mqttPassword: data.settings.mqttPassword || "",
          // MQTT TLS
          mqttTlsEnabled: data.settings.mqttTlsEnabled ?? false,
          mqttTlsInsecure: data.settings.mqttTlsInsecure ?? false,
          mqttCaCertPath: data.settings.mqttCaCertPath || null,
          mqttClientCertPath: data.settings.mqttClientCertPath || null,
          mqttClientKeyPath: data.settings.mqttClientKeyPath || null,
          // MQTT Subscription
          mqttSubscribeEnabled: data.settings.mqttSubscribeEnabled ?? false,
          mqttSubscribeTopicPattern: data.settings.mqttSubscribeTopicPattern || "override/#",
          mqttSubscribeQos: data.settings.mqttSubscribeQos ?? 1,
        };
        setSettings(loadedSettings);
        setBulkPollInterval(loadedSettings.defaultPollInterval);
      }

      // Load certificate status
      await loadCertificateStatus();
    } catch (error) {
      console.error("Failed to load settings:", error);
      setToast({ message: "Failed to load settings", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  async function loadCertificateStatus() {
    try {
      const response = await fetch("/api/settings/certificates");
      const data = await response.json();
      if (data.success) {
        setCertStatus(data.certificates);
      }
    } catch (error) {
      console.error("Failed to load certificate status:", error);
    }
  }

  async function uploadCertificate(file: File, certType: 'ca' | 'client' | 'key') {
    try {
      setUploadingCert(certType);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', certType);

      const response = await fetch("/api/settings/certificates", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (data.success) {
        setToast({ message: `${certType} certificate uploaded successfully`, type: "success" });
        await loadCertificateStatus();
        // Update only the certificate path in settings, preserve other unsaved changes
        if (data.path) {
          const certPathKey = certType === 'ca' ? 'mqttCaCertPath' : certType === 'client' ? 'mqttClientCertPath' : 'mqttClientKeyPath';
          setSettings(prev => ({ ...prev, [certPathKey]: data.path }));
        }
      } else {
        setToast({ message: data.error || "Failed to upload certificate", type: "error" });
      }
    } catch (error) {
      console.error("Failed to upload certificate:", error);
      setToast({ message: "Failed to upload certificate", type: "error" });
    } finally {
      setUploadingCert(null);
    }
  }

  async function deleteCertificate(certType: 'ca' | 'client' | 'key') {
    try {
      setUploadingCert(certType);
      const response = await fetch(`/api/settings/certificates?type=${certType}`, {
        method: "DELETE",
      });

      const data = await response.json();
      if (data.success) {
        setToast({ message: `${certType} certificate deleted`, type: "success" });
        await loadCertificateStatus();
        // Clear only the certificate path in settings, preserve other unsaved changes
        const certPathKey = certType === 'ca' ? 'mqttCaCertPath' : certType === 'client' ? 'mqttClientCertPath' : 'mqttClientKeyPath';
        setSettings(prev => ({ ...prev, [certPathKey]: null }));
      } else {
        setToast({ message: data.error || "Failed to delete certificate", type: "error" });
      }
    } catch (error) {
      console.error("Failed to delete certificate:", error);
      setToast({ message: "Failed to delete certificate", type: "error" });
    } finally {
      setUploadingCert(null);
    }
  }

  function handleFileSelect(certType: 'ca' | 'client' | 'key') {
    setPendingCertType(certType);
    fileInputRef.current?.click();
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file && pendingCertType) {
      uploadCertificate(file, pendingCertType);
    }
    // Reset the input so the same file can be selected again
    e.target.value = '';
    setPendingCertType(null);
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

  async function changePassword() {
    if (newPassword !== confirmPassword) {
      setToast({ message: "New passwords do not match", type: "error" });
      return;
    }

    if (newPassword.length < 4) {
      setToast({ message: "Password must be at least 4 characters", type: "error" });
      return;
    }

    // Require PIN if one is set
    if (settings.hasMasterPin && !masterPinForPassword) {
      setToast({ message: "Master PIN is required to change password", type: "error" });
      return;
    }

    try {
      setChangingPassword(true);
      const response = await fetch("/api/auth/password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          currentPassword,
          newPassword,
          masterPin: masterPinForPassword || undefined,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setToast({ message: "Password changed successfully!", type: "success" });
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
        setMasterPinForPassword("");
      } else {
        setToast({ message: data.error || "Failed to change password", type: "error" });
      }
    } catch (error) {
      console.error("Failed to change password:", error);
      setToast({ message: "Failed to change password", type: "error" });
    } finally {
      setChangingPassword(false);
    }
  }

  async function changePin() {
    if (newPin !== confirmPin) {
      setToast({ message: "New PINs do not match", type: "error" });
      return;
    }

    if (!/^\d{4,6}$/.test(newPin)) {
      setToast({ message: "PIN must be 4-6 digits", type: "error" });
      return;
    }

    // Require current PIN if one is already set
    if (settings.hasMasterPin && !currentPin) {
      setToast({ message: "Current PIN is required", type: "error" });
      return;
    }

    try {
      setChangingPin(true);
      const response = await fetch("/api/auth/pin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          currentPin: currentPin || undefined,
          newPin,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setToast({ message: settings.hasMasterPin ? "Master PIN changed successfully!" : "Master PIN set successfully!", type: "success" });
        setCurrentPin("");
        setNewPin("");
        setConfirmPin("");
        // Update local state to reflect PIN is now set
        setSettings({ ...settings, hasMasterPin: true });
      } else {
        setToast({ message: data.error || "Failed to change PIN", type: "error" });
      }
    } catch (error) {
      console.error("Failed to change PIN:", error);
      setToast({ message: "Failed to change PIN", type: "error" });
    } finally {
      setChangingPin(false);
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
                  Standard MQTT port (default: 1883, TLS: 8883)
                </p>
              </div>

              {/* MQTT Client ID */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Client ID
                </label>
                <input
                  type="text"
                  value={settings.mqttClientId}
                  onChange={(e) => setSettings({ ...settings, mqttClientId: e.target.value })}
                  placeholder="bacpipes_worker"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Unique identifier shown on MQTT broker
                </p>
              </div>
            </div>
          </div>

          {/* MQTT Authentication */}
          <div className="card bg-card p-6 rounded-lg border-2 border-border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Lock className="w-6 h-6 text-yellow-600" />
              MQTT Authentication
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Configure username and password for MQTT broker authentication (leave blank for anonymous)
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Username */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={settings.mqttUsername}
                  onChange={(e) => setSettings({ ...settings, mqttUsername: e.target.value })}
                  placeholder="mqtt_user"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={settings.mqttPassword}
                  onChange={(e) => setSettings({ ...settings, mqttPassword: e.target.value })}
                  placeholder="••••••••"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
              </div>
            </div>
          </div>

          {/* MQTT TLS/Security */}
          <div className="card bg-card p-6 rounded-lg border-2 border-border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Shield className="w-6 h-6 text-green-600" />
              MQTT TLS/Security
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Configure TLS encryption for secure MQTT connection
            </p>

            {/* Hidden file input for certificate uploads */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".crt,.pem,.key"
              className="hidden"
            />

            {/* TLS Enable Toggle */}
            <div className="flex items-center gap-3 mb-4">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.mqttTlsEnabled}
                  onChange={(e) => setSettings({ ...settings, mqttTlsEnabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
              <span className="text-sm font-medium">Enable TLS Encryption</span>
            </div>

            {settings.mqttTlsEnabled && (
              <>
                {/* Skip Verification Toggle */}
                <div className="flex items-center gap-3 mb-4 ml-4">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.mqttTlsInsecure}
                      onChange={(e) => setSettings({ ...settings, mqttTlsInsecure: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-orange-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-500"></div>
                  </label>
                  <span className="text-sm font-medium text-orange-700">Skip Certificate Verification (insecure)</span>
                </div>

                {/* Certificate Uploads */}
                <div className="space-y-4 mt-4">
                  {/* CA Certificate */}
                  <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium">CA Certificate</p>
                      <p className="text-xs text-muted-foreground">
                        {certStatus?.ca.configured
                          ? (certStatus.ca.exists ? `✅ ${certStatus.ca.path}` : `⚠️ File missing: ${certStatus.ca.path}`)
                          : "Not configured"}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleFileSelect('ca')}
                        disabled={uploadingCert === 'ca'}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                      >
                        <Upload className="w-4 h-4" />
                        {uploadingCert === 'ca' ? 'Uploading...' : 'Upload'}
                      </button>
                      {certStatus?.ca.configured && (
                        <button
                          onClick={() => deleteCertificate('ca')}
                          disabled={uploadingCert === 'ca'}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                </div>

                {/* TLS Info */}
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm text-green-900">
                    <strong>🔒 TLS Notes:</strong> Upload the CA certificate from your MQTT broker to verify server identity.
                    Use &quot;Skip Certificate Verification&quot; for self-signed certificates.
                    Standard MQTTS port is 8883.
                  </p>
                </div>
              </>
            )}
          </div>

          {/* MQTT Subscription (Setpoint Override) */}
          <div className="card bg-card p-6 rounded-lg border-2 border-border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Radio className="w-6 h-6 text-purple-600" />
              MQTT Subscription (Setpoint Override)
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Subscribe to external topics to receive setpoint override values from ML/optimization systems
            </p>

            {/* Subscribe Enable Toggle */}
            <div className="flex items-center gap-3 mb-4">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.mqttSubscribeEnabled}
                  onChange={(e) => setSettings({ ...settings, mqttSubscribeEnabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
              </label>
              <span className="text-sm font-medium">Enable Subscription for Setpoint Overrides</span>
            </div>

            {settings.mqttSubscribeEnabled && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Topic Pattern */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Subscribe Topic Pattern
                  </label>
                  <input
                    type="text"
                    value={settings.mqttSubscribeTopicPattern}
                    onChange={(e) => setSettings({ ...settings, mqttSubscribeTopicPattern: e.target.value })}
                    placeholder="override/#"
                    className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Use # for multi-level wildcard, + for single-level
                  </p>
                </div>

                {/* QoS Level */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    QoS Level
                  </label>
                  <select
                    value={settings.mqttSubscribeQos}
                    onChange={(e) => setSettings({ ...settings, mqttSubscribeQos: parseInt(e.target.value) })}
                    className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                  >
                    <option value={0}>0 - At most once (fire and forget)</option>
                    <option value={1}>1 - At least once (acknowledged)</option>
                    <option value={2}>2 - Exactly once (guaranteed)</option>
                  </select>
                </div>
              </div>
            )}

            {settings.mqttSubscribeEnabled && (
              <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <p className="text-sm text-purple-900">
                  <strong>📥 Override Flow:</strong> External systems (ML/optimizer) publish to <code className="bg-purple-100 px-1 rounded">override/...</code> topics.
                  BacPipes subscribes and writes values to BACnet devices. Only points with <code className="bg-purple-100 px-1 rounded">sp</code> (setpoint) in position-4 of their Haystack name can be overwritten.
                </p>
              </div>
            )}
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

          {/* Master PIN */}
          <div className="card bg-card p-6 rounded-lg border-2 border-border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Shield className="w-6 h-6 text-purple-600" />
              Master PIN
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              {settings.hasMasterPin
                ? "Master PIN is set. It is required to change the admin password."
                : "Set a master PIN to protect password changes. Only you (the system administrator) should know this PIN."}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Current PIN (only if PIN exists) */}
              {settings.hasMasterPin && (
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Current PIN
                  </label>
                  <input
                    type="password"
                    value={currentPin}
                    onChange={(e) => setCurrentPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="••••••"
                    maxLength={6}
                    className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                  />
                </div>
              )}

              {/* New PIN */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  {settings.hasMasterPin ? "New PIN" : "Set PIN"}
                </label>
                <input
                  type="password"
                  value={newPin}
                  onChange={(e) => setNewPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="4-6 digits"
                  maxLength={6}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
              </div>

              {/* Confirm PIN */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Confirm PIN
                </label>
                <input
                  type="password"
                  value={confirmPin}
                  onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="4-6 digits"
                  maxLength={6}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
              </div>
            </div>

            <div className="mt-4">
              <button
                onClick={changePin}
                disabled={changingPin || !newPin || !confirmPin || (settings.hasMasterPin && !currentPin)}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {changingPin ? "Saving..." : (settings.hasMasterPin ? "Change PIN" : "Set PIN")}
              </button>
            </div>

            {/* PIN Info */}
            <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <p className="text-sm text-purple-900">
                <strong>🔐 Important:</strong> The master PIN protects password changes. If you forget it, you can reset it via CLI command:
                <code className="bg-purple-100 px-2 py-0.5 rounded ml-1">docker exec bacpipes-frontend node scripts/reset-pin.js</code>
              </p>
            </div>
          </div>

          {/* Change Password */}
          <div className="card bg-card p-6 rounded-lg border-2 border-border">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Key className="w-6 h-6 text-orange-500" />
              Change Password
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Update the admin password for accessing this interface
              {settings.hasMasterPin && <span className="text-purple-600 font-medium"> (requires Master PIN)</span>}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Master PIN (if set) */}
              {settings.hasMasterPin && (
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-2 text-purple-700">
                    Master PIN <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="password"
                    value={masterPinForPassword}
                    onChange={(e) => setMasterPinForPassword(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="Enter your master PIN"
                    maxLength={6}
                    className="input w-full md:w-1/3 bg-background border-2 border-purple-300 px-3 py-2 rounded-md"
                  />
                </div>
              )}

              {/* Current Password */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Current Password
                </label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
              </div>

              {/* New Password */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  New Password
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                />
              </div>
            </div>

            <div className="mt-4">
              <button
                onClick={changePassword}
                disabled={changingPassword || !currentPassword || !newPassword || !confirmPassword || (settings.hasMasterPin && !masterPinForPassword)}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {changingPassword ? "Changing..." : "Change Password"}
              </button>
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

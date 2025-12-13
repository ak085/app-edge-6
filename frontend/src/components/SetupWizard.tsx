"use client";

import { useState, useEffect } from "react";
import { Network, Server, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";

interface NetworkInterface {
  name: string;
  address: string;
  cidr: string;
}

interface SetupWizardProps {
  isOpen: boolean;
  onComplete: () => void;
}

export default function SetupWizard({ isOpen, onComplete }: SetupWizardProps) {
  const [step, setStep] = useState<'network' | 'mqtt' | 'saving'>('network');
  const [interfaces, setInterfaces] = useState<NetworkInterface[]>([]);
  const [loadingInterfaces, setLoadingInterfaces] = useState(true);
  const [selectedBacnetIp, setSelectedBacnetIp] = useState<string>("");
  const [mqttBroker, setMqttBroker] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch available network interfaces
  useEffect(() => {
    if (isOpen) {
      fetchInterfaces();
    }
  }, [isOpen]);

  const fetchInterfaces = async () => {
    try {
      setLoadingInterfaces(true);
      setError(null);
      const response = await fetch('/api/network/interfaces');
      const data = await response.json();

      if (data.success && data.interfaces.length > 0) {
        setInterfaces(data.interfaces);
        // Auto-select first non-configured interface
        const firstDetected = data.interfaces.find((iface: NetworkInterface) =>
          iface.name.includes('(detected)')
        );
        if (firstDetected) {
          setSelectedBacnetIp(firstDetected.address);
        }
      } else {
        setError("No network interfaces detected. Please check system configuration.");
      }
    } catch (err) {
      setError("Failed to detect network interfaces");
      console.error("Interface detection error:", err);
    } finally {
      setLoadingInterfaces(false);
    }
  };

  const handleSaveConfiguration = async () => {
    if (!selectedBacnetIp) {
      setError("Please select a BACnet IP address");
      return;
    }
    if (!mqttBroker) {
      setError("Please enter MQTT broker IP address");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setStep('saving');

      // Save settings
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bacnetIp: selectedBacnetIp,
          mqttBroker: mqttBroker,
        }),
      });

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to save settings');
      }

      // Configuration saved successfully
      setTimeout(() => {
        onComplete();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save configuration");
      setStep('mqtt'); // Go back to MQTT step on error
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card rounded-lg shadow-lg max-w-2xl w-full mx-4">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border">
          <h2 className="text-xl font-semibold">First-Time Setup</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Configure network settings for BacPipes to start discovering BACnet devices
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          {/* Step 1: Network Interface Selection */}
          {step === 'network' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Network className="h-5 w-5 text-blue-500" />
                <h3 className="text-lg font-semibold">Step 1: Select BACnet Network Interface</h3>
              </div>

              <p className="text-sm text-muted-foreground mb-4">
                Select the network interface that can reach your BACnet devices.
                Avoid docker bridge IPs (172.x.x.x) - choose your host IP address.
              </p>

              {loadingInterfaces ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin text-blue-500" />
                  <span className="ml-2 text-sm">Detecting network interfaces...</span>
                </div>
              ) : interfaces.length === 0 ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
                    <div>
                      <p className="font-semibold text-red-900">No interfaces detected</p>
                      <p className="text-sm text-red-700 mt-1">
                        Unable to detect network interfaces. Please check your LXC container features
                        (nesting=1, keyctl=1) and Docker host networking configuration.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={fetchInterfaces}
                    className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
                  >
                    Retry Detection
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {interfaces.map((iface) => (
                    <label
                      key={iface.address}
                      className={`flex items-center gap-3 p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                        selectedBacnetIp === iface.address
                          ? "border-blue-500 bg-blue-50"
                          : "border-border hover:border-blue-300"
                      }`}
                    >
                      <input
                        type="radio"
                        name="bacnet-ip"
                        value={iface.address}
                        checked={selectedBacnetIp === iface.address}
                        onChange={(e) => setSelectedBacnetIp(e.target.value)}
                        className="w-4 h-4"
                      />
                      <div className="flex-1">
                        <div className="font-medium">{iface.address}{iface.cidr}</div>
                        <div className="text-sm text-muted-foreground">{iface.name}</div>
                      </div>
                      {iface.name.includes('(detected)') && (
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                          Recommended
                        </span>
                      )}
                    </label>
                  ))}
                </div>
              )}

              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setStep('mqtt')}
                  disabled={!selectedBacnetIp}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  Next: MQTT Configuration
                </button>
              </div>
            </div>
          )}

          {/* Step 2: MQTT Broker Configuration */}
          {step === 'mqtt' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Server className="h-5 w-5 text-blue-500" />
                <h3 className="text-lg font-semibold">Step 2: Configure MQTT Broker</h3>
              </div>

              <p className="text-sm text-muted-foreground mb-4">
                Enter the IP address of your MQTT broker. BacPipes will publish BACnet data to this broker.
              </p>

              {/* BACnet IP Summary */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="font-semibold text-green-900">BACnet IP Selected</p>
                    <p className="text-sm text-green-700">{selectedBacnetIp}</p>
                  </div>
                </div>
              </div>

              {/* MQTT Broker Input */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  MQTT Broker IP Address
                </label>
                <input
                  type="text"
                  placeholder="e.g., 10.0.60.3 or 192.168.1.100"
                  value={mqttBroker}
                  onChange={(e) => setMqttBroker(e.target.value)}
                  className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Leave empty if you don't have an MQTT broker yet (you can configure it later in Settings)
                </p>
              </div>

              <div className="flex justify-between gap-2 mt-6">
                <button
                  onClick={() => setStep('network')}
                  className="px-4 py-2 border border-border rounded hover:bg-gray-100"
                >
                  Back
                </button>
                <button
                  onClick={handleSaveConfiguration}
                  disabled={!selectedBacnetIp || saving}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {saving ? "Saving..." : "Complete Setup"}
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Saving */}
          {step === 'saving' && (
            <div className="py-8">
              <div className="flex flex-col items-center justify-center space-y-4">
                <RefreshCw className="h-12 w-12 animate-spin text-blue-500" />
                <div className="text-center">
                  <h3 className="text-lg font-semibold">Saving Configuration...</h3>
                  <p className="text-sm text-muted-foreground mt-2">
                    Please wait while we configure your system
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && step !== 'network' && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

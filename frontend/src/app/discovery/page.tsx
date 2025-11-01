"use client";

import { useState, useEffect } from "react";

interface NetworkInterface {
  name: string;
  address: string;
  cidr: string;
}

interface DiscoveryStatus {
  status: "idle" | "running" | "complete" | "error";
  jobId?: string;
  devicesFound: number;
  pointsFound: number;
  progress?: string;
  errorMessage?: string;
  startedAt?: string;
  completedAt?: string;
}

export default function DiscoveryPage() {
  // Network interfaces
  const [interfaces, setInterfaces] = useState<NetworkInterface[]>([]);
  const [loadingInterfaces, setLoadingInterfaces] = useState(true);

  // Configuration
  const [ipAddress, setIpAddress] = useState("192.168.1.35");
  const [bacnetPort, setBacnetPort] = useState("47808");
  const [timeout, setTimeout] = useState("15");
  const [deviceId, setDeviceId] = useState("3001234");

  // Discovery state
  const [discoveryStatus, setDiscoveryStatus] = useState<DiscoveryStatus>({
    status: "idle",
    devicesFound: 0,
    pointsFound: 0,
  });

  // Load network interfaces on mount
  useEffect(() => {
    loadNetworkInterfaces();
  }, []);

  // Poll discovery status when running
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (discoveryStatus.status === "running" && discoveryStatus.jobId) {
      interval = setInterval(() => {
        checkDiscoveryStatus(discoveryStatus.jobId!);
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [discoveryStatus.status, discoveryStatus.jobId]);

  async function loadNetworkInterfaces() {
    try {
      setLoadingInterfaces(true);
      const response = await fetch("/api/network/interfaces");
      if (response.ok) {
        const data = await response.json();
        setInterfaces(data.interfaces || []);
      }
    } catch (error) {
      console.error("Failed to load network interfaces:", error);
    } finally {
      setLoadingInterfaces(false);
    }
  }

  async function startDiscovery() {
    try {
      setDiscoveryStatus({
        status: "running",
        devicesFound: 0,
        pointsFound: 0,
        progress: "Starting discovery...",
      });

      const response = await fetch("/api/discovery/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ipAddress,
          port: parseInt(bacnetPort),
          timeout: parseInt(timeout),
          deviceId: parseInt(deviceId),
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setDiscoveryStatus((prev) => ({
          ...prev,
          jobId: data.jobId,
          progress: "Scanning BACnet network...",
        }));
      } else {
        setDiscoveryStatus({
          status: "error",
          devicesFound: 0,
          pointsFound: 0,
          errorMessage: data.error || "Failed to start discovery",
        });
      }
    } catch (error) {
      setDiscoveryStatus({
        status: "error",
        devicesFound: 0,
        pointsFound: 0,
        errorMessage: "Network error: " + (error as Error).message,
      });
    }
  }

  async function checkDiscoveryStatus(jobId: string) {
    try {
      const response = await fetch(`/api/discovery/status?jobId=${jobId}`);
      if (response.ok) {
        const data = await response.json();
        setDiscoveryStatus((prev) => ({
          ...prev,
          status: data.status,
          devicesFound: data.devicesFound || 0,
          pointsFound: data.pointsFound || 0,
          progress: data.progress,
          errorMessage: data.errorMessage,
          completedAt: data.completedAt,
        }));
      }
    } catch (error) {
      console.error("Failed to check discovery status:", error);
    }
  }

  async function stopDiscovery() {
    try {
      await fetch("/api/discovery/stop", { method: "POST" });
      setDiscoveryStatus({
        status: "idle",
        devicesFound: 0,
        pointsFound: 0,
      });
    } catch (error) {
      console.error("Failed to stop discovery:", error);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-foreground">BACnet Discovery</h1>
          <p className="text-sm text-muted-foreground">
            Scan your BACnet network and discover devices
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Configuration Card */}
          <div className="card bg-card p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Discovery Configuration</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* IP Address */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Local IP Address
                </label>
                {loadingInterfaces ? (
                  <div className="input bg-muted px-3 py-2 rounded-md">
                    Loading interfaces...
                  </div>
                ) : interfaces.length > 0 ? (
                  <select
                    value={ipAddress}
                    onChange={(e) => setIpAddress(e.target.value)}
                    className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                    disabled={discoveryStatus.status === "running"}
                  >
                    {interfaces.map((iface) => (
                      <option key={iface.address} value={iface.address}>
                        {iface.name} - {iface.address} ({iface.cidr})
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={ipAddress}
                    onChange={(e) => setIpAddress(e.target.value)}
                    className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                    disabled={discoveryStatus.status === "running"}
                    placeholder="192.168.1.35"
                  />
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  Select the network interface connected to your BACnet devices (configured in database)
                </p>
              </div>

              {/* BACnet Port */}
              <div>
                <label className="block text-sm font-medium mb-2">BACnet Port</label>
                <input
                  type="number"
                  value={bacnetPort}
                  onChange={(e) => setBacnetPort(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                  disabled={discoveryStatus.status === "running"}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Default: 47808 (BACnet/IP standard)
                </p>
              </div>

              {/* Timeout */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Discovery Timeout (seconds)
                </label>
                <input
                  type="number"
                  value={timeout}
                  onChange={(e) => setTimeout(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                  disabled={discoveryStatus.status === "running"}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  How long to wait for device responses
                </p>
              </div>

              {/* Device ID */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Scanner Device ID
                </label>
                <input
                  type="number"
                  value={deviceId}
                  onChange={(e) => setDeviceId(e.target.value)}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                  disabled={discoveryStatus.status === "running"}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Unique BACnet device ID for the scanner (must not conflict with existing devices). Default is fine unless you see errors.
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={startDiscovery}
                disabled={discoveryStatus.status === "running"}
                className="button px-6 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {discoveryStatus.status === "running"
                  ? "Discovery Running..."
                  : "Start Discovery"}
              </button>

              {discoveryStatus.status === "running" && (
                <button
                  onClick={stopDiscovery}
                  className="button px-6 py-2 bg-destructive text-destructive-foreground rounded-md font-medium hover:opacity-90"
                >
                  Stop Discovery
                </button>
              )}
            </div>
          </div>

          {/* Status Card */}
          {discoveryStatus.status !== "idle" && (
            <div
              className={`card p-6 rounded-lg ${
                discoveryStatus.status === "running"
                  ? "bg-blue-50 border-blue-200"
                  : discoveryStatus.status === "complete"
                  ? "bg-green-50 border-green-200"
                  : "bg-red-50 border-red-200"
              }`}
            >
              <h3 className="text-lg font-semibold mb-3">
                {discoveryStatus.status === "running" && "🔍 Discovery in Progress"}
                {discoveryStatus.status === "complete" && "✅ Discovery Complete"}
                {discoveryStatus.status === "error" && "❌ Discovery Failed"}
              </h3>

              {discoveryStatus.progress && (
                <p className="text-sm mb-3">{discoveryStatus.progress}</p>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Devices Found:</span>{" "}
                  <span className="text-lg font-bold">
                    {discoveryStatus.devicesFound}
                  </span>
                </div>
                <div>
                  <span className="font-medium">Points Found:</span>{" "}
                  <span className="text-lg font-bold">
                    {discoveryStatus.pointsFound}
                  </span>
                </div>
              </div>

              {discoveryStatus.errorMessage && (
                <div className="mt-3 p-3 bg-red-100 border border-red-300 rounded-md text-sm text-red-800">
                  {discoveryStatus.errorMessage}
                </div>
              )}

              {discoveryStatus.status === "complete" && (
                <div className="mt-4">
                  <a
                    href="/points"
                    className="inline-block px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90"
                  >
                    View Discovered Points →
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

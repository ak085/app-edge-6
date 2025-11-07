"use client";

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import {
  Activity, Wifi, WifiOff, Search, Pause, Play, X, Edit,
  BarChart3, Filter as FilterIcon
} from 'lucide-react';

interface MqttMessage {
  topic: string;
  payload: any;
  timestamp: string;
}

interface ConnectionStatus {
  connected: boolean;
  broker?: string;
  subscribed: boolean;
  lastHeartbeat?: string;
  error?: string;
}

interface Point {
  id: number;
  pointName: string;
  objectType: string;
  objectInstance: number;
  units: string | null;
  isWritable: boolean;
  mqttTopic: string;
  device: {
    deviceName: string;
    ipAddress: string;
  };
}

interface WriteModalState {
  isOpen: boolean;
  point: Point | null;
  topic: string;
  currentValue: any;
}

const PRIORITY_LEVELS = [
  { value: 1, name: 'Manual Life Safety', description: 'Highest priority - manual life safety override' },
  { value: 2, name: 'Automatic Life Safety', description: 'Automatic life safety functions' },
  { value: 3, name: 'Available', description: 'Reserved for future use' },
  { value: 4, name: 'Available', description: 'Reserved for future use' },
  { value: 5, name: 'Critical Equipment', description: 'Critical equipment control' },
  { value: 6, name: 'Minimum On/Off', description: 'Minimum on/off time control' },
  { value: 7, name: 'Available', description: 'Reserved for future use' },
  { value: 8, name: 'Manual Operator', description: 'Manual operator override (recommended)' },
  { value: 9, name: 'Available', description: 'Reserved for future use' },
  { value: 10, name: 'Available', description: 'Reserved for future use' },
  { value: 11, name: 'Available', description: 'Reserved for future use' },
  { value: 12, name: 'Available', description: 'Reserved for future use' },
  { value: 13, name: 'Available', description: 'Reserved for future use' },
  { value: 14, name: 'Available', description: 'Reserved for future use' },
  { value: 15, name: 'Available', description: 'Reserved for future use' },
  { value: 16, name: 'Default/Scheduled', description: 'Lowest priority - default/scheduled value' },
];

export default function MonitoringPage() {
  // Use Map to store latest value per topic (updates in place, no scrolling!)
  const [latestValues, setLatestValues] = useState<Map<string, MqttMessage>>(new Map());
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    connected: false,
    subscribed: false,
  });
  const [points, setPoints] = useState<Point[]>([]);
  const [filter, setFilter] = useState('');
  const [paused, setPaused] = useState(false);

  // Write modal state
  const [writeModal, setWriteModal] = useState<WriteModalState>({
    isOpen: false,
    point: null,
    topic: '',
    currentValue: null,
  });
  const [writeValue, setWriteValue] = useState('');
  const [writePriority, setWritePriority] = useState(8);
  const [releaseMode, setReleaseMode] = useState(false);
  const [writeStatus, setWriteStatus] = useState<{ type: 'success' | 'error' | 'loading' | null; message: string }>({
    type: null,
    message: '',
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  // Fetch points from database
  useEffect(() => {
    fetch('/api/points')
      .then(res => res.json())
      .then(data => {
        if (data.success && data.points) {
          setPoints(data.points);
        }
      })
      .catch(err => console.error('Failed to fetch points:', err));
  }, []);

  // Connect to SSE endpoint
  useEffect(() => {
    console.log('[Monitoring] Connecting to SSE endpoint...');

    const eventSource = new EventSource('/api/monitoring/stream');
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('[Monitoring] SSE connection opened');
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[Monitoring] Received event:', data.type);

        switch (data.type) {
          case 'connected':
            setConnectionStatus({
              connected: true,
              subscribed: false,
              broker: data.broker,
            });
            break;

          case 'subscribed':
            setConnectionStatus(prev => ({
              ...prev,
              subscribed: true,
            }));
            break;

          case 'mqtt_message':
            if (!paused) {
              const message: MqttMessage = {
                topic: data.topic,
                payload: data.payload,
                timestamp: data.timestamp,
              };

              // Update Map in place (same topic = same row)
              setLatestValues(prev => {
                const updated = new Map(prev);
                updated.set(message.topic, message);
                return updated;
              });
            }
            break;

          case 'heartbeat':
            setConnectionStatus(prev => ({
              ...prev,
              lastHeartbeat: data.timestamp,
            }));
            break;

          case 'disconnected':
            setConnectionStatus({
              connected: false,
              subscribed: false,
              error: 'Disconnected from MQTT broker',
            });
            break;

          case 'error':
            setConnectionStatus(prev => ({
              ...prev,
              error: data.message,
            }));
            break;
        }
      } catch (error) {
        console.error('[Monitoring] Error parsing SSE message:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('[Monitoring] SSE error:', error);
      setConnectionStatus({
        connected: false,
        subscribed: false,
        error: 'SSE connection error',
      });
    };

    // Cleanup on unmount
    return () => {
      console.log('[Monitoring] Cleaning up SSE connection');
      eventSource.close();
    };
  }, [paused]);

  // Convert Map to sorted array for rendering, then filter
  const sortedMessages = Array.from(latestValues.values()).sort((a, b) =>
    a.topic.localeCompare(b.topic)
  );

  const filteredMessages = sortedMessages.filter(msg =>
    msg.topic.toLowerCase().includes(filter.toLowerCase())
  );

  // Clear all values
  const handleClear = () => {
    setLatestValues(new Map());
  };

  // Toggle pause
  const handleTogglePause = () => {
    setPaused(!paused);
  };

  // Format payload for display
  const formatPayload = (payload: any): string => {
    if (typeof payload === 'object') {
      return JSON.stringify(payload, null, 2);
    }
    return String(payload);
  };

  // Get time ago string
  const getTimeAgo = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);

    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  // Find point by topic
  const findPointByTopic = (topic: string): Point | undefined => {
    return points.find(p => p.mqttTopic === topic);
  };

  // Open write modal
  const handleOpenWriteModal = (topic: string, currentValue: any) => {
    const point = findPointByTopic(topic);
    if (!point) {
      alert('Point not found for this topic');
      return;
    }

    // Note: We allow writes to all points, not just those marked as writable
    // Discovery may not always detect writability correctly

    setWriteModal({
      isOpen: true,
      point,
      topic,
      currentValue,
    });
    setWriteValue(currentValue?.value?.toString() || '');
    setWritePriority(8);
    setReleaseMode(false);
    setWriteStatus({ type: null, message: '' });
  };

  // Close write modal
  const handleCloseWriteModal = () => {
    setWriteModal({
      isOpen: false,
      point: null,
      topic: '',
      currentValue: null,
    });
    setWriteStatus({ type: null, message: '' });
  };

  // Execute write command
  const handleWriteCommand = async () => {
    if (!writeModal.point) return;

    setWriteStatus({ type: 'loading', message: 'Sending write command...' });

    try {
      const response = await fetch('/api/bacnet/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pointId: writeModal.point.id,
          value: releaseMode ? null : writeValue,
          priority: writePriority,
          release: releaseMode,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setWriteStatus({
          type: 'success',
          message: `✅ ${data.message} (Job ID: ${data.jobId})`,
        });

        // Close modal after 2 seconds
        setTimeout(() => {
          handleCloseWriteModal();
        }, 2000);
      } else {
        setWriteStatus({
          type: 'error',
          message: `❌ ${data.error}`,
        });
      }
    } catch (error) {
      setWriteStatus({
        type: 'error',
        message: `❌ Failed to send write command: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Activity className="w-8 h-8 text-purple-500" />
          <h1 className="text-3xl font-bold">Real-Time Monitoring</h1>
        </div>
        <p className="text-muted-foreground">
          Live MQTT data stream from BACnet devices
        </p>
      </div>

      {/* Connection Status Card */}
      <div className={`card bg-card p-6 rounded-lg border-2 mb-6 ${
        connectionStatus.connected ? 'border-green-300 border-l-4 border-l-green-500' : 'border-red-300 border-l-4 border-l-red-500'
      }`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              {connectionStatus.connected ? (
                <Wifi className="w-6 h-6 text-green-500" />
              ) : (
                <WifiOff className="w-6 h-6 text-red-500" />
              )}
              <h2 className={`text-xl font-semibold ${connectionStatus.connected ? 'text-green-700' : 'text-red-700'}`}>
                Connection Status
              </h2>
            </div>
            <div className="space-y-1 text-sm">
              <p>
                <span className="font-medium">MQTT Broker:</span>{' '}
                <span className={connectionStatus.connected ? 'text-green-600' : 'text-red-600'}>
                  {connectionStatus.broker || 'Not connected'}
                </span>
              </p>
              <p>
                <span className="font-medium">Subscribed:</span>{' '}
                <span className={connectionStatus.subscribed ? 'text-green-600' : 'text-yellow-600'}>
                  {connectionStatus.subscribed ? 'Yes (all topics)' : 'No'}
                </span>
              </p>
              {connectionStatus.lastHeartbeat && (
                <p>
                  <span className="font-medium">Last Heartbeat:</span>{' '}
                  {getTimeAgo(connectionStatus.lastHeartbeat)}
                </p>
              )}
              {connectionStatus.error && (
                <p className="text-red-600">
                  <span className="font-medium">Error:</span> {connectionStatus.error}
                </p>
              )}
            </div>
          </div>

          {/* Statistics */}
          <div className="text-right">
            <div className="flex items-center justify-end gap-2 mb-1">
              <BarChart3 className="w-5 h-5 text-blue-500" />
              <p className="text-sm font-medium text-muted-foreground">Statistics</p>
            </div>
            <p className="text-2xl font-bold">{latestValues.size}</p>
            <p className="text-sm text-muted-foreground">Unique Points</p>
            <p className="text-lg font-semibold mt-2">{filteredMessages.length}</p>
            <p className="text-sm text-muted-foreground">Filtered</p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="card bg-card p-4 rounded-lg border-2 border-border mb-6">
        <div className="flex flex-wrap items-center gap-4">
          {/* Filter */}
          <div className="flex-1 min-w-[200px]">
            <label className="flex items-center gap-2 text-sm font-medium mb-1">
              <Search className="w-4 h-4 text-blue-500" />
              Filter by Topic
            </label>
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="e.g., macau-casino/ahu"
              className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-2 mt-auto">
            <button
              onClick={handleTogglePause}
              className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium ${
                paused
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-yellow-600 hover:bg-yellow-700 text-white'
              }`}
            >
              {paused ? (
                <>
                  <Play className="w-4 h-4" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="w-4 h-4" />
                  Pause
                </>
              )}
            </button>
            <button
              onClick={handleClear}
              className="flex items-center gap-2 px-4 py-2 rounded-md font-medium bg-red-600 hover:bg-red-700 text-white"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
          </div>
        </div>
      </div>

      {/* Messages Table */}
      <div className="card bg-card rounded-lg border-2 border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted sticky top-0">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Time</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Topic</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Payload</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredMessages.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                    {paused
                      ? '⏸️ Streaming paused'
                      : connectionStatus.connected
                      ? '⏳ Waiting for MQTT messages...'
                      : '🔴 Not connected to MQTT broker'
                    }
                  </td>
                </tr>
              ) : (
                filteredMessages.map((msg) => {
                  const point = findPointByTopic(msg.topic);
                  return (
                    <tr
                      key={msg.topic}
                      className="border-t border-border hover:bg-muted/50"
                    >
                      <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                        {getTimeAgo(msg.timestamp)}
                      </td>
                      <td className="px-4 py-3 text-sm font-mono">
                        {msg.topic}
                        {point && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {point.pointName} ({point.device.deviceName})
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <pre className="text-xs overflow-x-auto">
                          {formatPayload(msg.payload)}
                        </pre>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {point && (
                          <button
                            onClick={() => handleOpenWriteModal(msg.topic, msg.payload)}
                            className="flex items-center gap-1 px-3 py-1 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium"
                            title={point.isWritable ? "Point is writable" : "Point writability not detected (may still work)"}
                          >
                            <Edit className="w-3 h-3" />
                            Write
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Write Modal */}
      {writeModal.isOpen && writeModal.point && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card p-6 rounded-lg border-2 border-border max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold mb-4">Write to BACnet Point</h2>

            {/* Point Information */}
            <div className="bg-muted p-4 rounded-md mb-4 text-sm">
              <p><span className="font-medium">Point:</span> {writeModal.point.pointName}</p>
              <p><span className="font-medium">Device:</span> {writeModal.point.device.deviceName}</p>
              <p><span className="font-medium">Type:</span> {writeModal.point.objectType}-{writeModal.point.objectInstance}</p>
              <p><span className="font-medium">Current Value:</span> {writeModal.currentValue?.value} {writeModal.point.units || ''}</p>
              {!writeModal.point.isWritable && (
                <div className="mt-2 p-2 bg-yellow-100 text-yellow-800 rounded text-xs">
                  ⚠️ Warning: Writability not detected during discovery. Write may fail if point is read-only.
                </div>
              )}
            </div>

            {/* Write Form */}
            <div className="space-y-4">
              {/* Release Mode Toggle */}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="releaseMode"
                  checked={releaseMode}
                  onChange={(e) => setReleaseMode(e.target.checked)}
                  className="w-4 h-4"
                />
                <label htmlFor="releaseMode" className="text-sm font-medium">
                  Release Priority (don't write value)
                </label>
              </div>

              {/* Value Input */}
              {!releaseMode && (
                <div>
                  <label className="block text-sm font-medium mb-2">
                    New Value {writeModal.point.units && `(${writeModal.point.units})`}
                  </label>
                  <input
                    type="text"
                    value={writeValue}
                    onChange={(e) => setWriteValue(e.target.value)}
                    placeholder="Enter value"
                    className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                  />
                </div>
              )}

              {/* Priority Selector */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Priority Level
                </label>
                <select
                  value={writePriority}
                  onChange={(e) => setWritePriority(Number(e.target.value))}
                  className="input w-full bg-background border-2 border-input px-3 py-2 rounded-md"
                >
                  {PRIORITY_LEVELS.map((level) => (
                    <option key={level.value} value={level.value}>
                      {level.value} - {level.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  {PRIORITY_LEVELS.find(l => l.value === writePriority)?.description}
                </p>
              </div>

              {/* Write Status */}
              {writeStatus.type && (
                <div className={`p-3 rounded-md text-sm ${
                  writeStatus.type === 'success' ? 'bg-green-100 text-green-800' :
                  writeStatus.type === 'error' ? 'bg-red-100 text-red-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {writeStatus.message}
                </div>
              )}

              {/* Buttons */}
              <div className="flex gap-2 justify-end">
                <button
                  onClick={handleCloseWriteModal}
                  disabled={writeStatus.type === 'loading'}
                  className="px-4 py-2 rounded-md border-2 border-border hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  onClick={handleWriteCommand}
                  disabled={writeStatus.type === 'loading' || (!releaseMode && !writeValue)}
                  className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {writeStatus.type === 'loading' ? 'Sending...' : releaseMode ? 'Release Priority' : 'Send Write Command'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Back to Dashboard */}
      <div className="mt-6">
        <Link
          href="/"
          className="inline-block px-4 py-2 rounded-md font-medium bg-primary text-primary-foreground hover:bg-primary/90"
        >
          ← Back to Dashboard
        </Link>
      </div>
    </div>
  );
}

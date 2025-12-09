'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  Network, MessageSquare, Clock, Server, Activity,
  TrendingUp, Wifi, Zap, Settings as SettingsIcon,
  CheckCircle2, AlertTriangle, XCircle, RefreshCw,
  Search, List
} from 'lucide-react'

interface DashboardData {
  systemStatus: 'operational' | 'degraded' | 'error'
  lastUpdate: string | null
  secondsSinceUpdate: number | null
  configuration: {
    bacnet: {
      ipAddress: string
      port: number
      deviceId: number
    }
    mqtt: {
      broker: string
      port: number
      connected: boolean
      configured: boolean
    }
    system: {
      timezone: string
      defaultPollInterval: number
      pollIntervals: {
        min: number | null
        max: number | null
        average: number | null
        distribution: Array<{ interval: number; count: number }>
      }
    }
  }
  devices: Array<{
    deviceId: number
    deviceName: string
    ipAddress: string
    pointCount: number
    enabled: boolean
  }>
  statistics: {
    totalPoints: number
    enabledPoints: number
    publishingPoints: number
    deviceCount: number
  }
  recentPoints: Array<{
    name: string
    dis: string | null
    device: string
    value: string | null
    units: string | null
    lastUpdate: string | null
    objectType: string
    objectInstance: number
  }>
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchData = async (isManualRefresh = false, signal?: AbortSignal) => {
    try {
      if (isManualRefresh) {
        setRefreshing(true)
      }

      const response = await fetch('/api/dashboard/summary', { signal })
      if (!response.ok) throw new Error('Failed to fetch dashboard data')
      const result = await response.json()
      if (result.success) {
        setData(result.data)
        setError(null)
      } else {
        setError(result.error || 'Unknown error')
      }
    } catch (err) {
      // Ignore abort errors (expected when component unmounts or auto-refresh changes)
      if (err instanceof Error && err.name === 'AbortError') {
        return
      }
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
    } finally {
      setLoading(false)
      if (isManualRefresh) {
        setRefreshing(false)
      }
    }
  }

  const handleManualRefresh = () => {
    fetchData(true)
  }

  useEffect(() => {
    const abortController = new AbortController()

    fetchData(false, abortController.signal)

    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchData(false, abortController.signal)
      }, 10000)
      return () => {
        clearInterval(interval)
        abortController.abort()
      }
    }

    return () => abortController.abort()
  }, [autoRefresh])

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading system data...</p>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="card bg-card border border-border p-8 rounded-lg max-w-md">
          <div className="flex items-center gap-3 mb-4">
            <XCircle className="w-6 h-6 text-red-500" />
            <h2 className="text-xl font-bold text-red-500">System Error</h2>
          </div>
          <p className="text-muted-foreground mb-4">{error || 'No data available'}</p>
          <button
            onClick={() => {
              setLoading(true)
              fetchData()
            }}
            className="btn bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'operational':
        return { icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-50', border: 'border-green-300' }
      case 'degraded':
        return { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-50', border: 'border-yellow-300' }
      case 'error':
        return { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50', border: 'border-red-300' }
      default:
        return { icon: AlertTriangle, color: 'text-muted-foreground', bg: 'bg-muted', border: 'border-border' }
    }
  }

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return 'Never'
    const date = new Date(timestamp)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatSecondsAgo = (seconds: number | null) => {
    if (seconds === null) return 'Unknown'
    if (seconds < 60) return `${seconds}s ago`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
    return `${Math.floor(seconds / 3600)}h ago`
  }

  const statusConfig = getStatusConfig(data.systemStatus)
  const StatusIcon = statusConfig.icon

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-foreground">Operations Dashboard</h1>
              <p className="text-sm text-muted-foreground">Building Automation Control System</p>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded"
                />
                Auto-refresh (10s)
              </label>
              <button
                onClick={handleManualRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                {refreshing ? 'Refreshing...' : 'Refresh Now'}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        {/* System Status Card */}
        <div className={`card ${statusConfig.bg} border ${statusConfig.border} p-5 rounded-lg mb-6`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <StatusIcon className={`w-8 h-8 ${statusConfig.color}`} />
              <div>
                <h2 className="text-lg font-semibold mb-1">System Status</h2>
                <p className={`text-xl font-bold capitalize ${statusConfig.color}`}>
                  {data.systemStatus}
                </p>
                <p className="text-sm text-muted-foreground">
                  Last update: {formatSecondsAgo(data.secondsSinceUpdate)}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Publishing Status</p>
              <p className="text-2xl font-bold">
                {data.statistics.publishingPoints}/{data.statistics.totalPoints}
              </p>
              <p className="text-xs text-muted-foreground">points active</p>
            </div>
          </div>
        </div>

        {/* Configuration Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {/* Network Configuration */}
          <div className="card bg-card border border-blue-200 border-l-4 border-l-blue-500 p-5 rounded-lg">
            <div className="flex items-center gap-2 mb-4">
              <Network className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold text-blue-700">Network Configuration</h3>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground">IP Address</p>
                <p className="font-mono text-sm">{data.configuration.bacnet.ipAddress}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Port</p>
                <p className="font-mono text-sm">{data.configuration.bacnet.port}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Device ID</p>
                <p className="font-mono text-sm">{data.configuration.bacnet.deviceId}</p>
              </div>
            </div>
          </div>

          {/* Message Broker */}
          <div className={`card bg-card border ${data.configuration.mqtt.connected ? 'border-green-200 border-l-4 border-l-green-500' : 'border-red-200 border-l-4 border-l-red-500'} p-5 rounded-lg`}>
            <div className="flex items-center gap-2 mb-4">
              <MessageSquare className={`w-5 h-5 ${data.configuration.mqtt.connected ? 'text-green-500' : 'text-red-500'}`} />
              <h3 className={`font-semibold ${data.configuration.mqtt.connected ? 'text-green-700' : 'text-red-700'}`}>MQTT Broker</h3>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground">Broker Address</p>
                <p className="font-mono text-sm">{data.configuration.mqtt.broker}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Port</p>
                <p className="font-mono text-sm">{data.configuration.mqtt.port}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Connection Status</p>
                <div className="flex items-center gap-2">
                  {data.configuration.mqtt.connected ? (
                    <>
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      <p className="text-sm font-semibold text-green-500">Connected</p>
                    </>
                  ) : (
                    <>
                      <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                      <p className="text-sm font-semibold text-red-500">Disconnected</p>
                    </>
                  )}
                </div>
                {!data.configuration.mqtt.configured && (
                  <p className="text-xs text-red-600 mt-1">⚠️ Configure broker in Settings</p>
                )}
              </div>
            </div>
          </div>

          {/* System Settings */}
          <div className="card bg-card border border-purple-200 border-l-4 border-l-purple-500 p-5 rounded-lg">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-5 h-5 text-purple-500" />
              <h3 className="font-semibold text-purple-700">System Settings</h3>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground">Timezone</p>
                <p className="text-sm">{data.configuration.system.timezone}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Poll Intervals</p>
                {data.configuration.system.pollIntervals.min !== null &&
                 data.configuration.system.pollIntervals.max !== null ? (
                  <div>
                    <p className="text-sm font-mono">
                      {data.configuration.system.pollIntervals.min === data.configuration.system.pollIntervals.max
                        ? `${data.configuration.system.pollIntervals.min}s`
                        : `${data.configuration.system.pollIntervals.min}s - ${data.configuration.system.pollIntervals.max}s`
                      }
                    </p>
                    {data.configuration.system.pollIntervals.distribution.length > 1 && (
                      <p className="text-xs text-muted-foreground">
                        {data.configuration.system.pollIntervals.distribution.map(d =>
                          `${d.count} @ ${d.interval}s`
                        ).join(', ')}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No active points</p>
                )}
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Last Poll</p>
                <p className="text-sm">{data.lastUpdate ? formatTimestamp(data.lastUpdate) : 'Never'}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Devices and Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Discovered Devices */}
          <div className="card bg-card border border-border p-5 rounded-lg">
            <div className="flex items-center gap-2 mb-4">
              <Server className="w-5 h-5 text-amber-500" />
              <h3 className="font-semibold">Discovered Devices ({data.statistics.deviceCount})</h3>
            </div>
            <div className="space-y-3">
              {data.devices.length === 0 ? (
                <p className="text-sm text-muted-foreground">No devices discovered</p>
              ) : (
                data.devices.map((device) => (
                  <div key={device.deviceId} className="border-b border-border pb-3 last:border-0">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{device.deviceName}</p>
                        <p className="text-xs text-muted-foreground font-mono">{device.ipAddress}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold">{device.pointCount} points</p>
                        <p className={`text-xs ${device.enabled ? 'text-green-500' : 'text-muted-foreground'}`}>
                          {device.enabled ? 'Enabled' : 'Disabled'}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Publishing Statistics */}
          <div className="card bg-card border border-border p-5 rounded-lg">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold">Publishing Statistics</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-secondary p-4 rounded-md">
                <p className="text-xs text-muted-foreground mb-1">Total Points</p>
                <p className="text-2xl font-bold">{data.statistics.totalPoints}</p>
              </div>
              <div className="bg-blue-50 border border-blue-200 p-4 rounded-md">
                <p className="text-xs text-blue-600 mb-1">Enabled</p>
                <p className="text-2xl font-bold text-blue-500">{data.statistics.enabledPoints}</p>
              </div>
              <div className="bg-green-50 border border-green-200 p-4 rounded-md">
                <p className="text-xs text-green-600 mb-1">Publishing</p>
                <p className="text-2xl font-bold text-green-500">{data.statistics.publishingPoints}</p>
              </div>
              <div className="bg-purple-50 border border-purple-200 p-4 rounded-md">
                <p className="text-xs text-purple-600 mb-1">Devices</p>
                <p className="text-2xl font-bold text-purple-500">{data.statistics.deviceCount}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Point Values */}
        <div className="card bg-card border border-border p-5 rounded-lg mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-cyan-500" />
            <h3 className="font-semibold">Recent Point Values (Top 10)</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">Device</th>
                  <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">Point Name</th>
                  <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">Type</th>
                  <th className="text-right py-2 px-3 text-sm font-medium text-muted-foreground">Value</th>
                  <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">Units</th>
                  <th className="text-left py-2 px-3 text-sm font-medium text-muted-foreground">Last Update</th>
                </tr>
              </thead>
              <tbody>
                {data.recentPoints.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-muted-foreground">
                      No recent data available
                    </td>
                  </tr>
                ) : (
                  data.recentPoints.map((point, idx) => (
                    <tr key={idx} className="border-b border-border hover:bg-muted/50">
                      <td className="py-2 px-3 text-sm">{point.device}</td>
                      <td className="py-2 px-3">
                        <div className="text-sm font-semibold text-slate-900">
                          {point.dis || point.name}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          <span className="font-mono">{point.objectType.replace('analog-', 'A').replace('binary-', 'B').replace('-input', 'I').replace('-output', 'O').replace('-value', 'V').toUpperCase()}:{point.objectInstance}</span>
                          <span className="ml-1">• {point.name.split('_')[0]}</span>
                        </div>
                      </td>
                      <td className="py-2 px-3 text-xs font-mono text-muted-foreground">
                        {point.objectType}:{point.objectInstance}
                      </td>
                      <td className="py-2 px-3 text-sm text-right font-mono">
                        {point.value !== null ? point.value : '-'}
                      </td>
                      <td className="py-2 px-3 text-xs text-muted-foreground">
                        {point.units || '-'}
                      </td>
                      <td className="py-2 px-3 text-xs text-muted-foreground">
                        {point.lastUpdate ? formatTimestamp(point.lastUpdate) : 'Never'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Navigation Links */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link href="/discovery" className="card bg-card border border-border hover:border-blue-400 hover:shadow-md p-4 rounded-lg transition-all">
            <div className="flex items-center gap-2 mb-1">
              <Search className="w-5 h-5 text-blue-500" />
              <h4 className="font-semibold">Discovery</h4>
            </div>
            <p className="text-xs text-muted-foreground">Scan network for devices</p>
          </Link>
          <Link href="/points" className="card bg-card border border-border hover:border-green-400 hover:shadow-md p-4 rounded-lg transition-all">
            <div className="flex items-center gap-2 mb-1">
              <List className="w-5 h-5 text-green-500" />
              <h4 className="font-semibold">Points</h4>
            </div>
            <p className="text-xs text-muted-foreground">Configure data points</p>
          </Link>
          <Link href="/monitoring" className="card bg-card border border-border hover:border-purple-400 hover:shadow-md p-4 rounded-lg transition-all">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-5 h-5 text-purple-500" />
              <h4 className="font-semibold">Monitoring</h4>
            </div>
            <p className="text-xs text-muted-foreground">Live data stream</p>
          </Link>
          <Link href="/settings" className="card bg-card border border-border hover:border-amber-400 hover:shadow-md p-4 rounded-lg transition-all">
            <div className="flex items-center gap-2 mb-1">
              <SettingsIcon className="w-5 h-5 text-amber-500" />
              <h4 className="font-semibold">Settings</h4>
            </div>
            <p className="text-xs text-muted-foreground">System configuration</p>
          </Link>
        </div>
      </main>
    </div>
  )
}

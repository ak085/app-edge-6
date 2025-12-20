// Dashboard summary API endpoint
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    // Get system settings
    const systemSettings = await prisma.systemSettings.findFirst();

    // Get MQTT configuration using raw SQL to bypass Prisma cache
    // This ensures we get fresh connection status from the worker
    const mqttConfigResult = await prisma.$queryRaw<Array<{
      broker: string | null;
      port: number;
      connectionStatus: string;
      lastConnected: Date | null;
      lastDataFlow: Date | null;
      tlsEnabled: boolean;
      enabled: boolean;
    }>>`
      SELECT broker, port, "connectionStatus", "lastConnected", "lastDataFlow",
             "tlsEnabled", enabled
      FROM "MqttConfig" WHERE id = 1 LIMIT 1
    `;
    const mqttConfig = mqttConfigResult[0] || null;

    // Get device statistics
    const devices = await prisma.device.findMany({
      select: {
        id: true,
        deviceId: true,
        deviceName: true,
        ipAddress: true,
        enabled: true,
        _count: {
          select: {
            points: true,
          },
        },
      },
      orderBy: {
        deviceId: 'asc',
      },
    });

    // Get point statistics
    const totalPoints = await prisma.point.count();
    const enabledPoints = await prisma.point.count({
      where: { enabled: true },
    });
    const publishingPoints = await prisma.point.count({
      where: {
        enabled: true,
        mqttPublish: true,
      },
    });

    // Get polling interval statistics for publishing points
    const publishingPointsWithIntervals = await prisma.point.findMany({
      where: {
        enabled: true,
        mqttPublish: true,
      },
      select: {
        pollInterval: true,
      },
    });

    // Calculate poll interval stats
    const intervals = publishingPointsWithIntervals.map(p => p.pollInterval);
    const minInterval = intervals.length > 0 ? Math.min(...intervals) : null;
    const maxInterval = intervals.length > 0 ? Math.max(...intervals) : null;
    const avgInterval = intervals.length > 0
      ? Math.round(intervals.reduce((sum, val) => sum + val, 0) / intervals.length)
      : null;

    // Get interval distribution (count by interval)
    const intervalCounts = intervals.reduce((acc, interval) => {
      acc[interval] = (acc[interval] || 0) + 1;
      return acc;
    }, {} as Record<number, number>);

    const intervalDistribution = Object.entries(intervalCounts)
      .map(([interval, count]) => ({ interval: Number(interval), count }))
      .sort((a, b) => a.interval - b.interval);

    // Get all publishing points with their latest values
    const recentPoints = await prisma.point.findMany({
      where: {
        mqttPublish: true,
        enabled: true,
      },
      select: {
        id: true,
        pointName: true,
        dis: true,
        objectType: true,
        objectInstance: true,
        lastValue: true,
        units: true,
        lastPollTime: true,
        device: {
          select: {
            deviceName: true,
          },
        },
      },
      orderBy: {
        lastPollTime: 'desc',
      },
    });

    // Calculate time since last update
    const lastUpdate = recentPoints[0]?.lastPollTime
      ? new Date(recentPoints[0].lastPollTime)
      : null;

    const secondsSinceUpdate = lastUpdate
      ? Math.floor((Date.now() - lastUpdate.getTime()) / 1000)
      : null;

    // Determine MQTT connection status from database (set by worker based on actual data flow)
    // This fixes the issue where status showed "connected" even for bogus broker IPs
    const isMqttConfigured = mqttConfig?.broker && mqttConfig.broker !== '10.0.60.3';
    const mqttConnectionStatus = mqttConfig?.connectionStatus || 'disconnected';
    const mqttConnected = mqttConnectionStatus === 'connected';
    const mqttConnecting = mqttConnectionStatus === 'connecting';

    // Determine system status
    let systemStatus: 'operational' | 'degraded' | 'error';
    if (!isMqttConfigured) {
      systemStatus = 'error'; // MQTT not configured
    } else if (publishingPoints === 0) {
      systemStatus = 'degraded'; // No points enabled for publishing
    } else if (mqttConnecting) {
      systemStatus = 'degraded'; // MQTT connecting - waiting for data flow
    } else if (!mqttConnected) {
      systemStatus = 'degraded'; // MQTT disconnected
    } else {
      systemStatus = 'operational'; // All good - data is flowing
    }

    // Check if first-run setup is needed
    const needsSetup = !systemSettings?.bacnetIp;

    // Build response
    return NextResponse.json({
      success: true,
      data: {
        needsSetup,
        systemStatus,
        lastUpdate: lastUpdate?.toISOString(),
        secondsSinceUpdate,
        configuration: {
          bacnet: {
            ipAddress: systemSettings?.bacnetIp || 'Not configured',
            port: systemSettings?.bacnetPort || 47808,
            deviceId: systemSettings?.bacnetDeviceId || 0,
          },
          mqtt: {
            broker: mqttConfig?.broker || 'Not configured',
            port: mqttConfig?.port || 1883,
            connected: mqttConnected,
            connecting: mqttConnecting,
            connectionStatus: mqttConnectionStatus,  // 'connected', 'connecting', 'disconnected'
            configured: isMqttConfigured,
          },
          system: {
            timezone: systemSettings?.timezone || 'UTC',
            defaultPollInterval: systemSettings?.defaultPollInterval || 60,
            pollIntervals: {
              min: minInterval,
              max: maxInterval,
              average: avgInterval,
              distribution: intervalDistribution,
            },
          },
        },
        devices: devices.map(d => ({
          deviceId: d.deviceId,
          deviceName: d.deviceName,
          ipAddress: d.ipAddress,
          pointCount: d._count.points,
          enabled: d.enabled,
        })),
        statistics: {
          totalPoints,
          enabledPoints,
          publishingPoints,
          deviceCount: devices.length,
        },
        recentPoints: recentPoints.map(p => ({
          name: p.pointName,
          dis: p.dis,
          device: p.device.deviceName,
          value: p.lastValue,
          units: p.units,
          lastUpdate: p.lastPollTime,
          objectType: p.objectType,
          objectInstance: p.objectInstance,
        })),
      },
    });
  } catch (error) {
    console.error('Dashboard summary error:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Failed to fetch dashboard data',
      },
      { status: 500 }
    );
  }
}

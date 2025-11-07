// Dashboard summary API endpoint
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    // Get system settings
    const systemSettings = await prisma.systemSettings.findFirst();

    // Get MQTT configuration
    const mqttConfig = await prisma.mqttConfig.findFirst();

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

    // Get recent point values (top 10 most recently updated)
    const recentPoints = await prisma.point.findMany({
      where: {
        mqttPublish: true,
        lastPollTime: {
          not: null,
        },
      },
      select: {
        id: true,
        pointName: true,
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
      take: 10,
    });

    // Calculate time since last update
    const lastUpdate = recentPoints[0]?.lastPollTime
      ? new Date(recentPoints[0].lastPollTime)
      : null;

    const secondsSinceUpdate = lastUpdate
      ? Math.floor((Date.now() - lastUpdate.getTime()) / 1000)
      : null;

    // Determine system status
    let systemStatus: 'operational' | 'degraded' | 'error';
    if (!mqttConfig?.enabled) {
      systemStatus = 'error';
    } else if (secondsSinceUpdate !== null && secondsSinceUpdate > 120) {
      systemStatus = 'degraded';
    } else if (publishingPoints === 0) {
      systemStatus = 'degraded';
    } else {
      systemStatus = 'operational';
    }

    // Build response
    return NextResponse.json({
      success: true,
      data: {
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
            enabled: mqttConfig?.enabled || false,
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

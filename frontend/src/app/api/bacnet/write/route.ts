// API endpoint for BACnet write commands
import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import mqtt from 'mqtt';
import { v4 as uuidv4 } from 'uuid';

/**
 * Resolve broker connection for frontend's Docker bridge network
 * Frontend cannot access 'localhost' (would resolve to frontend container)
 * External brokers (IP addresses) are used as configured
 * NOTE: BacPipes uses external MQTT broker architecture - localhost is not supported
 */
function resolveBrokerForFrontend(dbBroker: string | null, dbPort: number): { broker: string; port: number } {
  // Check if broker is configured
  if (!dbBroker || dbBroker.trim() === '') {
    throw new Error('MQTT broker not configured. Please complete the setup wizard or configure in Settings.');
  }

  // Localhost is not supported in current architecture
  // Frontend runs in Docker and needs external broker IP (e.g., 10.0.60.3)
  if (dbBroker === 'localhost' || dbBroker === '127.0.0.1') {
    throw new Error('Localhost MQTT broker is not supported. Please configure an external broker IP address in Settings.');
  }
  // External broker: use as configured
  return {
    broker: dbBroker,
    port: dbPort
  };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { pointId, value, priority = 8, release = false } = body;

    // Validate required fields
    if (!pointId) {
      return NextResponse.json(
        { success: false, error: 'pointId is required' },
        { status: 400 }
      );
    }

    if (release === false && (value === null || value === undefined)) {
      return NextResponse.json(
        { success: false, error: 'value is required when not releasing priority' },
        { status: 400 }
      );
    }

    if (priority < 1 || priority > 16) {
      return NextResponse.json(
        { success: false, error: 'priority must be between 1 and 16' },
        { status: 400 }
      );
    }

    // Get point from database
    const point = await prisma.point.findUnique({
      where: { id: pointId },
      include: { device: true },
    });

    if (!point) {
      return NextResponse.json(
        { success: false, error: 'Point not found' },
        { status: 404 }
      );
    }

    // Verify point is writable
    if (!point.isWritable) {
      return NextResponse.json(
        { success: false, error: 'Point is not writable' },
        { status: 400 }
      );
    }

    // Generate unique job ID
    const jobId = uuidv4();

    // Get MQTT configuration
    const mqttConfig = await prisma.mqttConfig.findFirst();

    if (!mqttConfig) {
      return NextResponse.json(
        { success: false, error: 'MQTT configuration not found' },
        { status: 500 }
      );
    }

    // Resolve broker for frontend's Docker network
    const { broker, port } = resolveBrokerForFrontend(mqttConfig.broker, mqttConfig.port);

    // Prepare write command
    const writeCommand = {
      jobId,
      deviceId: point.device.deviceId,
      deviceIp: point.device.ipAddress,
      objectType: point.objectType,
      objectInstance: point.objectInstance,
      value: release ? null : value,
      priority,
      release,
      timestamp: new Date().toISOString(),
      pointName: point.pointName,
      siteId: point.siteId,
      equipmentType: point.equipmentType,
      equipmentId: point.equipmentId,
    };

    // Connect to MQTT broker and publish write command
    const brokerUrl = `mqtt://${broker}:${port}`;
    const client = mqtt.connect(brokerUrl, {
      clientId: `bacpipes_write_${Date.now()}`,
      clean: true,
    });

    // Wait for connection and publish
    const publishPromise = new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        client.end();
        reject(new Error('MQTT connection timeout'));
      }, 10000);

      client.on('connect', () => {
        clearTimeout(timeout);

        // Publish write command
        client.publish(
          'bacnet/write/command',
          JSON.stringify(writeCommand),
          { qos: 1 },
          (err) => {
            client.end();
            if (err) {
              reject(err);
            } else {
              resolve();
            }
          }
        );
      });

      client.on('error', (err) => {
        clearTimeout(timeout);
        client.end();
        reject(err);
      });
    });

    try {
      await publishPromise;
    } catch (error) {
      console.error('[Write API] Failed to publish write command:', error);
      return NextResponse.json(
        {
          success: false,
          error: 'Failed to publish write command to MQTT broker',
          details: error instanceof Error ? error.message : 'Unknown error'
        },
        { status: 500 }
      );
    }

    // TODO: Store write history in database (Phase 6)
    // For now, just return success with job ID

    console.log(`[Write API] Write command published: ${jobId}`);
    console.log(`  Device: ${point.device.deviceName} (${point.device.ipAddress})`);
    console.log(`  Point: ${point.pointName} (${point.objectType}-${point.objectInstance})`);
    console.log(`  Action: ${release ? 'Release priority' : 'Write value'} ${release ? '' : value}`);
    console.log(`  Priority: ${priority}`);

    return NextResponse.json({
      success: true,
      jobId,
      message: release
        ? `Priority ${priority} release command sent`
        : `Write command sent: ${value}`,
      point: {
        id: point.id,
        name: point.pointName,
        device: point.device.deviceName,
        objectType: point.objectType,
        objectInstance: point.objectInstance,
      },
    });

  } catch (error) {
    console.error('[Write API] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

// GET endpoint to check write status (future enhancement)
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const jobId = searchParams.get('jobId');

  if (!jobId) {
    return NextResponse.json(
      { success: false, error: 'jobId parameter is required' },
      { status: 400 }
    );
  }

  // TODO: Query write history from database (Phase 6)
  // For now, return placeholder response

  return NextResponse.json({
    success: true,
    jobId,
    status: 'pending',
    message: 'Write status tracking not yet implemented',
  });
}

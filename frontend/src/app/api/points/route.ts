import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/**
 * GET /api/points
 * List all points with optional filters
 * Query params:
 *   - deviceId: Filter by device ID
 *   - objectType: Filter by object type (analog-input, etc.)
 *   - mqttPublish: Filter by MQTT publish status (true/false)
 *   - search: Search in point name
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const deviceId = searchParams.get("deviceId");
    const objectType = searchParams.get("objectType");
    const mqttPublish = searchParams.get("mqttPublish");
    const search = searchParams.get("search");

    // Build where clause
    const where: any = {};

    if (deviceId) {
      where.deviceId = parseInt(deviceId);
    }

    if (objectType) {
      where.objectType = objectType;
    }

    if (mqttPublish !== null) {
      where.mqttPublish = mqttPublish === "true";
    }

    if (search) {
      where.pointName = {
        contains: search,
        mode: "insensitive",
      };
    }

    // Fetch points with device information
    const points = await prisma.point.findMany({
      where,
      include: {
        device: {
          select: {
            id: true,
            deviceId: true,
            deviceName: true,
            ipAddress: true,
          },
        },
      },
      orderBy: [{ deviceId: "asc" }, { objectType: "asc" }, { objectInstance: "asc" }],
    });

    return NextResponse.json({
      success: true,
      points,
      count: points.length,
    });
  } catch (error) {
    console.error("Failed to fetch points:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch points: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

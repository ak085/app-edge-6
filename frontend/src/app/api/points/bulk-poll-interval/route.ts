import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/**
 * POST /api/points/bulk-poll-interval
 * Update poll interval for all MQTT-enabled points
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { pollInterval } = body;

    // Validate input
    if (!pollInterval || pollInterval < 1) {
      return NextResponse.json(
        {
          success: false,
          error: "Poll interval must be at least 1 second",
        },
        { status: 400 }
      );
    }

    if (pollInterval > 3600) {
      return NextResponse.json(
        {
          success: false,
          error: "Poll interval cannot exceed 3600 seconds (1 hour)",
        },
        { status: 400 }
      );
    }

    // Update all points where mqttPublish = true
    const result = await prisma.point.updateMany({
      where: {
        mqttPublish: true,
      },
      data: {
        pollInterval: pollInterval,
      },
    });

    return NextResponse.json({
      success: true,
      updatedCount: result.count,
      message: `Updated poll interval to ${pollInterval} seconds for ${result.count} point(s)`,
    });
  } catch (error) {
    console.error("Failed to update poll intervals:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to update poll intervals: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/**
 * GET /api/devices
 * List all discovered devices
 */
export async function GET() {
  try {
    const devices = await prisma.device.findMany({
      orderBy: [{ discoveredAt: "desc" }],
      include: {
        _count: {
          select: { points: true },
        },
      },
    });

    return NextResponse.json({
      success: true,
      devices,
      count: devices.length,
    });
  } catch (error) {
    console.error("Failed to fetch devices:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch devices: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { ipAddress, port, timeout, deviceId } = body;

    // Validate inputs
    if (!ipAddress || !port || !timeout || !deviceId) {
      return NextResponse.json(
        { success: false, error: "Missing required parameters" },
        { status: 400 }
      );
    }

    // Create discovery job in database with status="running"
    // The worker polls the database every 5 seconds and will pick up this job automatically
    const job = await prisma.discoveryJob.create({
      data: {
        ipAddress,
        port: parseInt(port),
        timeout: parseInt(timeout),
        deviceId: parseInt(deviceId),
        status: "running",
      },
    });

    return NextResponse.json({
      success: true,
      jobId: job.id,
      message: "Discovery job created - worker will process it automatically",
    });
  } catch (error) {
    console.error("Discovery start error:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to start discovery: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

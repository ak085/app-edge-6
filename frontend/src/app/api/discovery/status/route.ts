import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");

    if (!jobId) {
      return NextResponse.json(
        { success: false, error: "Missing jobId parameter" },
        { status: 400 }
      );
    }

    // Get job status from database
    const job = await prisma.discoveryJob.findUnique({
      where: { id: jobId },
    });

    if (!job) {
      return NextResponse.json(
        { success: false, error: "Job not found" },
        { status: 404 }
      );
    }

    // Count discovered devices and points
    const devicesCount = await prisma.device.count();
    const pointsCount = await prisma.point.count();

    return NextResponse.json({
      success: true,
      status: job.status,
      devicesFound: job.devicesFound,
      pointsFound: job.pointsFound,
      progress:
        job.status === "running"
          ? `Scanning... Found ${job.devicesFound} devices, ${job.pointsFound} points`
          : job.status === "complete"
          ? "Discovery completed successfully"
          : job.status === "error"
          ? "Discovery failed"
          : "Discovery cancelled",
      errorMessage: job.errorMessage,
      startedAt: job.startedAt,
      completedAt: job.completedAt,
      totalDevices: devicesCount,
      totalPoints: pointsCount,
    });
  } catch (error) {
    console.error("Discovery status error:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to get discovery status: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

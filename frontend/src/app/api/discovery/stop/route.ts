import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST() {
  try {
    // Find running discovery jobs and mark them as cancelled
    await prisma.discoveryJob.updateMany({
      where: { status: "running" },
      data: {
        status: "cancelled",
        completedAt: new Date(),
      },
    });

    return NextResponse.json({
      success: true,
      message: "Discovery stopped",
    });
  } catch (error) {
    console.error("Discovery stop error:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to stop discovery: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

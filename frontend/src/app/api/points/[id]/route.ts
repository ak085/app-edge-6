import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { generateMqttTopic } from "@/lib/mqtt-topic";

/**
 * GET /api/points/[id]
 * Get a single point by ID
 */
export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    const pointId = parseInt(params.id);

    const point = await prisma.point.findUnique({
      where: { id: pointId },
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
    });

    if (!point) {
      return NextResponse.json({ success: false, error: "Point not found" }, { status: 404 });
    }

    return NextResponse.json({
      success: true,
      point,
    });
  } catch (error) {
    console.error("Failed to fetch point:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch point: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/points/[id]
 * Update a point's configuration
 */
export async function PUT(request: Request, { params }: { params: { id: string } }) {
  try {
    const pointId = parseInt(params.id);
    const body = await request.json();

    // Extract update fields
    const {
      siteId,
      equipmentType,
      equipmentId,
      pointFunction,
      pointType,
      haystackPointName,
      mqttPublish,
      pollInterval,
      qos,
      enabled,
    } = body;

    // Prepare update data
    const updateData: any = {};

    if (siteId !== undefined) updateData.siteId = siteId;
    if (equipmentType !== undefined) updateData.equipmentType = equipmentType;
    if (equipmentId !== undefined) updateData.equipmentId = equipmentId;
    if (pointFunction !== undefined) updateData.pointFunction = pointFunction;
    if (pointType !== undefined) updateData.pointType = pointType;
    if (haystackPointName !== undefined) updateData.haystackPointName = haystackPointName;
    if (mqttPublish !== undefined) updateData.mqttPublish = mqttPublish;
    if (pollInterval !== undefined) updateData.pollInterval = parseInt(pollInterval);
    if (qos !== undefined) updateData.qos = parseInt(qos);
    if (enabled !== undefined) updateData.enabled = enabled;

    // Get current point data to generate MQTT topic
    const currentPoint = await prisma.point.findUnique({
      where: { id: pointId },
    });

    if (!currentPoint) {
      return NextResponse.json({ success: false, error: "Point not found" }, { status: 404 });
    }

    // Generate MQTT topic if Haystack tags are complete
    const pointForTopic = {
      siteId: updateData.siteId ?? currentPoint.siteId,
      equipmentType: updateData.equipmentType ?? currentPoint.equipmentType,
      equipmentId: updateData.equipmentId ?? currentPoint.equipmentId,
      objectType: currentPoint.objectType,
      objectInstance: currentPoint.objectInstance,
    };

    const mqttTopic = generateMqttTopic(pointForTopic);
    if (mqttTopic) {
      updateData.mqttTopic = mqttTopic;
    }

    // Update the point
    const updatedPoint = await prisma.point.update({
      where: { id: pointId },
      data: updateData,
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
    });

    return NextResponse.json({
      success: true,
      point: updatedPoint,
      message: "Point updated successfully",
    });
  } catch (error) {
    console.error("Failed to update point:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to update point: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

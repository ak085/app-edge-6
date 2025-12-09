import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { generateMqttTopic } from "@/lib/mqtt-topic";

/**
 * GET /api/points/[id]
 * Get a single point by ID
 */
export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const pointId = parseInt(id);

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
export async function PUT(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const pointId = parseInt(id);
    const body = await request.json();

    // Extract update fields
    const {
      siteId,
      equipmentType,
      equipmentId,
      pointFunction,
      quantity,
      subject,
      location,
      qualifier,
      dis,
      mqttPublish,
      pollInterval,
      qos,
      enabled,
      isWritable,
      minPresValue,
      maxPresValue,
    } = body;

    // Prepare update data
    const updateData: any = {};

    if (siteId !== undefined) updateData.siteId = siteId;
    if (equipmentType !== undefined) updateData.equipmentType = equipmentType;
    if (equipmentId !== undefined) updateData.equipmentId = equipmentId;
    if (pointFunction !== undefined) updateData.pointFunction = pointFunction;
    if (quantity !== undefined) updateData.quantity = quantity;
    if (subject !== undefined) updateData.subject = subject;
    if (location !== undefined) updateData.location = location;
    if (qualifier !== undefined) updateData.qualifier = qualifier;
    if (dis !== undefined) updateData.dis = dis;
    if (mqttPublish !== undefined) updateData.mqttPublish = mqttPublish;
    if (pollInterval !== undefined) updateData.pollInterval = parseInt(pollInterval);
    if (qos !== undefined) updateData.qos = parseInt(qos);
    if (enabled !== undefined) updateData.enabled = enabled;
    if (isWritable !== undefined) updateData.isWritable = isWritable;
    if (minPresValue !== undefined) updateData.minPresValue = minPresValue;
    if (maxPresValue !== undefined) updateData.maxPresValue = maxPresValue;

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

    // Generate haystack_point_name if all required fields are present
    const finalSiteId = updateData.siteId ?? currentPoint.siteId;
    const finalEquipmentType = updateData.equipmentType ?? currentPoint.equipmentType;
    const finalEquipmentId = updateData.equipmentId ?? currentPoint.equipmentId;
    const finalPointFunction = updateData.pointFunction ?? currentPoint.pointFunction;
    const finalQuantity = updateData.quantity ?? currentPoint.quantity;
    const finalSubject = updateData.subject ?? currentPoint.subject;
    const finalLocation = updateData.location ?? currentPoint.location;
    const finalQualifier = updateData.qualifier ?? currentPoint.qualifier;

    // Meta-data quantities (schedule, calendar, datetime, date) may have blank subject/location
    const metaDataQuantities = ['schedule', 'calendar', 'datetime', 'date'];
    const isMetaData = metaDataQuantities.includes(finalQuantity || '');

    // For regular points: require all 8 fields
    // For meta-data points: allow blank subject/location
    const hasRequiredFields = isMetaData
      ? (finalSiteId && finalEquipmentType && finalEquipmentId && finalPointFunction && finalQuantity && finalQualifier)
      : (finalSiteId && finalEquipmentType && finalEquipmentId && finalPointFunction && finalQuantity && finalSubject && finalLocation && finalQualifier);

    if (hasRequiredFields) {
      const components = [
        finalSiteId,
        finalEquipmentType,
        finalEquipmentId,
        finalPointFunction,
        finalQuantity,
        finalSubject,
        finalLocation,
        finalQualifier
      ].filter(Boolean);
      updateData.haystackPointName = components.join('.').toLowerCase();
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

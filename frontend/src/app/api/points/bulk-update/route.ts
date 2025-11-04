import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { generateMqttTopic } from "@/lib/mqtt-topic";

/**
 * POST /api/points/bulk-update
 * Update multiple points at once
 * Body: {
 *   pointIds: number[],
 *   updates: { field: value, ... }
 * }
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { pointIds, updates } = body;

    if (!pointIds || !Array.isArray(pointIds) || pointIds.length === 0) {
      return NextResponse.json(
        { success: false, error: "pointIds array is required" },
        { status: 400 }
      );
    }

    if (!updates || typeof updates !== "object") {
      return NextResponse.json({ success: false, error: "updates object is required" }, { status: 400 });
    }

    // Prepare update data
    const updateData: any = {};

    if (updates.siteId !== undefined) updateData.siteId = updates.siteId;
    if (updates.equipmentType !== undefined) updateData.equipmentType = updates.equipmentType;
    if (updates.equipmentId !== undefined) updateData.equipmentId = updates.equipmentId;
    if (updates.pointFunction !== undefined) updateData.pointFunction = updates.pointFunction;
    if (updates.quantity !== undefined) updateData.quantity = updates.quantity;
    if (updates.subject !== undefined) updateData.subject = updates.subject;
    if (updates.location !== undefined) updateData.location = updates.location;
    if (updates.qualifier !== undefined) updateData.qualifier = updates.qualifier;
    if (updates.dis !== undefined) updateData.dis = updates.dis;
    if (updates.mqttPublish !== undefined) updateData.mqttPublish = updates.mqttPublish;
    if (updates.pollInterval !== undefined) updateData.pollInterval = parseInt(updates.pollInterval);
    if (updates.qos !== undefined) updateData.qos = parseInt(updates.qos);
    if (updates.enabled !== undefined) updateData.enabled = updates.enabled;

    // If updating Haystack tags, need to regenerate MQTT topics and haystack names for each point individually
    if (updates.siteId !== undefined || updates.equipmentType !== undefined || updates.equipmentId !== undefined ||
        updates.pointFunction !== undefined || updates.quantity !== undefined || updates.subject !== undefined ||
        updates.location !== undefined || updates.qualifier !== undefined) {
      // Get all affected points
      const points = await prisma.point.findMany({
        where: { id: { in: pointIds } },
      });

      // Update each point individually to regenerate its MQTT topic and haystack name
      const updatePromises = points.map((point) => {
        const finalSiteId = updates.siteId !== undefined ? updates.siteId : point.siteId;
        const finalEquipmentType = updates.equipmentType !== undefined ? updates.equipmentType : point.equipmentType;
        const finalEquipmentId = updates.equipmentId !== undefined ? updates.equipmentId : point.equipmentId;
        const finalPointFunction = updates.pointFunction !== undefined ? updates.pointFunction : point.pointFunction;
        const finalQuantity = updates.quantity !== undefined ? updates.quantity : point.quantity;
        const finalSubject = updates.subject !== undefined ? updates.subject : point.subject;
        const finalLocation = updates.location !== undefined ? updates.location : point.location;
        const finalQualifier = updates.qualifier !== undefined ? updates.qualifier : point.qualifier;

        const pointForTopic = {
          siteId: finalSiteId,
          equipmentType: finalEquipmentType,
          equipmentId: finalEquipmentId,
          objectType: point.objectType,
          objectInstance: point.objectInstance,
        };

        const mqttTopic = generateMqttTopic(pointForTopic);
        const dataToUpdate = { ...updateData };
        if (mqttTopic) {
          dataToUpdate.mqttTopic = mqttTopic;
        }

        // Generate haystack_point_name if all required fields are present
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
          dataToUpdate.haystackPointName = components.join('.').toLowerCase();
        }

        return prisma.point.update({
          where: { id: point.id },
          data: dataToUpdate,
        });
      });

      await Promise.all(updatePromises);
    } else {
      // No Haystack tag changes, bulk update is fine
      await prisma.point.updateMany({
        where: { id: { in: pointIds } },
        data: updateData,
      });
    }

    return NextResponse.json({
      success: true,
      updatedCount: pointIds.length,
      message: `Successfully updated ${pointIds.length} points`,
    });
  } catch (error) {
    console.error("Failed to bulk update points:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to bulk update points: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

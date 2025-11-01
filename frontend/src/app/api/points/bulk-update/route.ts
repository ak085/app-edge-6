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
    if (updates.pointType !== undefined) updateData.pointType = updates.pointType;
    if (updates.haystackPointName !== undefined) updateData.haystackPointName = updates.haystackPointName;
    if (updates.mqttPublish !== undefined) updateData.mqttPublish = updates.mqttPublish;
    if (updates.pollInterval !== undefined) updateData.pollInterval = parseInt(updates.pollInterval);
    if (updates.qos !== undefined) updateData.qos = parseInt(updates.qos);
    if (updates.enabled !== undefined) updateData.enabled = updates.enabled;

    // If updating Haystack tags, need to regenerate MQTT topics for each point individually
    if (updates.siteId !== undefined || updates.equipmentType !== undefined || updates.equipmentId !== undefined) {
      // Get all affected points
      const points = await prisma.point.findMany({
        where: { id: { in: pointIds } },
      });

      // Update each point individually to regenerate its MQTT topic
      const updatePromises = points.map((point) => {
        const pointForTopic = {
          siteId: updates.siteId !== undefined ? updates.siteId : point.siteId,
          equipmentType: updates.equipmentType !== undefined ? updates.equipmentType : point.equipmentType,
          equipmentId: updates.equipmentId !== undefined ? updates.equipmentId : point.equipmentId,
          objectType: point.objectType,
          objectInstance: point.objectInstance,
        };

        const mqttTopic = generateMqttTopic(pointForTopic);
        const dataToUpdate = { ...updateData };
        if (mqttTopic) {
          dataToUpdate.mqttTopic = mqttTopic;
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

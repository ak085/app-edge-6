import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/**
 * GET /api/settings
 * Get system settings (SystemSettings + MqttConfig)
 */
export async function GET() {
  try {
    // Get BACnet settings (created by database seeding)
    const systemSettings = await prisma.systemSettings.findFirst();

    // Get MQTT settings (created by database seeding)
    const mqttConfig = await prisma.mqttConfig.findFirst();

    // Both should exist from seeding, but handle gracefully if not
    if (!systemSettings || !mqttConfig) {
      return NextResponse.json({
        success: false,
        error: "System not initialized - database seeding may have failed",
      }, { status: 500 });
    }

    // Combine into single response
    const settings = {
      bacnetIp: systemSettings.bacnetIp,
      bacnetPort: systemSettings.bacnetPort,
      mqttBroker: mqttConfig.broker,
      mqttPort: mqttConfig.port,
      timezone: systemSettings.timezone,
      defaultPollInterval: systemSettings.defaultPollInterval,
    };

    return NextResponse.json({
      success: true,
      settings,
    });
  } catch (error) {
    console.error("Failed to fetch settings:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch settings: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/settings
 * Update system settings (SystemSettings + MqttConfig)
 */
export async function PUT(request: Request) {
  try {
    const body = await request.json();

    // Update BACnet settings (SystemSettings table)
    const systemSettings = await prisma.systemSettings.findFirst();
    if (systemSettings) {
      await prisma.systemSettings.update({
        where: { id: systemSettings.id },
        data: {
          bacnetIp: body.bacnetIp ?? null,
          bacnetPort: body.bacnetPort,
          timezone: body.timezone || systemSettings.timezone,
          defaultPollInterval: body.defaultPollInterval !== undefined ? body.defaultPollInterval : systemSettings.defaultPollInterval,
        },
      });
    } else {
      // Should never happen (seeding creates this), but handle gracefully
      await prisma.systemSettings.create({
        data: {
          bacnetIp: body.bacnetIp ?? null,
          bacnetPort: body.bacnetPort ?? 47808,
          timezone: body.timezone || "Asia/Kuala_Lumpur",
          defaultPollInterval: body.defaultPollInterval || 60,
        },
      });
    }

    // Update MQTT settings (MqttConfig table)
    const mqttConfig = await prisma.mqttConfig.findFirst();
    if (mqttConfig) {
      await prisma.mqttConfig.update({
        where: { id: mqttConfig.id },
        data: {
          broker: body.mqttBroker ?? null,
          port: body.mqttPort,
        },
      });
    } else {
      // Should never happen (seeding creates this), but handle gracefully
      await prisma.mqttConfig.create({
        data: {
          broker: body.mqttBroker ?? null,
          port: body.mqttPort ?? 1883,
          clientId: "bacpipes_worker",
        },
      });
    }

    return NextResponse.json({
      success: true,
      message: "Settings updated successfully",
    });
  } catch (error) {
    console.error("Failed to update settings:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to update settings: " + (error as Error).message,
      },
      { status: 500 }
    );
  }
}

import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/**
 * GET /api/settings
 * Get system settings (SystemSettings + MqttConfig)
 */
export async function GET() {
  try {
    // Get BACnet settings
    let systemSettings = await prisma.systemSettings.findFirst();
    if (!systemSettings) {
      systemSettings = await prisma.systemSettings.create({
        data: {
          bacnetIp: "192.168.1.35",
          bacnetPort: 47808,
        },
      });
    }

    // Get MQTT settings
    let mqttConfig = await prisma.mqttConfig.findFirst();
    if (!mqttConfig) {
      mqttConfig = await prisma.mqttConfig.create({
        data: {
          broker: "10.0.60.2",
          port: 1883,
          clientId: "bacpipes_worker",
        },
      });
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
    let systemSettings = await prisma.systemSettings.findFirst();
    if (systemSettings) {
      await prisma.systemSettings.update({
        where: { id: systemSettings.id },
        data: {
          bacnetIp: body.bacnetIp,
          bacnetPort: body.bacnetPort,
          timezone: body.timezone || systemSettings.timezone,
          defaultPollInterval: body.defaultPollInterval !== undefined ? body.defaultPollInterval : systemSettings.defaultPollInterval,
        },
      });
    } else {
      await prisma.systemSettings.create({
        data: {
          bacnetIp: body.bacnetIp,
          bacnetPort: body.bacnetPort,
          timezone: body.timezone || "Asia/Kuala_Lumpur",
          defaultPollInterval: body.defaultPollInterval || 60,
        },
      });
    }

    // Update MQTT settings (MqttConfig table)
    let mqttConfig = await prisma.mqttConfig.findFirst();
    if (mqttConfig) {
      await prisma.mqttConfig.update({
        where: { id: mqttConfig.id },
        data: {
          broker: body.mqttBroker,
          port: body.mqttPort,
        },
      });
    } else {
      await prisma.mqttConfig.create({
        data: {
          broker: body.mqttBroker,
          port: body.mqttPort,
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

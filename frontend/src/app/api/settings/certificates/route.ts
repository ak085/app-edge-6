import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { writeFile, mkdir, unlink } from "fs/promises";
import { existsSync } from "fs";
import path from "path";

// Certificate storage directory (inside container)
const CERTS_DIR = "/app/certs";

// Allowed certificate types
const CERT_TYPES = {
  ca: { filename: "ca.crt", dbField: "caCertPath" },
  client: { filename: "client.crt", dbField: "clientCertPath" },
  key: { filename: "client.key", dbField: "clientKeyPath" },
} as const;

type CertType = keyof typeof CERT_TYPES;

/**
 * GET /api/settings/certificates
 * Get current certificate file status
 */
export async function GET() {
  try {
    const mqttConfig = await prisma.mqttConfig.findFirst();

    if (!mqttConfig) {
      return NextResponse.json({
        success: false,
        error: "MQTT configuration not found",
      }, { status: 404 });
    }

    // Check which certificates exist
    const certificates = {
      ca: {
        configured: !!mqttConfig.caCertPath,
        path: mqttConfig.caCertPath,
        exists: mqttConfig.caCertPath ? existsSync(mqttConfig.caCertPath) : false,
      },
      client: {
        configured: !!mqttConfig.clientCertPath,
        path: mqttConfig.clientCertPath,
        exists: mqttConfig.clientCertPath ? existsSync(mqttConfig.clientCertPath) : false,
      },
      key: {
        configured: !!mqttConfig.clientKeyPath,
        path: mqttConfig.clientKeyPath,
        exists: mqttConfig.clientKeyPath ? existsSync(mqttConfig.clientKeyPath) : false,
      },
    };

    return NextResponse.json({
      success: true,
      certificates,
    });
  } catch (error) {
    console.error("Failed to get certificate status:", error);
    return NextResponse.json({
      success: false,
      error: "Failed to get certificate status: " + (error as Error).message,
    }, { status: 500 });
  }
}

/**
 * POST /api/settings/certificates
 * Upload a certificate file
 * Body: multipart/form-data with 'file' and 'type' (ca, client, key)
 */
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File | null;
    const certType = formData.get("type") as CertType | null;

    // Validate inputs
    if (!file) {
      return NextResponse.json({
        success: false,
        error: "No file provided",
      }, { status: 400 });
    }

    if (!certType || !CERT_TYPES[certType]) {
      return NextResponse.json({
        success: false,
        error: "Invalid certificate type. Must be one of: ca, client, key",
      }, { status: 400 });
    }

    // Validate file size (max 100KB for certificates)
    if (file.size > 100 * 1024) {
      return NextResponse.json({
        success: false,
        error: "File too large. Maximum size is 100KB",
      }, { status: 400 });
    }

    // Validate file content (basic PEM check)
    const content = await file.text();
    if (certType === "key") {
      if (!content.includes("-----BEGIN") || !content.includes("KEY-----")) {
        return NextResponse.json({
          success: false,
          error: "Invalid key file. Must be in PEM format",
        }, { status: 400 });
      }
    } else {
      if (!content.includes("-----BEGIN CERTIFICATE-----")) {
        return NextResponse.json({
          success: false,
          error: "Invalid certificate file. Must be in PEM format",
        }, { status: 400 });
      }
    }

    // Ensure certs directory exists
    if (!existsSync(CERTS_DIR)) {
      await mkdir(CERTS_DIR, { recursive: true });
    }

    // Write file to disk
    const certConfig = CERT_TYPES[certType];
    const filePath = path.join(CERTS_DIR, certConfig.filename);
    await writeFile(filePath, content, { mode: 0o600 }); // Restrictive permissions

    // Update database with file path
    const mqttConfig = await prisma.mqttConfig.findFirst();
    if (mqttConfig) {
      await prisma.mqttConfig.update({
        where: { id: mqttConfig.id },
        data: {
          [certConfig.dbField]: filePath,
        },
      });
    }

    return NextResponse.json({
      success: true,
      message: `${certType} certificate uploaded successfully`,
      path: filePath,
    });
  } catch (error) {
    console.error("Failed to upload certificate:", error);
    return NextResponse.json({
      success: false,
      error: "Failed to upload certificate: " + (error as Error).message,
    }, { status: 500 });
  }
}

/**
 * DELETE /api/settings/certificates
 * Delete a certificate file
 * Query param: type (ca, client, key)
 */
export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const certType = searchParams.get("type") as CertType | null;

    if (!certType || !CERT_TYPES[certType]) {
      return NextResponse.json({
        success: false,
        error: "Invalid certificate type. Must be one of: ca, client, key",
      }, { status: 400 });
    }

    const certConfig = CERT_TYPES[certType];
    const filePath = path.join(CERTS_DIR, certConfig.filename);

    // Delete file if it exists
    if (existsSync(filePath)) {
      await unlink(filePath);
    }

    // Clear path in database
    const mqttConfig = await prisma.mqttConfig.findFirst();
    if (mqttConfig) {
      await prisma.mqttConfig.update({
        where: { id: mqttConfig.id },
        data: {
          [certConfig.dbField]: null,
        },
      });
    }

    return NextResponse.json({
      success: true,
      message: `${certType} certificate deleted successfully`,
    });
  } catch (error) {
    console.error("Failed to delete certificate:", error);
    return NextResponse.json({
      success: false,
      error: "Failed to delete certificate: " + (error as Error).message,
    }, { status: 500 });
  }
}

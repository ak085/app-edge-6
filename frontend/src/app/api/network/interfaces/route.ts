import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import { prisma } from "@/lib/prisma";

const execAsync = promisify(exec);

interface NetworkInterface {
  name: string;
  address: string;
  cidr: string;
}

export async function GET() {
  try {
    // Primary: Get BACnet IP from database (SystemSettings)
    const settings = await prisma.systemSettings.findFirst();

    const interfaces: NetworkInterface[] = [];

    if (settings?.bacnetIp) {
      // Add configured BACnet IP from database (only if not null)
      interfaces.push({
        name: "BACnet Network (configured)",
        address: settings.bacnetIp,
        cidr: "/24",
      });
    }

    // Secondary: Try to detect additional interfaces from system
    try {
      const { stdout } = await execAsync("ip -4 addr show");
      const lines = stdout.split("\n");
      let currentInterface = "";

      for (const line of lines) {
        const ifaceMatch = line.match(/^\d+:\s+([^:]+):/);
        if (ifaceMatch) {
          currentInterface = ifaceMatch[1];
        }

        const ipMatch = line.match(/inet\s+([0-9.]+)\/(\d+)/);
        if (ipMatch && currentInterface && currentInterface !== "lo") {
          const address = ipMatch[1];
          const cidr = `/${ipMatch[2]}`;

          // Filter out docker bridge IPs (172.17.x.x - 172.31.x.x)
          const isDockerBridge = address.startsWith("172.") &&
                                  parseInt(address.split(".")[1]) >= 17 &&
                                  parseInt(address.split(".")[1]) <= 31;

          // Only add if not already in list and not docker bridge
          if (!interfaces.some((iface) => iface.address === address) && !isDockerBridge) {
            interfaces.push({
              name: `${currentInterface} (detected)`,
              address,
              cidr,
            });
          }
        }
      }
    } catch (detectError) {
      // Detection failed, but we have database fallback
      console.log("Interface detection failed, using database only");
    }

    return NextResponse.json({
      success: true,
      interfaces,
    });
  } catch (error) {
    console.error("Failed to get network interfaces:", error);

    return NextResponse.json(
      {
        success: false,
        error: "Failed to detect network interfaces",
        interfaces: [],
      },
      { status: 500 }
    );
  }
}

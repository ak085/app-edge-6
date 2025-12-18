import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { hashPassword, verifyPassword } from '@/lib/auth'

export async function POST(request: NextRequest) {
  try {
    const { currentPin, newPin } = await request.json()

    // Validate new PIN format (4-6 digits)
    if (!newPin || !/^\d{4,6}$/.test(newPin)) {
      return NextResponse.json(
        { success: false, error: 'PIN must be 4-6 digits' },
        { status: 400 }
      )
    }

    // Get system settings
    const settings = await prisma.systemSettings.findFirst()

    if (!settings) {
      return NextResponse.json(
        { success: false, error: 'System not configured' },
        { status: 500 }
      )
    }

    // If PIN already exists, verify current PIN
    if (settings.masterPinHash) {
      if (!currentPin) {
        return NextResponse.json(
          { success: false, error: 'Current PIN is required' },
          { status: 400 }
        )
      }

      const isValid = await verifyPassword(currentPin, settings.masterPinHash)
      if (!isValid) {
        return NextResponse.json(
          { success: false, error: 'Current PIN is incorrect' },
          { status: 401 }
        )
      }
    }

    // Hash and save new PIN
    const newPinHash = await hashPassword(newPin)

    await prisma.systemSettings.update({
      where: { id: settings.id },
      data: { masterPinHash: newPinHash },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('PIN change error:', error)
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    )
  }
}

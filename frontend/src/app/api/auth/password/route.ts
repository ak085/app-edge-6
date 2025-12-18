import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { verifyPassword, hashPassword } from '@/lib/auth'

export async function POST(request: NextRequest) {
  try {
    const { currentPassword, newPassword, masterPin } = await request.json()

    if (!currentPassword || !newPassword) {
      return NextResponse.json(
        { success: false, error: 'Current and new password are required' },
        { status: 400 }
      )
    }

    if (newPassword.length < 4) {
      return NextResponse.json(
        { success: false, error: 'New password must be at least 4 characters' },
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

    // Verify master PIN if one is set
    if (settings.masterPinHash) {
      if (!masterPin) {
        return NextResponse.json(
          { success: false, error: 'Master PIN is required' },
          { status: 400 }
        )
      }

      const isPinValid = await verifyPassword(masterPin, settings.masterPinHash)
      if (!isPinValid) {
        return NextResponse.json(
          { success: false, error: 'Master PIN is incorrect' },
          { status: 401 }
        )
      }
    }

    // Verify current password
    const isValid = await verifyPassword(currentPassword, settings.adminPasswordHash)

    if (!isValid) {
      return NextResponse.json(
        { success: false, error: 'Current password is incorrect' },
        { status: 401 }
      )
    }

    // Hash new password
    const newHash = await hashPassword(newPassword)

    // Update password in database
    await prisma.systemSettings.update({
      where: { id: settings.id },
      data: { adminPasswordHash: newHash },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Password change error:', error)
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    )
  }
}

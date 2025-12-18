import { NextRequest, NextResponse } from 'next/server'
import { getIronSession } from 'iron-session'
import { prisma } from '@/lib/prisma'
import { verifyPassword } from '@/lib/auth'
import { SessionData, sessionOptions } from '@/lib/session'

export async function POST(request: NextRequest) {
  try {
    const { username, password } = await request.json()

    if (!username || !password) {
      return NextResponse.json(
        { success: false, error: 'Username and password are required' },
        { status: 400 }
      )
    }

    // Get system settings (contains admin credentials)
    // Auto-create default settings if none exist (fresh deployment)
    let settings = await prisma.systemSettings.findFirst()

    if (!settings) {
      settings = await prisma.systemSettings.create({
        data: {
          adminUsername: 'admin',
          adminPasswordHash: '', // Empty = use default "admin" password
        }
      })
    }

    // Check username
    if (username !== settings.adminUsername) {
      return NextResponse.json(
        { success: false, error: 'Invalid credentials' },
        { status: 401 }
      )
    }

    // Check password
    const isValid = await verifyPassword(password, settings.adminPasswordHash)

    if (!isValid) {
      return NextResponse.json(
        { success: false, error: 'Invalid credentials' },
        { status: 401 }
      )
    }

    // Create session - need to use response object for cookie to be set
    const response = NextResponse.json({ success: true })
    const session = await getIronSession<SessionData>(request, response, sessionOptions)
    session.username = username
    session.isLoggedIn = true
    session.expiresAt = Date.now() + 3 * 60 * 60 * 1000 // 3 hours
    await session.save()

    return response
  } catch (error) {
    console.error('Login error:', error)
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    )
  }
}

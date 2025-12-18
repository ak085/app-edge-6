import { SessionOptions } from 'iron-session'

export interface SessionData {
  username: string
  isLoggedIn: boolean
  expiresAt: number
}

export const sessionOptions: SessionOptions = {
  password: process.env.SESSION_SECRET || 'complex_password_at_least_32_characters_long',
  cookieName: 'bacpipes_session',
  cookieOptions: {
    secure: false, // Allow HTTP for internal/edge deployments
    httpOnly: true,
    sameSite: 'lax' as const,
    maxAge: 3 * 60 * 60, // 3 hours
  },
}

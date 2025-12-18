import bcrypt from 'bcryptjs'

const SALT_ROUNDS = 10

// Default password hash for "admin" - pre-computed for initial setup
// Generated with: bcrypt.hashSync('admin', 10)
export const DEFAULT_PASSWORD_HASH = '$2b$10$fkbfQ7KDpWjdlRYKCXuvh.2TSxvblJCkakqU2esBHHZ1y7W3zQyxW'

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, SALT_ROUNDS)
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  // If no hash is set (empty string), use default password "admin"
  if (!hash || hash === '') {
    return password === 'admin'
  }
  return bcrypt.compare(password, hash)
}

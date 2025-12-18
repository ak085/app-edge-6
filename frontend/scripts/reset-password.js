#!/usr/bin/env node
/**
 * Reset Admin Password
 *
 * Usage: node scripts/reset-password.js
 *
 * This script resets the admin password to the default "admin".
 * Use this if you forget the password and cannot access the system.
 */

const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

const prisma = new PrismaClient();

async function main() {
  console.log('🔐 Resetting admin password to "admin"...');

  const settings = await prisma.systemSettings.findFirst();

  if (!settings) {
    console.error('❌ System settings not found. Database may not be initialized.');
    process.exit(1);
  }

  // Generate hash for "admin"
  const defaultHash = await bcrypt.hash('admin', 10);

  await prisma.systemSettings.update({
    where: { id: settings.id },
    data: { adminPasswordHash: defaultHash },
  });

  console.log('✅ Password has been reset to "admin".');
  console.log('   Please login and change it immediately.');
}

main()
  .catch((e) => {
    console.error('❌ Error:', e.message);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

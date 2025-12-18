#!/usr/bin/env node
/**
 * Set Master PIN via CLI
 *
 * Usage: node scripts/set-pin.js <new-pin>
 *
 * This script sets the master PIN directly without requiring the current PIN.
 * Use this for remote management or initial setup.
 *
 * Example:
 *   node scripts/set-pin.js 1234
 *   docker exec bacpipes-frontend node scripts/set-pin.js 1234
 */

const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

const prisma = new PrismaClient();

async function main() {
  const newPin = process.argv[2];

  if (!newPin) {
    console.log('Usage: node scripts/set-pin.js <new-pin>');
    console.log('');
    console.log('Example: node scripts/set-pin.js 1234');
    console.log('');
    console.log('PIN must be 4-6 digits.');
    process.exit(1);
  }

  // Validate PIN format
  if (!/^\d{4,6}$/.test(newPin)) {
    console.error('❌ PIN must be 4-6 digits (numbers only).');
    process.exit(1);
  }

  console.log('🔐 Setting Master PIN...');

  const settings = await prisma.systemSettings.findFirst();

  if (!settings) {
    console.error('❌ System settings not found. Database may not be initialized.');
    process.exit(1);
  }

  // Hash the new PIN
  const pinHash = await bcrypt.hash(newPin, 10);

  await prisma.systemSettings.update({
    where: { id: settings.id },
    data: { masterPinHash: pinHash },
  });

  console.log('✅ Master PIN has been set successfully.');
  console.log('   This PIN is now required to change the admin password.');
}

main()
  .catch((e) => {
    console.error('❌ Error:', e.message);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

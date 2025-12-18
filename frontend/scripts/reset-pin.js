#!/usr/bin/env node
/**
 * Reset Master PIN
 *
 * Usage: node scripts/reset-pin.js
 *
 * This script resets the master PIN to null, allowing you to set a new one
 * from the Settings page. Use this if you forget your master PIN.
 */

const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

async function main() {
  console.log('🔐 Resetting Master PIN...');

  const settings = await prisma.systemSettings.findFirst();

  if (!settings) {
    console.error('❌ System settings not found. Database may not be initialized.');
    process.exit(1);
  }

  if (!settings.masterPinHash) {
    console.log('ℹ️  No master PIN is currently set.');
    process.exit(0);
  }

  await prisma.systemSettings.update({
    where: { id: settings.id },
    data: { masterPinHash: null },
  });

  console.log('✅ Master PIN has been reset.');
  console.log('   You can now set a new PIN from the Settings page.');
}

main()
  .catch((e) => {
    console.error('❌ Error:', e.message);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

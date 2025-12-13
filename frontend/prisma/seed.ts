import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Seeding database...')

  // Seed MQTT Configuration
  const mqttConfig = await prisma.mqttConfig.upsert({
    where: { id: 1 },
    update: {},
    create: {
      broker: process.env.MQTT_BROKER || null,  // NULL - requires setup wizard
      port: parseInt(process.env.MQTT_PORT || '1883'),
      clientId: process.env.MQTT_CLIENT_ID || 'bacpipes_worker',
      keepAlive: 30,
      writeCommandTopic: 'bacnet/write/command',
      writeResultTopic: 'bacnet/write/result',
      enabled: true,
    },
  })
  console.log('✅ MQTT config:', mqttConfig)

  // Seed System Settings
  const systemSettings = await prisma.systemSettings.upsert({
    where: { id: 1 },
    update: {},
    create: {
      bacnetIp: process.env.BACNET_IP || null,  // NULL - requires setup wizard
      bacnetPort: parseInt(process.env.BACNET_PORT || '47808'),
      bacnetDeviceId: parseInt(process.env.BACNET_DEVICE_ID || '3001234'),
      discoveryTimeout: 15,
      timezone: process.env.TZ || 'Asia/Kuala_Lumpur',
      defaultPollInterval: parseInt(process.env.DEFAULT_POLL_INTERVAL || '60'),
      configRefreshInterval: parseInt(process.env.CONFIG_REFRESH_INTERVAL || '60'),
      dashboardRefresh: 10,
      logRetentionDays: 30,
    },
  })
  console.log('✅ System settings:', systemSettings)

  console.log('🌱 Seeding complete!')
}

main()
  .catch((e) => {
    console.error('❌ Error seeding database:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })

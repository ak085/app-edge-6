-- Add connection status tracking fields to MqttConfig
ALTER TABLE "MqttConfig" ADD COLUMN IF NOT EXISTS "connectionStatus" TEXT NOT NULL DEFAULT 'disconnected';
ALTER TABLE "MqttConfig" ADD COLUMN IF NOT EXISTS "lastConnected" TIMESTAMP(3);
ALTER TABLE "MqttConfig" ADD COLUMN IF NOT EXISTS "lastDataFlow" TIMESTAMP(3);

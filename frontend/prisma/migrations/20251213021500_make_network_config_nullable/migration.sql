-- Make MQTT broker and BACnet IP nullable for setup wizard
-- This forces users through first-run configuration instead of using hardcoded defaults

-- MqttConfig: Make broker nullable
ALTER TABLE "MqttConfig" ALTER COLUMN "broker" DROP DEFAULT;
ALTER TABLE "MqttConfig" ALTER COLUMN "broker" DROP NOT NULL;

-- SystemSettings: Make bacnetIp nullable
ALTER TABLE "SystemSettings" ALTER COLUMN "bacnetIp" DROP DEFAULT;
ALTER TABLE "SystemSettings" ALTER COLUMN "bacnetIp" DROP NOT NULL;

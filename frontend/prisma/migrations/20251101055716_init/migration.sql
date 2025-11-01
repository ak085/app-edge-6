-- CreateTable
CREATE TABLE "Device" (
    "id" SERIAL NOT NULL,
    "deviceId" INTEGER NOT NULL,
    "deviceName" TEXT NOT NULL,
    "ipAddress" TEXT NOT NULL,
    "port" INTEGER NOT NULL DEFAULT 47808,
    "vendorId" INTEGER,
    "vendorName" TEXT,
    "description" TEXT,
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "discoveredAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "lastSeenAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Device_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Point" (
    "id" SERIAL NOT NULL,
    "deviceId" INTEGER NOT NULL,
    "objectType" TEXT NOT NULL,
    "objectInstance" INTEGER NOT NULL,
    "pointName" TEXT NOT NULL,
    "description" TEXT,
    "units" TEXT,
    "siteId" TEXT,
    "equipmentType" TEXT,
    "equipmentId" TEXT,
    "pointFunction" TEXT,
    "pointType" TEXT,
    "haystackPointName" TEXT,
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "mqttPublish" BOOLEAN NOT NULL DEFAULT false,
    "mqttTopic" TEXT,
    "pollInterval" INTEGER NOT NULL DEFAULT 60,
    "qos" INTEGER NOT NULL DEFAULT 1,
    "isReadable" BOOLEAN NOT NULL DEFAULT true,
    "isWritable" BOOLEAN NOT NULL DEFAULT false,
    "priorityArray" BOOLEAN NOT NULL DEFAULT false,
    "priorityLevel" INTEGER,
    "lastValue" TEXT,
    "lastPollTime" TIMESTAMP(3),
    "errorCount" INTEGER NOT NULL DEFAULT 0,
    "lastError" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Point_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "MqttConfig" (
    "id" SERIAL NOT NULL,
    "broker" TEXT NOT NULL DEFAULT '10.0.60.50',
    "port" INTEGER NOT NULL DEFAULT 1883,
    "clientId" TEXT NOT NULL DEFAULT 'bacpipes_worker',
    "username" TEXT,
    "password" TEXT,
    "keepAlive" INTEGER NOT NULL DEFAULT 30,
    "writeCommandTopic" TEXT NOT NULL DEFAULT 'bacnet/write/command',
    "writeResultTopic" TEXT NOT NULL DEFAULT 'bacnet/write/result',
    "enabled" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "MqttConfig_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "InfluxConfig" (
    "id" SERIAL NOT NULL,
    "host" TEXT NOT NULL DEFAULT '10.0.60.5',
    "port" INTEGER NOT NULL DEFAULT 8086,
    "organization" TEXT DEFAULT 'bacnet',
    "bucket" TEXT DEFAULT 'bacnet_data',
    "token" TEXT,
    "retentionDays" INTEGER NOT NULL DEFAULT 30,
    "enabled" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "InfluxConfig_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "WriteHistory" (
    "id" SERIAL NOT NULL,
    "jobId" TEXT NOT NULL,
    "pointId" INTEGER NOT NULL,
    "value" TEXT,
    "priority" INTEGER NOT NULL,
    "release" BOOLEAN NOT NULL DEFAULT false,
    "success" BOOLEAN NOT NULL,
    "errorMessage" TEXT,
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "WriteHistory_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ErrorLog" (
    "id" SERIAL NOT NULL,
    "pointId" INTEGER,
    "source" TEXT,
    "message" TEXT NOT NULL,
    "stackTrace" TEXT,
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ErrorLog_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "DiscoveryJob" (
    "id" TEXT NOT NULL,
    "ipAddress" TEXT NOT NULL,
    "port" INTEGER NOT NULL DEFAULT 47808,
    "timeout" INTEGER NOT NULL DEFAULT 15,
    "deviceId" INTEGER NOT NULL DEFAULT 3001234,
    "status" TEXT NOT NULL,
    "devicesFound" INTEGER NOT NULL DEFAULT 0,
    "pointsFound" INTEGER NOT NULL DEFAULT 0,
    "errorMessage" TEXT,
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAt" TIMESTAMP(3),

    CONSTRAINT "DiscoveryJob_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SystemSettings" (
    "id" SERIAL NOT NULL,
    "bacnetIp" TEXT NOT NULL DEFAULT '192.168.1.35',
    "bacnetPort" INTEGER NOT NULL DEFAULT 47808,
    "bacnetDeviceId" INTEGER NOT NULL DEFAULT 3001234,
    "discoveryTimeout" INTEGER NOT NULL DEFAULT 15,
    "timezone" TEXT NOT NULL DEFAULT 'Asia/Kuala_Lumpur',
    "defaultPollInterval" INTEGER NOT NULL DEFAULT 60,
    "configRefreshInterval" INTEGER NOT NULL DEFAULT 60,
    "dashboardRefresh" INTEGER NOT NULL DEFAULT 10,
    "logRetentionDays" INTEGER NOT NULL DEFAULT 30,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SystemSettings_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Device_deviceId_key" ON "Device"("deviceId");

-- CreateIndex
CREATE INDEX "Device_deviceId_idx" ON "Device"("deviceId");

-- CreateIndex
CREATE INDEX "Device_enabled_idx" ON "Device"("enabled");

-- CreateIndex
CREATE INDEX "Point_deviceId_idx" ON "Point"("deviceId");

-- CreateIndex
CREATE INDEX "Point_enabled_idx" ON "Point"("enabled");

-- CreateIndex
CREATE INDEX "Point_mqttPublish_idx" ON "Point"("mqttPublish");

-- CreateIndex
CREATE INDEX "Point_siteId_equipmentType_equipmentId_idx" ON "Point"("siteId", "equipmentType", "equipmentId");

-- CreateIndex
CREATE UNIQUE INDEX "Point_deviceId_objectType_objectInstance_key" ON "Point"("deviceId", "objectType", "objectInstance");

-- CreateIndex
CREATE UNIQUE INDEX "WriteHistory_jobId_key" ON "WriteHistory"("jobId");

-- CreateIndex
CREATE INDEX "WriteHistory_pointId_idx" ON "WriteHistory"("pointId");

-- CreateIndex
CREATE INDEX "WriteHistory_timestamp_idx" ON "WriteHistory"("timestamp");

-- CreateIndex
CREATE INDEX "WriteHistory_success_idx" ON "WriteHistory"("success");

-- CreateIndex
CREATE INDEX "ErrorLog_pointId_idx" ON "ErrorLog"("pointId");

-- CreateIndex
CREATE INDEX "ErrorLog_timestamp_idx" ON "ErrorLog"("timestamp");

-- CreateIndex
CREATE INDEX "ErrorLog_source_idx" ON "ErrorLog"("source");

-- CreateIndex
CREATE INDEX "DiscoveryJob_status_idx" ON "DiscoveryJob"("status");

-- CreateIndex
CREATE INDEX "DiscoveryJob_startedAt_idx" ON "DiscoveryJob"("startedAt");

-- AddForeignKey
ALTER TABLE "Point" ADD CONSTRAINT "Point_deviceId_fkey" FOREIGN KEY ("deviceId") REFERENCES "Device"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "WriteHistory" ADD CONSTRAINT "WriteHistory_pointId_fkey" FOREIGN KEY ("pointId") REFERENCES "Point"("id") ON DELETE CASCADE ON UPDATE CASCADE;

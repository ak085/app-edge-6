-- AlterTable
ALTER TABLE "SystemSettings" ADD COLUMN     "adminPasswordHash" TEXT NOT NULL DEFAULT '',
ADD COLUMN     "adminUsername" TEXT NOT NULL DEFAULT 'admin';

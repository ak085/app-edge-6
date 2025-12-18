/*
  Warnings:

  - You are about to drop the column `pointType` on the `Point` table. All the data in the column will be lost.
  - You are about to drop the `InfluxConfig` table. If the table is not empty, all the data it contains will be lost.

*/
-- AlterTable
ALTER TABLE "Point" DROP COLUMN "pointType";

-- DropTable
DROP TABLE "public"."InfluxConfig";

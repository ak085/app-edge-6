/**
 * MQTT Topic Generation Utility
 *
 * Generates standardized MQTT topics based on Haystack tags
 * Format: {site}/{equipmentType}_{equipmentId}/{objectType}{objectInstance}/presentValue
 * Example: klcc/ahu_12/analogInput435/presentValue
 */

export interface PointForTopic {
  siteId?: string | null;
  equipmentType?: string | null;
  equipmentId?: string | null;
  objectType: string;
  objectInstance: number;
}

/**
 * Generate MQTT topic from point Haystack tags
 * Returns empty string if required tags are missing
 */
export function generateMqttTopic(point: PointForTopic): string {
  const { siteId, equipmentType, equipmentId, objectType, objectInstance } = point;

  // Require all three Haystack tags for valid topic
  if (!siteId || !equipmentType || !equipmentId) {
    return "";
  }

  // Clean and format components
  const site = siteId.toLowerCase().replace(/\s+/g, "_");
  const equipment = `${equipmentType.toLowerCase()}_${equipmentId}`.replace(/\s+/g, "_");
  const object = `${objectType.replace(/-/g, "")}${objectInstance}`; // Remove hyphens from object type

  return `${site}/${equipment}/${object}/presentValue`;
}

/**
 * Validate if point has minimum tags required for MQTT publishing
 */
export function canPublishToMqtt(point: PointForTopic): boolean {
  return !!(point.siteId && point.equipmentType && point.equipmentId);
}

/**
 * Preview topic generation - returns either valid topic or error message
 */
export function previewMqttTopic(point: PointForTopic): { valid: boolean; topic: string; error?: string } {
  if (!point.siteId) {
    return { valid: false, topic: "", error: "Site ID required" };
  }
  if (!point.equipmentType) {
    return { valid: false, topic: "", error: "Equipment Type required" };
  }
  if (!point.equipmentId) {
    return { valid: false, topic: "", error: "Equipment ID required" };
  }

  const topic = generateMqttTopic(point);
  return { valid: true, topic };
}

/**
 * Room label precedence order (matches backend PHOTO_SEQUENCE_PRIORITY)
 * Lower index = higher precedence (appears first)
 */
const PHOTO_SEQUENCE_PRIORITY = [
  "front_exterior",  // 1. Front exterior (primary)
  "living_room",     // 2. Living area
  "kitchen",         // 3. Kitchen
  "master_bedroom",  // 4. Primary bedroom
  "primary_bedroom",
  "bathroom",        // 5. Bathrooms
  "master_bathroom",
  "primary_bathroom",
  "guest_bathroom",
  "dining_room",     // 6. Other interior rooms
  "bedroom",
  "guest_bedroom",
  "backyard",        // 7. Backyard / patio
  "patio",
  "deck",
  "garage",
  "basement",
  "attic",
  "community",       // 8. Community / amenities
  "amenities",
  "floor_plan",      // 9. Floor plans / maps
  "map",
  "other"            // Last: other
];

// Create precedence dictionary for fast lookup
const ROOM_LABEL_PRECEDENCE: Record<string, number> = {};
PHOTO_SEQUENCE_PRIORITY.forEach((label, idx) => {
  ROOM_LABEL_PRECEDENCE[label] = idx;
});

// Add missing labels with low precedence
ROOM_LABEL_PRECEDENCE["back_exterior"] = 12;  // Group with backyard/patio
ROOM_LABEL_PRECEDENCE["side_exterior"] = 12;  // Group with backyard/patio

const MAX_PRECEDENCE = 999;

/**
 * Get the precedence order for a room label.
 * Lower number = higher precedence (appears first).
 * 
 * @param roomLabel Room label string (e.g., "front_exterior", "living_room")
 * @returns Precedence integer (0 = first, higher = later, 999 = last/unknown)
 */
export function getRoomLabelPrecedence(roomLabel: string | null | undefined): number {
  if (!roomLabel) {
    return MAX_PRECEDENCE;
  }
  return ROOM_LABEL_PRECEDENCE[roomLabel.toLowerCase()] ?? MAX_PRECEDENCE;
}

/**
 * Sort images by room label precedence, then by upload order.
 * Exterior images (front_exterior) will appear first.
 * 
 * @param images Array of image objects with detected_features.room_label
 * @returns Sorted array of images
 */
export function sortImagesByPrecedence<T extends { detected_features?: { room_label?: string } }>(
  images: T[]
): T[] {
  // Create array with original index to preserve upload order for same precedence
  const imagesWithIndex = images.map((img, idx) => ({ img, originalIndex: idx }));
  
  return imagesWithIndex
    .sort((a, b) => {
      const roomLabelA = a.img.detected_features?.room_label;
      const roomLabelB = b.img.detected_features?.room_label;
      
      const precedenceA = getRoomLabelPrecedence(roomLabelA);
      const precedenceB = getRoomLabelPrecedence(roomLabelB);
      
      // Sort by precedence first (lower number = higher precedence)
      if (precedenceA !== precedenceB) {
        return precedenceA - precedenceB;
      }
      
      // If same precedence, maintain original upload order
      return a.originalIndex - b.originalIndex;
    })
    .map(({ img }) => img);
}

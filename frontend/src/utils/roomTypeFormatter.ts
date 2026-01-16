/**
 * Converts snake_case room type to Title Case
 * Example: "front_exterior" -> "Front Exterior"
 */
export function formatRoomType(roomType: string | null | undefined): string {
  if (!roomType) return '';
  
  return roomType
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

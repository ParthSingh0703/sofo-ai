"""
Helper functions for renaming image files based on labels.
Handles file name sanitization and renaming operations.
"""
import os
import re
from pathlib import Path
from typing import Optional
from services.api.database import get_db

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")

# Room label precedence order (matches PHOTO_SEQUENCE_PRIORITY from enrichment_photo_sequencing.py)
# Lower index = higher precedence (appears first in sequence)
PHOTO_SEQUENCE_PRIORITY = [
    "front_exterior",  # 1. Front exterior (primary)
    "living_room",     # 2. Living area
    "kitchen",         # 3. Kitchen
    "master_bedroom",  # 4. Primary bedroom
    "primary_bedroom",
    "bathroom",        # 5. Bathrooms
    "master_bathroom",
    "primary_bathroom",
    "guest_bathroom",
    "dining_room",     # 6. Other interior rooms
    "bedroom",
    "guest_bedroom",
    "backyard",        # 7. Backyard / patio
    "patio",
    "deck",
    "garage",
    "basement",
    "attic",
    "community",       # 8. Community / amenities
    "amenities",
    "floor_plan",      # 9. Floor plans / maps
    "map",
    "other"            # Last: other
]

# Create precedence dictionary for fast lookup
ROOM_LABEL_PRECEDENCE = {label: idx for idx, label in enumerate(PHOTO_SEQUENCE_PRIORITY)}
# Add missing labels with low precedence
ROOM_LABEL_PRECEDENCE.update({
    "back_exterior": 12,  # Group with backyard/patio
    "side_exterior": 12,  # Group with backyard/patio
})

# Unknown labels get highest precedence number
_MAX_PRECEDENCE = 999


def format_label_to_filename(label: str) -> str:
    """
    Convert a label (e.g., "living_room", "Living Room") to a sanitized filename.
    
    Args:
        label: The label to convert (can be snake_case, Title Case, etc.)
        
    Returns:
        Sanitized filename-friendly string (e.g., "Living Room")
        
    Examples:
        "living_room" -> "Living Room"
        "front_exterior" -> "Front Exterior"
        "master_bedroom" -> "Master Bedroom"
        "Living Room 1" -> "Living Room 1"
    """
    if not label:
        return ""
    
    # Convert snake_case to Title Case
    # Replace underscores with spaces
    formatted = label.replace("_", " ")
    
    # Title case (capitalize first letter of each word)
    formatted = formatted.title()
    
    # Remove invalid filename characters (keep spaces, dots, dashes, alphanumeric)
    # Windows: < > : " / \ | ? *
    # Unix/Linux: /
    formatted = re.sub(r'[<>:"/\\|?*]', '', formatted)
    
    # Remove leading/trailing spaces and dots
    formatted = formatted.strip('. ')
    
    # Replace multiple spaces with single space
    formatted = re.sub(r'\s+', ' ', formatted)
    
    return formatted


def get_room_label_precedence(room_label: Optional[str]) -> int:
    """
    Get the precedence order for a room label.
    Lower number = higher precedence (appears first).
    
    Args:
        room_label: Room label string (e.g., "front_exterior", "living_room")
        
    Returns:
        Precedence integer (0 = first, higher = later, 999 = last/unknown)
    """
    if not room_label:
        return _MAX_PRECEDENCE
    return ROOM_LABEL_PRECEDENCE.get(room_label.lower(), _MAX_PRECEDENCE)


def sequence_and_rename_images(listing_id: str) -> None:
    """
    Sequence all images for a listing by room label precedence and rename files with sequence numbers.
    
    Images are sorted by room label precedence order, then renamed with sequence numbers:
    - "001 Front Exterior.jpeg"
    - "002 Living Room.jpeg"
    - etc.
    
    Args:
        listing_id: The listing ID (UUID string)
    """
    from services.api.database import get_db
    
    with get_db() as (conn, cur):
        # Get all images with their labels and upload order
        cur.execute(
            """
            SELECT id, ai_suggested_label, final_label, uploaded_at
            FROM listing_images
            WHERE listing_id = %s
            ORDER BY uploaded_at ASC
            """,
            (listing_id,)
        )
        images = cur.fetchall()
        
        # Prepare list of (image_id, label, precedence, upload_order) tuples
        image_data = []
        upload_order = 0
        for row in images:
            image_id = str(row[0])
            # Use final_label if available, otherwise ai_suggested_label
            label = row[2] if row[2] else row[1]
            if label:
                upload_order += 1
                precedence = get_room_label_precedence(label)
                image_data.append((image_id, label, precedence, upload_order))
        
        # Sort by precedence, then by upload order (matches generate_photo_sequence logic)
        image_data.sort(key=lambda x: (x[2], x[3]))  # Sort by precedence, then by upload order
        
        # Rename each image with sequence number
        for sequence_num, (image_id, label, _, _) in enumerate(image_data, start=1):
            rename_image_file(image_id, label, listing_id, sequence_number=sequence_num)


def rename_image_file(image_id: str, new_label: str, listing_id: Optional[str] = None, sequence_number: Optional[int] = None) -> Optional[str]:
    """
    Rename an image file in storage based on a label and optional sequence number.
    
    Args:
        image_id: The image ID (UUID string)
        new_label: The new label to use for the filename
        listing_id: Optional listing ID (will be fetched if not provided)
        sequence_number: Optional sequence number to prefix filename (e.g., 1 → "001 Front Exterior.jpeg")
        
    Returns:
        New storage_path relative to STORAGE_ROOT, or None if rename failed
    """
    if not new_label:
        return None
    
    try:
        with get_db() as (conn, cur):
            # Get current storage_path and listing_id
            cur.execute(
                """
                SELECT storage_path, listing_id
                FROM listing_images
                WHERE id = %s
                """,
                (image_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return None
            
            old_storage_path = row[0]
            listing_id = listing_id or str(row[1])
            
            # Build old absolute path
            old_abs_path = os.path.join(STORAGE_ROOT, old_storage_path)
            
            if not os.path.exists(old_abs_path):
                print(f"Warning: Image file not found at {old_abs_path}")
                return None
            
            # Get file extension from old filename
            old_path_obj = Path(old_abs_path)
            file_extension = old_path_obj.suffix  # e.g., ".jpeg", ".jpg", ".png"
            
            # Format label to filename
            filename_base = format_label_to_filename(new_label)
            
            if not filename_base:
                return None
            
            # Add sequence number prefix if provided (e.g., "001 Front Exterior")
            if sequence_number is not None:
                sequence_prefix = f"{sequence_number:03d} "  # 3-digit with leading zeros
                filename_base = f"{sequence_prefix}{filename_base}"
            
            # Build new filename with extension
            new_filename = f"{filename_base}{file_extension}"
            
            # Build new directory and path
            rel_dir = os.path.join("images", listing_id)
            new_rel_path = os.path.join(rel_dir, new_filename)
            new_abs_path = os.path.join(STORAGE_ROOT, new_rel_path)
            
            # Handle duplicate filenames by adding a number suffix
            if os.path.exists(new_abs_path) and new_abs_path != old_abs_path:
                # File with this name already exists, add number suffix
                base_name = filename_base
                counter = 1
                while os.path.exists(new_abs_path):
                    new_filename = f"{base_name} {counter}{file_extension}"
                    new_rel_path = os.path.join(rel_dir, new_filename)
                    new_abs_path = os.path.join(STORAGE_ROOT, new_rel_path)
                    counter += 1
                    if counter > 1000:  # Safety limit
                        print(f"Error: Could not find unique filename for {image_id}")
                        return None
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(new_abs_path), exist_ok=True)
            
            # Rename the file
            os.rename(old_abs_path, new_abs_path)
            
            # Update database with new storage_path
            cur.execute(
                """
                UPDATE listing_images
                SET storage_path = %s
                WHERE id = %s
                """,
                (new_rel_path, image_id)
            )
            
            return new_rel_path
            
    except Exception as e:
        print(f"Error renaming image file {image_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

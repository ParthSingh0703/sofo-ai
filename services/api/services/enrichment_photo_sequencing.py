"""
Photo sequencing service for MLS photo order recommendations.
"""
from typing import List, Dict, Any, Optional
from services.api.database import get_db


# Priority order for MLS photo sequencing
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
    "floor_plan",     # 9. Floor plans / maps
    "map",
    "other"           # Last: other
]


def generate_photo_sequence(listing_id: str) -> List[str]:
    """
    Generate recommended MLS photo order for a listing.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        Ordered list of image_ids in recommended sequence
    """
    # Get all images for listing with their labels
    images = _get_listing_images_with_labels(listing_id)
    
    if not images:
        return []
    
    # Sort images by priority
    sorted_images = sorted(
        images,
        key=lambda img: _get_sequence_priority(img['room_label'], img['upload_order'])
    )
    
    return [img['id'] for img in sorted_images]


def _get_listing_images_with_labels(listing_id: str) -> List[Dict[str, Any]]:
    """
    Get all images for a listing with their labels and upload order.
    """
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT 
                id,
                ai_suggested_label,
                final_label,
                display_order,
                is_primary,
                uploaded_at
            FROM listing_images
            WHERE listing_id = %s
            ORDER BY uploaded_at ASC
            """,
            (listing_id,)
        )
        
        images = []
        for row in cur.fetchall():
            image_id, ai_label, final_label, display_order, is_primary, uploaded_at = row
            
            # Use final_label if set, otherwise ai_suggested_label
            room_label = final_label or ai_label or "other"
            
            images.append({
                'id': str(image_id),
                'room_label': room_label,
                'display_order': display_order or 0,
                'is_primary': is_primary or False,
                'upload_order': len(images) + 1  # Preserve relative upload order
            })
        
        return images


def _get_sequence_priority(room_label: str, upload_order: int) -> tuple[int, int]:
    """
    Get priority tuple for sorting.
    Lower numbers = higher priority.
    
    Returns:
        Tuple of (category_priority, upload_order)
    """
    # Find category priority
    try:
        category_priority = PHOTO_SEQUENCE_PRIORITY.index(room_label)
    except ValueError:
        category_priority = len(PHOTO_SEQUENCE_PRIORITY) - 1  # "other" is last
    
    # Within same category, preserve upload order
    return (category_priority, upload_order)


def identify_primary_image(listing_id: str) -> Optional[str]:
    """
    Identify the best front exterior image to set as primary.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        Image ID of best primary candidate, or None
    """
    images = _get_listing_images_with_labels(listing_id)
    
    # Find front exterior images
    front_exterior_images = [
        img for img in images
        if img['room_label'] == "front_exterior"
    ]
    
    if not front_exterior_images:
        return None
    
    # If one is already marked primary, use it
    for img in front_exterior_images:
        if img['is_primary']:
            return img['id']
    
    # Otherwise, use the first one (earliest upload)
    return front_exterior_images[0]['id']

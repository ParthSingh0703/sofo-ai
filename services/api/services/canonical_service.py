from uuid import UUID
from datetime import datetime
from typing import Optional

from services.api.database import get_db
from services.api.models.canonical import CanonicalListing
from services.api.services.user_service import get_or_create_test_user


def _format_room_type(room_type: Optional[str]) -> Optional[str]:
    """
    Convert snake_case room type to Title Case.
    Example: "front_exterior" -> "Front Exterior"
    
    Args:
        room_type: Room type in snake_case format
        
    Returns:
        Room type in Title Case format, or None if input is None/empty
    """
    if not room_type:
        return None
    
    return ' '.join(word.capitalize() for word in room_type.split('_'))


# -----------------------------
# CREATE LISTING + EMPTY CANONICAL
# -----------------------------
def create_listing_with_canonical(user_id: UUID) -> UUID:
    """
    Creates a new listing with an empty canonical payload.
    
    Validates that the user exists. In development/testing, creates a test user
    if it doesn't exist. In production, this should be handled by authentication.
    
    Args:
        user_id: The user ID creating the listing
        
    Returns:
        The created listing ID
        
    Raises:
        ValueError: If user validation fails
    """
    # Ensure user exists (will create test user in development if needed)
    validated_user_id = get_or_create_test_user(user_id)
    
    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO listings (created_by)
            VALUES (%s)
            RETURNING id
            """,
            (str(validated_user_id),)
        )
        listing_id = cur.fetchone()[0]

        empty_canonical = CanonicalListing()
        # Use model_dump_json() to properly serialize datetime objects
        canonical_json = empty_canonical.model_dump_json()

        cur.execute(
            """
            INSERT INTO canonical_listings (
                listing_id,
                schema_version,
                canonical_payload,
                mode,
                locked
            )
            VALUES (%s, %s, %s, 'draft', false)
            """,
            (
                str(listing_id),
                "1.0",
                canonical_json
            )
        )
        return listing_id


# -----------------------------
# GET CANONICAL
# -----------------------------
def get_canonical(listing_id: UUID) -> CanonicalListing | None:
    """
    Retrieves the canonical listing for a given listing ID.
    Populates media_images from database if needed.
    """
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT canonical_payload
            FROM canonical_listings
            WHERE listing_id = %s
            """,
            (str(listing_id),)
        )
        row = cur.fetchone()

        if not row:
            return None

        canonical = CanonicalListing(**row[0])
        
        # Populate media_images from database if needed
        # Get all images with their labels, descriptions, and room types
        cur.execute(
            """
            SELECT 
                li.id,
                li.ai_suggested_label,
                li.final_label,
                li.display_order,
                li.is_primary,
                ia.description,
                ia.detected_features
            FROM listing_images li
            LEFT JOIN image_ai_analysis ia ON li.id = ia.image_id
            WHERE li.listing_id = %s
            ORDER BY li.display_order, li.uploaded_at
            """,
            (str(listing_id),)
        )
        
        import json
        image_rows = cur.fetchall()
        image_dict = {}
        for row in image_rows:
            detected_features = row[6] if row[6] else {}
            # Extract room_label from detected_features (fallback to ai_suggested_label if not in detected_features)
            room_label = detected_features.get('room_label') if isinstance(detected_features, dict) else (json.loads(detected_features).get('room_label') if detected_features else None)
            if not room_label:
                room_label = row[1]  # Fallback to ai_suggested_label
            
            image_dict[str(row[0])] = {
                'ai_suggested_label': row[1],
                'final_label': row[2],
                'display_order': row[3],
                'is_primary': row[4],
                'description': row[5],
                'ai_suggested_room_type': room_label
            }
        
        # Update canonical media_images with database data
        if not canonical.media:
            from services.api.models.canonical import Media
            canonical.media = Media()
        
        # Update existing media_images or create new ones
        existing_image_ids = {img.image_id for img in canonical.media.media_images}
        
        for image_id, image_data in image_dict.items():
            if image_id in existing_image_ids:
                # Update existing - preserve user-edited values, update AI-suggested values
                for img in canonical.media.media_images:
                    if img.image_id == image_id:
                        # Update AI-suggested fields from database
                        img.ai_suggested_label = image_data['ai_suggested_label']
                        img.ai_suggested_description = image_data['description']
                        img.ai_suggested_room_type = image_data['ai_suggested_room_type']
                        
                        # Only update label/description/room_type if not already user-edited
                        # (preserve user edits from canonical)
                        if img.label is None and image_data['final_label']:
                            img.label = image_data['final_label']
                        if img.description is None and image_data['description']:
                            img.description = image_data['description']
                        if img.room_type is None and image_data['ai_suggested_room_type']:
                            img.room_type = _format_room_type(image_data['ai_suggested_room_type'])
                        
                        # Update display order and primary flag from database
                        img.display_order = image_data['display_order']
                        img.is_primary = image_data['is_primary']
                        break
            else:
                # Add new
                from services.api.models.canonical import ImageMedia
                canonical.media.media_images.append(ImageMedia(
                    image_id=image_id,
                    ai_suggested_label=image_data['ai_suggested_label'],
                    label=image_data['final_label'],
                    ai_suggested_description=image_data['description'],
                    description=image_data['description'],  # Use AI description as initial description
                    ai_suggested_room_type=image_data['ai_suggested_room_type'],
                    room_type=_format_room_type(image_data['ai_suggested_room_type']),  # Convert to Title Case
                    display_order=image_data['display_order'],
                    is_primary=image_data['is_primary']
                ))
        
        return canonical


# -----------------------------
# UPDATE CANONICAL (ONLY IF NOT LOCKED)
# -----------------------------
def update_canonical(
    listing_id: UUID,
    canonical: CanonicalListing
) -> CanonicalListing | None:
    """
    Updates the canonical listing if it's not locked.
    
    When the canonical is locked (validated), no updates are allowed,
    including image descriptions, labels, and room types. This ensures data integrity after validation.
    
    Returns None if the listing doesn't exist or is locked.
    """
    with get_db() as (conn, cur):
        # Check if canonical is locked first
        cur.execute(
            """
            SELECT locked
            FROM canonical_listings
            WHERE listing_id = %s
            """,
            (str(listing_id),)
        )
        row = cur.fetchone()
        
        if not row:
            return None
        
        if row[0]:  # locked = true
            return None  # Cannot update locked canonical (includes image descriptions, labels, and room types)
        
        canonical.updated_at = datetime.utcnow()

        try:
            # Serialize canonical to JSON (use mode='json' to ensure proper datetime serialization)
            canonical_json = canonical.model_dump_json()
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error serializing canonical to JSON: {error_trace}")
            raise ValueError(f"Failed to serialize canonical listing: {str(e)}")

        try:
            cur.execute(
                """
                UPDATE canonical_listings
                SET canonical_payload = %s,
                    updated_at = now()
                WHERE listing_id = %s
                  AND locked = false
                RETURNING canonical_payload
                """,
                (
                    canonical_json,
                    str(listing_id)
                )
            )
            
            # Sync image labels back to listing_images table and rename files
            if canonical.media and canonical.media.media_images:
                from services.api.services.image_rename_helper import rename_image_file
                
                for image_media in canonical.media.media_images:
                    if image_media.label is not None:  # Only update if label is explicitly set
                        # Check current final_label to see if it changed
                        cur.execute(
                            """
                            SELECT final_label FROM listing_images
                            WHERE id = %s AND listing_id = %s
                            """,
                            (image_media.image_id, str(listing_id))
                        )
                        current_row = cur.fetchone()
                        current_final_label = current_row[0] if current_row else None
                        
                        # Update final_label in database
                        cur.execute(
                            """
                            UPDATE listing_images
                            SET final_label = %s
                            WHERE id = %s AND listing_id = %s
                            """,
                            (image_media.label, image_media.image_id, str(listing_id))
                        )
                        
                        # Rename file if final_label changed
                        if current_final_label != image_media.label:
                            rename_image_file(image_media.image_id, image_media.label, str(listing_id))
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error updating canonical in database: {error_trace}")
            raise ValueError(f"Failed to update canonical in database: {str(e)}")

        row = cur.fetchone()

        if not row:
            # This could happen if the listing was locked between the check and the update
            # or if the listing_id doesn't exist
            print(f"Warning: UPDATE query returned no rows for listing_id: {listing_id}")
            return None

        try:
            return CanonicalListing(**row[0])
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error deserializing canonical from database: {error_trace}")
            raise ValueError(f"Failed to deserialize canonical listing: {str(e)}")

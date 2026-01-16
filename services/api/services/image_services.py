"""
Image upload and management services.
Handles image file validation, storage, and database operations.
"""
import os
import re
import uuid
import shutil
from uuid import UUID
from fastapi import UploadFile
from services.api.database import get_db
from services.api.services.file_validation import validate_image_file

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing common Windows duplicate suffixes.
    
    Examples:
        "image - Copy.jpg" -> "image.jpg"
        "photo - Copy (2).jpg" -> "photo.jpg"
    """
    if not filename:
        return filename
    
    # Remove Windows duplicate suffixes: " - Copy", " - Copy (2)", etc.
    # Pattern matches: " - Copy", " - Copy (2)", " - Copy (3)", etc.
    pattern = r'\s*-\s*Copy(?:\s*\(\d+\))?(?=\.[^.]+$|$)'
    sanitized = re.sub(pattern, '', filename, flags=re.IGNORECASE)
    return sanitized


async def save_image_file(listing_id: UUID, file: UploadFile) -> str:
    """
    Save a validated image file to disk and database.
    
    Args:
        listing_id: The listing ID to associate the image with
        file: The uploaded file (must be JPG, JPEG, or PNG)
        
    Returns:
        The image ID as a string
        
    Raises:
        HTTPException: If file validation fails
    """
    # 1) Validate file type and size
    validate_image_file(file)
    
    # 2) Sanitize filename and build local path
    sanitized_filename = sanitize_filename(file.filename)
    safe_name = f"{uuid.uuid4()}_{sanitized_filename}"
    rel_dir = os.path.join("images", str(listing_id))
    rel_path = os.path.join(rel_dir, safe_name)
    abs_dir = os.path.join(STORAGE_ROOT, rel_dir)
    abs_path = os.path.join(STORAGE_ROOT, rel_path)

    os.makedirs(abs_dir, exist_ok=True)

    # 3) Save file to disk
    with open(abs_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # 4) Insert DB row
    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO listing_images (listing_id, storage_path, original_filename)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (str(listing_id), rel_path, sanitized_filename),
        )
        image_id = cur.fetchone()[0]
        return str(image_id)


async def delete_image_file(listing_id: UUID, image_id: str) -> bool:
    """
    Delete an image file from disk and database.
    
    Args:
        listing_id: The listing ID (for validation)
        image_id: The image ID to delete
        
    Returns:
        True if deletion was successful, False otherwise
        
    Raises:
        HTTPException: If image not found or deletion fails
    """
    with get_db() as (conn, cur):
        # Get storage path before deletion
        cur.execute(
            """
            SELECT storage_path FROM listing_images
            WHERE id = %s AND listing_id = %s
            """,
            (image_id, str(listing_id))
        )
        row = cur.fetchone()
        
        if not row:
            return False
        
        storage_path = row[0]
        
        # Delete from database (CASCADE will handle image_ai_analysis)
        cur.execute(
            """
            DELETE FROM listing_images
            WHERE id = %s AND listing_id = %s
            """,
            (image_id, str(listing_id))
        )
        
        if cur.rowcount == 0:
            return False
        
        # Delete file from disk
        abs_path = os.path.join(STORAGE_ROOT, storage_path)
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception as e:
            print(f"Warning: Failed to delete file {abs_path}: {str(e)}")
            # Continue even if file deletion fails
        
        return True
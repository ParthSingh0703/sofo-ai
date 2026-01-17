"""
Image upload endpoints.
Handles image file uploads with validation.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from uuid import UUID
import os
from services.api.services.image_services import save_image_file, delete_image_file
from services.api.database import get_db

router = APIRouter(prefix="/images", tags=["Images"])

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")


@router.post("/listings/{listing_id}")
async def upload_image(listing_id: UUID, file: UploadFile = File(...)):
    """
    Upload an image file for a listing.
    
    Allowed image types: JPG, JPEG, PNG
    Maximum file size: 10 MB
    
    Args:
        listing_id: The listing ID to associate the image with
        file: The image file to upload
        
    Returns:
        Dictionary containing the image_id
        
    Raises:
        HTTPException: If validation fails or upload error occurs
    """
    try:
        image_id = await save_image_file(listing_id, file)
        return {"image_id": image_id}
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.delete("/listings/{listing_id}/{image_id}")
async def delete_image(listing_id: UUID, image_id: UUID):
    """
    Delete an image file for a listing.
    
    Args:
        listing_id: The listing ID
        image_id: The image ID to delete
        
    Returns:
        Dictionary with success status
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        success = await delete_image_file(listing_id, str(image_id))
        if not success:
            raise HTTPException(status_code=404, detail="Image not found")
        return {"success": True, "message": "Image deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {str(e)}")


@router.get("/listings/{listing_id}")
async def get_listing_images(listing_id: UUID):
    """
    Get all images for a listing with their analysis data.
    
    Returns:
        List of images with metadata, labels, and descriptions
    """
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT 
                li.id,
                li.original_filename,
                li.storage_path,
                li.ai_suggested_label,
                li.final_label,
                li.ai_suggested_order,
                li.display_order,
                li.is_primary,
                ia.description as ai_description,
                ia.detected_features
            FROM listing_images li
            LEFT JOIN image_ai_analysis ia ON li.id = ia.image_id
            WHERE li.listing_id = %s
            ORDER BY li.display_order, li.ai_suggested_order, li.uploaded_at
            """,
            (str(listing_id),)
        )
        rows = cur.fetchall()
        
        images = []
        for row in rows:
            images.append({
                "image_id": str(row[0]),
                "original_filename": row[1],
                "storage_path": row[2],
                "ai_suggested_label": row[3],
                "final_label": row[4],
                "ai_suggested_order": row[5],
                "display_order": row[6],
                "is_primary": row[7],
                "ai_description": row[8],
                "detected_features": row[9] if row[9] else {}
            })
        
        return {"images": images}


@router.get("/{listing_id}/{image_id}")
async def serve_image(listing_id: str, image_id: str):
    """
    Serve uploaded images by listing_id and image_id.
    """
    # Get image path from database
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT storage_path FROM listing_images
            WHERE listing_id = %s AND id = %s
            """,
            (listing_id, image_id)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Image not found")
        
        storage_path = row[0]
        file_path = os.path.join(STORAGE_ROOT, storage_path)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Image file not found")
        
        return FileResponse(file_path)


@router.post("/listings/{listing_id}/resequence")
async def resequence_images(listing_id: UUID):
    """
    Resequence images for a listing based on room type precedence.
    Uses existing room types/labels from the database - no AI needed.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        Dictionary with success status and sequence information
    """
    try:
        from services.api.services.enrichment_photo_sequencing import (
            generate_photo_sequence,
            identify_primary_image
        )
        from services.api.services.enrichment_service import _update_image_sequencing
        from services.api.services.image_rename_helper import sequence_and_rename_images
        
        # Generate sequence based on existing room types/labels
        sequence = generate_photo_sequence(str(listing_id))
        
        if not sequence:
            return {
                "success": True,
                "message": "No images to sequence",
                "sequence": []
            }
        
        # Identify primary image
        primary_id = identify_primary_image(str(listing_id))
        
        # Update database with sequencing and primary flag
        _update_image_sequencing(listing_id, sequence, primary_id)
        
        # Sequence and rename image files with sequence numbers
        sequence_and_rename_images(str(listing_id))
        
        return {
            "success": True,
            "message": f"Resequenced {len(sequence)} image(s)",
            "sequence": sequence,
            "primary_image": primary_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resequence images: {str(e)}"
        )

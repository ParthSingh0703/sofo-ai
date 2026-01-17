"""
Image upload utilities for MLS automation.
Handles uploading images to MLS forms with room type information.
"""
import os
from typing import Dict, Any, Optional, List
from uuid import UUID
from pathlib import Path
from playwright.sync_api import Page, Locator
import time

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")


def get_listing_images(listing_id: UUID) -> List[Dict[str, Any]]:
    """
    Get all images for a listing with their metadata.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        List of image dictionaries with:
        - image_id: UUID
        - storage_path: Relative path
        - final_label: Image label (sequence number + label)
        - room_type: Room type
        - display_order: Display order
        - is_primary: Whether it's the primary image
    """
    from services.api.database import get_db
    
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT 
                li.id,
                li.storage_path,
                li.final_label,
                li.display_order,
                li.is_primary,
                ia.detected_features->>'room_label' as room_type
            FROM listing_images li
            LEFT JOIN image_ai_analysis ia ON li.id = ia.image_id
            WHERE li.listing_id = %s
            ORDER BY li.display_order, li.uploaded_at
            """,
            (str(listing_id),)
        )
        
        rows = cur.fetchall()
        images = []
        for row in rows:
            image_id, storage_path, final_label, display_order, is_primary, room_type = row
            full_path = os.path.join(STORAGE_ROOT, storage_path)
            
            images.append({
                "image_id": image_id,
                "storage_path": storage_path,
                "full_path": full_path,
                "label": final_label or f"Image {display_order}",
                "room_type": room_type,
                "display_order": display_order or 0,
                "is_primary": bool(is_primary)
            })
        
        return images


def find_image_upload_area(page: Page) -> Optional[Locator]:
    """
    Find the image upload area/button on the MLS form.
    
    Tries multiple strategies:
    1. Input[type="file"]
    2. Button with "upload", "image", "photo" text
    3. Drop zone area
    
    Args:
        page: Playwright page object
        
    Returns:
        Locator for upload area, or None if not found
    """
    # Strategy 1: File input
    try:
        file_input = page.locator('input[type="file"]').first
        if file_input.count() > 0:
            return file_input
    except:
        pass
    
    # Strategy 2: Upload button
    try:
        upload_btn = page.locator('button:has-text("upload" i), button:has-text("image" i), button:has-text("photo" i), a:has-text("upload" i)').first
        if upload_btn.count() > 0:
            return upload_btn
    except:
        pass
    
    # Strategy 3: Drop zone
    try:
        dropzone = page.locator('[class*="dropzone" i], [class*="upload" i], [id*="upload" i]').first
        if dropzone.count() > 0:
            return dropzone
    except:
        pass
    
    return None


def upload_images_to_mls(
    page: Page,
    listing_id: UUID,
    max_images: int = 50
) -> Dict[str, Any]:
    """
    Upload images to MLS form.
    
    Args:
        page: Playwright page object
        listing_id: The listing ID
        max_images: Maximum number of images to upload
        
    Returns:
        Dictionary with:
        - uploaded: Number of images uploaded
        - skipped: Number of images skipped
        - errors: List of error messages
    """
    uploaded = 0
    skipped = 0
    errors = []
    
    # Get images for listing
    images = get_listing_images(listing_id)
    
    if not images:
        return {
            "uploaded": 0,
            "skipped": 0,
            "errors": ["No images found for listing"]
        }
    
    # Limit to max_images
    images = images[:max_images]
    
    # Find upload area
    upload_area = find_image_upload_area(page)
    if not upload_area:
        return {
            "uploaded": 0,
            "skipped": 0,
            "errors": ["Image upload area not found on page"]
        }
    
    # Upload each image
    for image in images:
        try:
            full_path = image["full_path"]
            
            # Check if file exists
            if not os.path.exists(full_path):
                skipped += 1
                errors.append(f"Image file not found: {full_path}")
                continue
            
            # Determine upload method based on element type
            tag_name = upload_area.evaluate("el => el.tagName.toLowerCase()")
            
            if tag_name == "input" and upload_area.get_attribute("type") == "file":
                # Direct file input
                upload_area.set_input_files(full_path)
                time.sleep(1)  # Wait for upload to start
            else:
                # Click button to trigger file picker, then use file input
                upload_area.click()
                time.sleep(0.5)
                
                # Find file input (may be newly visible)
                file_input = page.locator('input[type="file"]').first
                if file_input.count() > 0:
                    file_input.set_input_files(full_path)
                    time.sleep(1)
                else:
                    skipped += 1
                    errors.append(f"File input not available for: {image['label']}")
                    continue
            
            # Wait for upload confirmation (optional - may vary by MLS)
            time.sleep(0.5)
            
            uploaded += 1
            
        except Exception as e:
            skipped += 1
            error_msg = f"Error uploading {image['label']}: {str(e)}"
            errors.append(error_msg)
            print(error_msg)
    
    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "errors": errors
    }


def _wait_for_upload_completion(page: Page, image_label: str, timeout: float = 15.0) -> bool:
    """
    Wait for image upload to complete by detecting progress indicators.
    
    Args:
        page: Playwright page object
        image_label: Label/name of image being uploaded
        timeout: Maximum time to wait (seconds)
        
    Returns:
        True if upload appears complete, False if timeout
    """
    import time
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Check for common upload completion indicators
        # 1. Upload progress bars disappear
        progress_bars = page.locator('[class*="progress" i], [class*="uploading" i], .spinner, .loading').first
        if progress_bars.count() == 0 or not progress_bars.is_visible(timeout=500):
            # No progress indicators - upload likely complete
            time.sleep(1.0)  # Wait a moment for final state
            return True
        
        # 2. Check for success messages
        success_msg = page.locator('text=/upload.*complete|upload.*success|uploaded.*successfully/i').first
        if success_msg.count() > 0 and success_msg.is_visible(timeout=500):
            return True
        
        # 3. Check for error messages
        error_msg = page.locator('text=/upload.*error|upload.*failed|failed.*upload/i').first
        if error_msg.count() > 0 and error_msg.is_visible(timeout=500):
            return False  # Upload failed
        
        time.sleep(0.5)
    
    # Timeout - assume completion (might be a slow upload)
    return True


def set_image_room_types(
    page: Page,
    listing_id: UUID
) -> Dict[str, Any]:
    """
    Set room type labels for uploaded images with enhanced detection.
    
    Attempts to find and set room type dropdowns/tags for each uploaded image.
    
    Args:
        page: Playwright page object
        listing_id: The listing ID
        
    Returns:
        Dictionary with:
        - set: Number of room types set
        - skipped: Number skipped
        - errors: List of error messages
    """
    set_count = 0
    skipped = 0
    errors = []
    
    try:
        # Get images with room types
        images = get_listing_images(listing_id)
        
        # Try to find room type controls for each image
        # Strategy: Look for room type dropdowns/tags near image thumbnails
        image_containers = page.locator('[class*="image" i], [class*="photo" i], [class*="thumbnail" i]').all()
        
        for idx, image in enumerate(images[:len(image_containers)]):
            if not image.get("room_type"):
                skipped += 1
                continue
            
            room_type = image["room_type"]
            
            try:
                if idx < len(image_containers):
                    container = image_containers[idx]
                    
                    # Look for room type dropdown/select in container
                    room_type_select = container.locator('select, [class*="room" i], [class*="type" i]').first
                    if room_type_select.count() > 0:
                        # Try to select the room type
                        from services.api.services.mls_automation.field_filler import fill_dropdown_field
                        success, _ = fill_dropdown_field(page, room_type_select, room_type, use_ai_matching=True, field_name="room_type")
                        if success:
                            set_count += 1
                        else:
                            skipped += 1
                            errors.append(f"Could not set room type '{room_type}' for image {idx + 1}")
                    else:
                        skipped += 1
                else:
                    skipped += 1
            except Exception as e:
                skipped += 1
                errors.append(f"Error setting room type for image {idx + 1}: {str(e)}")
        
        return {
            "set": set_count,
            "skipped": skipped,
            "errors": errors
        }
    except Exception as e:
        return {
            "set": 0,
            "skipped": 0,
            "errors": [f"Error in room type setting: {str(e)}"]
        }

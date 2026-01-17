"""
Main enrichment service that orchestrates all enrichment tasks.
Supports parallel processing for improved performance.
"""
import os
import json
from typing import Literal, Optional, List, Dict, Any
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.api.services.enrichment_image_analysis import analyze_image_with_vision
from services.api.services.enrichment_photo_sequencing import (
    generate_photo_sequence,
    identify_primary_image
)
from services.api.services.enrichment_listing_descriptions import generate_listing_descriptions
from services.api.services.enrichment_geo_intelligence import enrich_geo_intelligence
from services.api.services.enrichment_property_description import generate_ai_property_description
from services.api.services.canonical_service import get_canonical, update_canonical
from services.api.database import get_db
from services.api.models.canonical import CanonicalListing

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")


def enrich_listing(
    listing_id: UUID,
    analyze_images: bool = True,
    generate_descriptions: bool = True,
    enrich_geo: bool = True
) -> Dict[str, Any]:
    """
    Main enrichment function that runs all enrichment tasks.
    
    Args:
        listing_id: The listing ID to enrich
        analyze_images: Whether to analyze and label images
        generate_descriptions: Whether to generate listing descriptions (AI determines tone automatically)
        enrich_geo: Whether to enrich with geo-intelligence data
        
    Returns:
        Dictionary with enrichment results
    """
    results = {
        "image_analysis": {},
        "photo_sequence": [],
        "primary_image": None,
        "descriptions": {},
        "geo_intelligence": {},
        "ai_property_description": {}
    }
    
    # Run independent tasks in parallel
    print(f"Starting enrichment for listing {listing_id}...")
    import time
    enrichment_start = time.time()
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit independent tasks
        image_future = None
        if analyze_images:
            image_future = executor.submit(_analyze_all_images, listing_id)
        
        geo_future = None
        if enrich_geo:
            geo_future = executor.submit(enrich_geo_intelligence, listing_id)
        
        # Wait for image analysis
        if image_future:
            image_results = image_future.result()
            results["image_analysis"] = image_results
            # Note: Photo sequencing is now done only on "Finalize Assets" button click
            # (via POST /images/listings/{listing_id}/resequence endpoint)
        
        # Get geo results (already running in parallel)
        if geo_future:
            geo_result = geo_future.result()
            results["geo_intelligence"] = geo_result
        
        # Generate descriptions (can run after image analysis completes)
        if generate_descriptions:
            canonical = get_canonical(listing_id)
            if canonical:
                descriptions = generate_listing_descriptions(canonical)
                results["descriptions"] = descriptions
                
                # Update canonical with descriptions
                canonical.remarks.public_remarks = descriptions.get("public_remarks")
                canonical.remarks.syndication_remarks = descriptions.get("syndication_remarks")
                update_canonical(listing_id, canonical)
        
        # AI property description (depends on geo for POIs)
        try:
            if geo_future:
                geo_future.result()  # Ensure geo is done
            ai_desc_result = generate_ai_property_description(listing_id)
            results["ai_property_description"] = ai_desc_result
        except Exception as e:
            results["ai_property_description"] = {
                "success": False,
                "error": str(e)
            }
    
    enrichment_elapsed = time.time() - enrichment_start
    print(f"✓ Completed enrichment in {enrichment_elapsed:.2f} seconds")
    
    return results


def _analyze_single_image(image: Dict[str, Any], listing_id: UUID) -> Optional[tuple[str, Dict[str, Any]]]:
    """
    Analyze a single image.
    Designed to be called in parallel.
    
    Args:
        image: Dictionary with 'id', 'storage_path', 'filename'
        listing_id: Listing ID for logging
        
    Returns:
        Tuple of (image_id, analysis_dict) or None if analysis fails
    """
    image_id = image['id']
    storage_path = image['storage_path']
    filename = image['filename']
    
    try:
        # Build full file path
        file_path = os.path.join(STORAGE_ROOT, storage_path)
        
        if not os.path.exists(file_path):
            print(f"Warning: Image file not found: {file_path}")
            return None
        
        # Analyze image
        analysis = analyze_image_with_vision(file_path, filename)
        
        # Store results in database
        _save_image_analysis(image_id, analysis)
        
        return (str(image_id), analysis)
    except Exception as e:
        print(f"Error analyzing image {image_id} ({filename}): {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def _analyze_all_images(listing_id: UUID) -> Dict[str, Dict[str, Any]]:
    """
    Analyze all images for a listing in parallel.
    Only analyzes images that haven't been analyzed yet.
    
    Returns:
        Dictionary mapping image_id -> analysis results
    """
    # Get only unanalyzed images
    images = _get_listing_images(listing_id, only_unanalyzed=True)
    
    if not images:
        print("All images already analyzed, skipping analysis.")
        return {}
    
    results = {}
    
    print(f"Analyzing {len(images)} image(s) in parallel...")
    import time
    start_time = time.time()
    
    # Process images in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_image = {
            executor.submit(_analyze_single_image, image, listing_id): image
            for image in images
        }
        
        for future in as_completed(future_to_image):
            image = future_to_image[future]
            image_id = image['id']
            filename = image['filename']
            
            try:
                result = future.result()
                if result:
                    img_id, analysis = result
                    results[img_id] = analysis
                    print(f"✓ Successfully analyzed image {image_id} ({filename})")
                else:
                    print(f"⚠ No analysis result for image {image_id} ({filename})")
            except Exception as e:
                print(f"✗ Error processing image analysis for {image_id} ({filename}): {str(e)}")
                continue
    
    elapsed_time = time.time() - start_time
    print(f"✓ Completed analysis of {len(images)} image(s) in {elapsed_time:.2f} seconds")
    
    return results


def _get_listing_images(listing_id: UUID, only_unanalyzed: bool = False) -> List[Dict[str, Any]]:
    """
    Get all images for a listing.
    
    Args:
        listing_id: The listing ID
        only_unanalyzed: If True, only return images that haven't been analyzed yet
    """
    with get_db() as (conn, cur):
        if only_unanalyzed:
            # Only get images that don't have analysis yet
            cur.execute(
                """
                SELECT li.id, li.storage_path, li.original_filename
                FROM listing_images li
                LEFT JOIN image_ai_analysis ia ON li.id = ia.image_id
                WHERE li.listing_id = %s AND ia.id IS NULL
                ORDER BY li.uploaded_at ASC
                """,
                (str(listing_id),)
            )
        else:
            # Get all images (existing behavior)
            cur.execute(
                """
                SELECT id, storage_path, original_filename
                FROM listing_images
                WHERE listing_id = %s
                ORDER BY uploaded_at ASC
                """,
                (str(listing_id),)
            )
        
        images = []
        for row in cur.fetchall():
            images.append({
                'id': row[0],
                'storage_path': row[1],
                'filename': row[2]
            })
        
        return images


def _save_image_analysis(image_id: str, analysis: Dict[str, Any]) -> None:
    """
    Save image analysis results to database and rename file based on label.
    """
    from services.api.services.image_rename_helper import rename_image_file
    
    with get_db() as (conn, cur):
        # Get listing_id for file renaming
        cur.execute(
            """
            SELECT listing_id FROM listing_images WHERE id = %s
            """,
            (image_id,)
        )
        listing_row = cur.fetchone()
        listing_id = str(listing_row[0]) if listing_row else None
        
        # Check current state before updating
        cur.execute(
            """
            SELECT ai_suggested_label, final_label FROM listing_images WHERE id = %s
            """,
            (image_id,)
        )
        current_row = cur.fetchone()
        current_ai_label = current_row[0] if current_row else None
        current_final_label = current_row[1] if current_row else None
        
        # Update listing_images table
        room_label = analysis.get("room_label")
        cur.execute(
            """
            UPDATE listing_images
            SET 
                ai_suggested_label = %s,
                is_primary = %s
            WHERE id = %s
            """,
            (
                room_label,
                analysis.get("is_primary_candidate", False),
                image_id
            )
        )
        
        # Note: File renaming with sequence numbers happens after all images are analyzed
        # in sequence_and_rename_images() called from enrich_listing()
        
        # Save to image_ai_analysis table
        # Store photo_type and other metadata in detected_features JSONB
        detected_features = {
            "photo_type": analysis.get("photo_type"),
            "room_label": analysis.get("room_label"),
            "is_primary_candidate": analysis.get("is_primary_candidate", False)
        }
        
        # Check if analysis already exists
        cur.execute(
            """
            SELECT id FROM image_ai_analysis WHERE image_id = %s
            """,
            (image_id,)
        )
        existing = cur.fetchone()
        
        if existing:
            # Update existing
            cur.execute(
                """
                UPDATE image_ai_analysis
                SET description = %s, detected_features = %s, model_version = %s
                WHERE image_id = %s
                """,
                (
                    analysis.get("description"),
                    json.dumps(detected_features),
                    os.getenv("IMAGE_VISION_MODEL", "gemini-2.5-flash"),
                    image_id
                )
            )
        else:
            # Insert new
            cur.execute(
                """
                INSERT INTO image_ai_analysis (image_id, description, detected_features, model_version)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    image_id,
                    analysis.get("description"),
                    json.dumps(detected_features),
                    os.getenv("VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
                )
            )


def _update_image_sequencing(
    listing_id: UUID,
    sequence: List[str],
    primary_image_id: Optional[str]
) -> None:
    """
    Update image sequencing and primary flag in database.
    """
    with get_db() as (conn, cur):
        # Clear existing primary flags
        cur.execute(
            """
            UPDATE listing_images
            SET is_primary = false
            WHERE listing_id = %s
            """,
            (str(listing_id),)
        )
        
        # Update sequence order and primary flag
        for order, image_id in enumerate(sequence, start=1):
            is_primary = (image_id == primary_image_id) if primary_image_id else False
            
            cur.execute(
                """
                UPDATE listing_images
                SET 
                    ai_suggested_order = %s,
                    display_order = %s,
                    is_primary = %s
                WHERE id = %s
                """,
                (order, order, is_primary, image_id)
            )

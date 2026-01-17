"""
Listing enrichment endpoints.
Handles AI-based enrichment of property listings.
"""
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import Literal, Optional
import psycopg2
from services.api.services.enrichment_service import enrich_listing

router = APIRouter(prefix="/enrichment", tags=["Enrichment"])


@router.post("/listings/{listing_id}/enrich")
async def enrich_listing_endpoint(
    listing_id: UUID,
    analyze_images: bool = Query(
        default=True,
        description="Whether to analyze and label images"
    ),
    generate_descriptions: bool = Query(
        default=True,
        description="Whether to generate listing descriptions"
    ),
    enrich_geo: bool = Query(
        default=True,
        description="Whether to enrich with geo-intelligence data (requires GOOGLE_MAPS_API_KEY)"
    )
):
    """
    Enrich a listing with AI-based analysis and descriptions.
    
    Tasks performed:
    1. Image-based photo labeling (room/portion identification)
    2. Image descriptions (1-2 sentences per image)
    3. Photo sequencing recommendations (MLS order)
    4. Listing descriptions (public_remarks, syndication_remarks) - AI determines appropriate tone
    5. Geo-intelligence enrichment (latitude/longitude, directions, nearby POIs, water body proximity)
    
    Args:
        listing_id: The listing ID to enrich
        analyze_images: Whether to analyze images
        generate_descriptions: Whether to generate text descriptions
        enrich_geo: Whether to enrich with geo-intelligence data
        
    Returns:
        Dictionary with enrichment results
    """
    try:
        results = enrich_listing(
            listing_id=listing_id,
            analyze_images=analyze_images,
            generate_descriptions=generate_descriptions,
            enrich_geo=enrich_geo
        )
        
        return {
            "listing_id": str(listing_id),
            "enrichment_complete": True,
            "results": results
        }
    
    except HTTPException:
        raise
    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Please ensure the database is running."
        )
    except ImportError as e:
        error_msg = str(e)
        if "google-genai" in error_msg or "google.genai" in error_msg:
            raise HTTPException(
                status_code=500,
                detail=f"Required library not installed: {error_msg}. Please install the required dependencies."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Missing dependency: {error_msg}"
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Resource not found: {str(e)}"
        )
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_trace = traceback.format_exc()
        print(f"Enrichment error: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Enrichment failed: {str(e)}"
        )


@router.get("/listings/{listing_id}/enrichment-status")
async def get_enrichment_status(listing_id: UUID):
    """
    Get current enrichment status for a listing.
    """
    try:
        from services.api.database import get_db
        
        with get_db() as (conn, cur):
            # Check image analysis status
            cur.execute(
                """
                SELECT COUNT(*) as total,
                       COUNT(ai_suggested_label) as labeled,
                       COUNT(CASE WHEN is_primary THEN 1 END) as primary_set
                FROM listing_images
                WHERE listing_id = %s
                """,
                (str(listing_id),)
            )
            img_stats = cur.fetchone()
            
            # Check if descriptions exist
            from services.api.services.canonical_service import get_canonical
            canonical = get_canonical(listing_id)
            has_descriptions = (
                canonical and
                canonical.remarks and
                (canonical.remarks.public_remarks or canonical.remarks.syndication_remarks)
            )
            
            return {
                "listing_id": str(listing_id),
                "images": {
                    "total": img_stats[0] if img_stats else 0,
                    "labeled": img_stats[1] if img_stats else 0,
                    "primary_set": img_stats[2] if img_stats else 0
                },
                "descriptions": {
                    "public_remarks": bool(has_descriptions),
                    "syndication_remarks": bool(has_descriptions)
                }
            }
    
    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Please ensure the database is running."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get enrichment status: {str(e)}"
        )

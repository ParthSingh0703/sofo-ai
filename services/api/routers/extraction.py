"""
Document extraction endpoints.
Handles extraction pipeline orchestration and method switching.
"""
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import Literal, Optional
import psycopg2
from services.api.services.extraction_pipeline import (
    extract_listing_from_documents,
    save_extraction_results
)
from services.api.models.extraction import ExtractionConfig
from services.api.services.canonical_service import update_canonical

router = APIRouter(prefix="/extraction", tags=["Extraction"])


@router.post("/listings/{listing_id}/extract")
async def extract_listing(listing_id: UUID):
    """
    Extract structured data from all uploaded documents for a listing using AI.
    
    Process:
    1. For each document:
       - Extract text → Gemini 2.5 Flash for structured extraction
       - Extract images (if PDF contains images) → Gemini 2.5 Flash for vision extraction
    2. Merge extracted fields into canonical listing
    3. Update canonical listing in database
    
    Args:
        listing_id: The listing ID to extract data for
        
    Returns:
        Dictionary with extraction results and canonical listing
    """
    try:
        # Create extraction config (no parameters needed - always AI-only)
        config = ExtractionConfig()
        
        # Run extraction pipeline
        canonical = extract_listing_from_documents(listing_id, config)
        
        # Update canonical in database (only if not locked)
        updated = update_canonical(listing_id, canonical)
        
        if not updated:
            raise HTTPException(
                status_code=400,
                detail="Cannot update canonical: listing is locked or does not exist"
            )
        
        # Serialize canonical to dict (use mode='json' for proper datetime serialization)
        try:
            canonical_dict = canonical.model_dump(mode='json')
        except Exception as e:
            # If model_dump fails, try with default mode and log the error
            import traceback
            print(f"Error serializing canonical: {traceback.format_exc()}")
            canonical_dict = canonical.model_dump()
        
        return {
            "listing_id": str(listing_id),
            "extraction_method": "ai",
            "canonical": canonical_dict,
            "message": "Extraction completed using AI (Gemini 2.5 Flash for all extraction tasks)"
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
        if "pdf2image" in error_msg or "google-genai" in error_msg or "google.genai" in error_msg:
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
            detail=f"Document file not found: {str(e)}"
        )
    except ValueError as e:
        # Catch Poppler installation errors, unsupported formats, and other value errors
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"ValueError during extraction: {error_trace}")
        
        if "Poppler" in error_msg or "poppler" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
        elif "not yet supported" in error_msg.lower() or "not applicable" in error_msg.lower() or "unsupported" in error_msg.lower():
            # Unsupported file format for vision extraction
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {error_msg}"
        )
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_trace = traceback.format_exc()
        print(f"Extraction error: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@router.get("/listings/{listing_id}/extraction-methods")
async def get_extraction_methods(listing_id: UUID):
    """
    Get current extraction configuration.
    All extraction is now AI-only.
    """
    return {
        "extraction_method": "ai",
        "models": {
            "text_extraction": "Gemini 2.5 Flash",
            "image_extraction": "Gemini 2.5 Flash"
        },
        "description": "All documents are processed using AI. Both text and images are extracted using Gemini 2.5 Flash."
    }

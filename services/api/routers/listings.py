from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
import psycopg2
from psycopg2 import pool

from services.api.services.canonical_service import (
    create_listing_with_canonical,
    get_canonical,
    update_canonical,
)
from services.api.services.validation_service import validate_canonical
from services.api.services.mapping.unlock_mls.service import prepare_mls_fields
from services.api.services.mls_mapping_service import save_mls_mapping, get_mls_mapping

from services.api.models.canonical import CanonicalListing

router = APIRouter(prefix="/listings", tags=["Listings"])


# -----------------------------
# CREATE LISTING + EMPTY CANONICAL
# -----------------------------
@router.post("")
def create_listing(user_id: UUID):
    try:
        listing_id = create_listing_with_canonical(user_id)
        return {
            "listing_id": listing_id,
            "status": "draft"
        }
    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Please ensure the database is running."
        )


# -----------------------------
# GET CANONICAL
# -----------------------------
@router.get("/{listing_id}/canonical", response_model=CanonicalListing)
def get_listing_canonical(listing_id: UUID):
    try:
        canonical = get_canonical(listing_id)
        if not canonical:
            raise HTTPException(status_code=404, detail="Canonical not found")
        return canonical
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except pool.PoolError as e:
        # Connection pool exhausted - retry after a short delay
        import time
        time.sleep(0.1)  # Brief delay before retry
        try:
            canonical = get_canonical(listing_id)
            if not canonical:
                raise HTTPException(status_code=404, detail="Canonical not found")
            return canonical
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="Database connection pool exhausted. Please try again in a moment."
            )
    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Please ensure the database is running."
        )


# -----------------------------
# UPDATE CANONICAL (DRAFT ONLY)
# -----------------------------
@router.put("/{listing_id}/canonical", response_model=CanonicalListing)
def update_listing_canonical(
    listing_id: UUID,
    canonical: CanonicalListing
):
    try:
        updated = update_canonical(listing_id, canonical)
        if not updated:
            raise HTTPException(
                status_code=400,
                detail="Canonical is locked or does not exist"
            )
        return updated
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Please ensure the database is running."
        )


# -----------------------------
# PREPARE MLS FIELDS
# -----------------------------
@router.get("/{listing_id}/mls-fields")
def get_mls_fields(listing_id: UUID, mls_system: str = Query(default="unlock_mls", description="MLS system code")):
    """
    Prepare canonical listing for MLS autofill and save to database.
    
    Args:
        listing_id: The listing ID
        mls_system: MLS system code (default: "unlock_mls")
    
    Returns:
        Dictionary with:
        - field_mappings: Field mapping configuration
        - transformed_fields: MLS-ready field values
        - validation: Validation results
        - ready_for_autofill: Boolean indicating readiness
        - saved: Boolean indicating if mapping was saved to database
    """
    try:
        canonical = get_canonical(listing_id)
        if not canonical:
            raise HTTPException(status_code=404, detail="Canonical not found")
        
        # Prepare MLS fields
        result = prepare_mls_fields(canonical)
        
        # Save to database
        saved = False
        try:
            saved = save_mls_mapping(listing_id, mls_system, result)
        except Exception as e:
            print(f"Warning: Failed to save MLS mapping to database: {str(e)}")
            # Continue even if save fails
        
        result["saved"] = saved
        return result
    
    except HTTPException:
        raise
    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Please ensure the database is running."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare MLS fields: {str(e)}"
        )


@router.get("/{listing_id}/mls-mapping/{mls_system}")
def get_stored_mls_fields(listing_id: UUID, mls_system: str):
    """
    Retrieve stored MLS field mappings from database.
    
    Args:
        listing_id: The listing ID
        mls_system: MLS system code (e.g., "unlock_mls")
    
    Returns:
        The stored MLS field mappings, or 404 if not found
    """
    try:
        stored_mapping = get_mls_mapping(listing_id, mls_system)
        
        if not stored_mapping:
            raise HTTPException(
                status_code=404,
                detail=f"MLS mapping not found for listing {listing_id} and system {mls_system}"
            )
        
        return stored_mapping
    
    except HTTPException:
        raise
    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Please ensure the database is running."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve MLS mapping: {str(e)}"
        )


# -----------------------------
# VALIDATE & LOCK CANONICAL
# -----------------------------
@router.post("/{listing_id}/validate")
def validate_listing(
    listing_id: UUID,
    user_id: UUID
):
    try:
        result = validate_canonical(listing_id, user_id)
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["errors"]
            )

        return {
            "status": "locked",
            "validated_at": result["validated_at"]
        }
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Please ensure the database is running."
        )

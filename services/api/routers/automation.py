"""
MLS Automation endpoints using Playwright.
Handles browser automation for MLS form autofill.
"""
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
import psycopg2

from services.api.services.mls_automation.automation_service import (
    prepare_automation_config,
    start_automation
)
from services.api.services.mls_automation.models import AutomationResult

router = APIRouter(prefix="/automation", tags=["Automation"])


@router.post("/listings/{listing_id}/start")
def start_mls_automation(
    listing_id: UUID,
    mls_system: str = Query(..., description="MLS system code (e.g., 'unlock_mls')"),
    mls_url: str = Query(None, description="MLS URL for new MLS discovery (optional)")
) -> AutomationResult:
    """
    Start Playwright automation to autofill MLS listing form.
    
    This endpoint should only be called after:
    1. Canonical listing is validated
    2. MLS mapping has been prepared (GET /listings/{listing_id}/mls-fields)
    3. User clicks "Start Automation" button
    
    Args:
        listing_id: The listing ID
        mls_system: MLS system code
        mls_url: Optional MLS URL for new MLS discovery
        
    Returns:
        AutomationResult with status and statistics
    """
    try:
        # Prepare automation config (validates canonical is validated and mapping exists)
        config = prepare_automation_config(listing_id, mls_system, mls_url)
        
        # Start automation
        result = start_automation(config)
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except psycopg2.OperationalError as e:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Please ensure the database is running."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start automation: {str(e)}"
        )

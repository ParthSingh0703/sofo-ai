"""
MLS Automation endpoints using Playwright.
Handles browser automation for MLS form autofill.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from uuid import UUID
import psycopg2
import os

from services.api.services.mls_automation.automation_service import (
    prepare_automation_config,
    start_automation,
    open_listing_site,
    is_session_active
)
from services.api.services.mls_automation.browser_session import close_session
from services.api.services.mls_automation.models import AutomationResult

router = APIRouter(prefix="/automation", tags=["Automation"])

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")


@router.post("/listings/{listing_id}/open-site")
async def open_site(
    listing_id: UUID,
    mls_system: str = Query(..., description="MLS system code (e.g., 'unlock_mls')"),
    mls_url: str = Query(None, description="MLS URL for new MLS discovery (optional)")
) -> dict:
    """
    Open MLS listing site in an embedded browser.
    User can navigate and login manually before starting automation.
    
    Args:
        listing_id: The listing ID
        mls_system: MLS system code
        mls_url: Optional MLS URL for new MLS discovery
        
    Returns:
        Dictionary with status and message
    """
    try:
        result = await open_listing_site(listing_id, mls_system, mls_url)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to open site: {str(e)}"
        )


@router.get("/listings/{listing_id}/session-status")
def get_session_status(listing_id: UUID) -> dict:
    """
    Check if a browser session is active for a listing.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        Dictionary with is_active boolean
    """
    return {"is_active": is_session_active(listing_id)}


@router.post("/listings/{listing_id}/close-session")
def close_browser_session(listing_id: UUID) -> dict:
    """
    Close the browser session for a listing.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        Dictionary with status
    """
    success = close_session(listing_id)
    if success:
        return {"status": "closed", "message": "Browser session closed"}
    else:
        return {"status": "not_found", "message": "No active session found"}


@router.post("/listings/{listing_id}/start")
async def start_mls_automation(
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
        result = await start_automation(config)
        
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


@router.get("/listings/{listing_id}/live-screenshot")
def get_live_screenshot(listing_id: UUID):
    """
    Get the latest live screenshot for an automation in progress.
    
    Args:
        listing_id: The listing ID
        
    Returns:
        FileResponse with screenshot image or 404 if not available
    """
    # Construct path to live screenshot
    live_screenshot_path = os.path.join(STORAGE_ROOT, "automation_screenshots", f"{listing_id}_live.png")
    
    if not os.path.exists(live_screenshot_path):
        raise HTTPException(status_code=404, detail="Live screenshot not available")
    
    return FileResponse(live_screenshot_path, media_type="image/png")


@router.get("/screenshots/{screenshot_path:path}")
def serve_screenshot(screenshot_path: str):
    """
    Serve automation screenshots.
    
    Args:
        screenshot_path: Relative path to screenshot from storage root
        
    Returns:
        FileResponse with screenshot image
    """
    # Construct full path
    file_path = os.path.join(STORAGE_ROOT, screenshot_path)
    
    # Security: Ensure path is within storage root
    if not os.path.abspath(file_path).startswith(os.path.abspath(STORAGE_ROOT)):
        raise HTTPException(status_code=403, detail="Invalid screenshot path")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Screenshot not found")
    
    return FileResponse(file_path, media_type="image/png")

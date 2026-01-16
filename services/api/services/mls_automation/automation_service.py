"""
Playwright automation service for MLS form autofill.

This service handles browser automation to autofill MLS listing forms
using mapped JSON data. It supports both known MLS systems (with stored
mappings) and new MLS systems (with dynamic discovery).
"""
import os
import json
import time
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    Page = None
    Browser = None
    BrowserContext = None
    PlaywrightTimeoutError = None

from services.api.database import get_db
from services.api.models.canonical import CanonicalListing
from services.api.services.canonical_service import get_canonical
from services.api.services.mls_mapping_service import get_mls_mapping
from services.api.services.mls_automation.models import (
    AutomationConfig,
    AutomationResult,
    MLSFieldSelector,
    MLSMappingConfig
)

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")
AUTOMATION_SCREENSHOTS_DIR = os.path.join(STORAGE_ROOT, "automation_screenshots")


def is_canonical_validated(listing_id: UUID) -> bool:
    """
    Check if canonical listing is validated (locked).
    
    Args:
        listing_id: The listing ID
        
    Returns:
        True if canonical is validated/locked, False otherwise
    """
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT locked
            FROM canonical_listings
            WHERE listing_id = %s
            """,
            (str(listing_id),)
        )
        row = cur.fetchone()
        return row[0] if row else False


def prepare_automation_config(
    listing_id: UUID,
    mls_system_code: str,
    mls_url: Optional[str] = None
) -> AutomationConfig:
    """
    Prepare automation configuration by checking if canonical is validated
    and loading mapped MLS JSON.
    
    Args:
        listing_id: The listing ID
        mls_system_code: MLS system code (e.g., "unlock_mls")
        mls_url: Optional MLS URL for new MLS discovery
        
    Returns:
        AutomationConfig with mapped JSON
        
    Raises:
        ValueError: If canonical is not validated or mapping not found
    """
    # Check if canonical is validated
    if not is_canonical_validated(listing_id):
        raise ValueError("Canonical must be validated before automation can start")
    
    # Get mapped MLS JSON from database
    stored_mapping = get_mls_mapping(listing_id, mls_system_code)
    if not stored_mapping:
        raise ValueError(f"MLS mapping not found for listing {listing_id} and system {mls_system_code}. Please prepare MLS fields first.")
    
    # Extract transformed fields from stored mapping
    mapped_json = stored_mapping.get("transformed_fields", {})
    
    return AutomationConfig(
        listing_id=listing_id,
        mls_system_code=mls_system_code,
        mls_url=mls_url,
        mapped_json=mapped_json,
        mode="SAVE_ONLY"
    )


def start_automation(config: AutomationConfig) -> AutomationResult:
    """
    Start Playwright automation to autofill MLS form.
    
    This function should be called after user clicks "Start Automation".
    It handles:
    1. Login detection and skipping
    2. MLS detection (known vs new)
    3. Field mapping and filling
    4. Enum handling
    5. Image upload
    6. Save (not submit)
    
    Args:
        config: Automation configuration
        
    Returns:
        AutomationResult with status and statistics
    """
    if not PLAYWRIGHT_AVAILABLE:
        return AutomationResult(
            status="failed",
            errors=["Playwright not installed. Please install with: pip install playwright && playwright install chromium"]
        )
    
    # Create screenshots directory
    os.makedirs(AUTOMATION_SCREENSHOTS_DIR, exist_ok=True)
    
    result = AutomationResult(
        status="failed",
        fields_filled=0,
        fields_skipped=0,
        images_updated=0
    )
    
    try:
        with sync_playwright() as p:
            # Launch browser in headed mode with slow-mo
            browser = p.chromium.launch(headless=False, slow_mo=500)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            try:
                # Navigate to MLS URL (if provided for new MLS) or use known MLS URL
                mls_url = config.mls_url or _get_mls_url(config.mls_system_code)
                if not mls_url:
                    result.errors.append("MLS URL not provided and not found in configuration")
                    return result
                
                page.goto(mls_url, wait_until="networkidle")
                time.sleep(2)  # Allow page to stabilize
                
                # Step 1: Login detection and skipping
                login_skipped = _detect_and_skip_login(page)
                result.login_skipped = login_skipped
                
                if not login_skipped:
                    # User needs to log in manually - wait for them
                    _wait_for_manual_login(page)
                    result.login_skipped = True
                
                # Step 2: MLS detection (known vs new)
                is_new_mls = config.mls_url is not None
                result.new_mls = is_new_mls
                
                # Step 3: Load or discover field mappings
                if is_new_mls:
                    field_mappings = _discover_mls_fields(page)
                    # Store discovered mappings for future use
                    if field_mappings:
                        _save_discovered_mappings(config.mls_system_code, page, field_mappings)
                else:
                    field_mappings = _load_mls_mappings(config.mls_system_code)
                
                # Step 4: Fill fields
                fill_result = _fill_mls_fields(page, config.mapped_json, field_mappings, config.mls_system_code)
                result.fields_filled = fill_result["filled"]
                result.fields_skipped = fill_result["skipped"]
                result.errors.extend(fill_result.get("errors", []))
                result.warnings.extend(fill_result.get("warnings", []))
                
                # Step 5: Upload images (after fields)
                image_result = _upload_mls_images(page, config.listing_id, config.mls_system_code)
                result.images_updated = image_result["uploaded"]
                result.errors.extend(image_result.get("errors", []))
                
                # Step 6: Save (not submit)
                save_success = _save_mls_listing(page, config.mls_system_code)
                if save_success:
                    result.status = "saved"
                else:
                    result.status = "failed"
                    result.errors.append("Failed to save MLS listing")
                
                # Take final screenshot
                screenshot_path = _take_screenshot(page, config.listing_id, "final")
                result.screenshot_paths.append(screenshot_path)
                
            except Exception as e:
                result.status = "failed"
                result.errors.append(f"Automation error: {str(e)}")
                # Take error screenshot
                try:
                    screenshot_path = _take_screenshot(page, config.listing_id, "error")
                    result.screenshot_paths.append(screenshot_path)
                except:
                    pass
                raise
            finally:
                browser.close()
    
    except Exception as e:
        result.status = "failed"
        result.errors.append(f"Failed to start automation: {str(e)}")
    
    result.completed_at = datetime.utcnow()
    return result


def _get_mls_url(mls_system_code: str) -> Optional[str]:
    """
    Get MLS URL for known MLS system.
    
    Args:
        mls_system_code: MLS system code
        
    Returns:
        MLS URL or None if not found
    """
    # TODO: Store MLS URLs in database or config
    known_urls = {
        "unlock_mls": "https://unlockmls.com"  # Placeholder
    }
    return known_urls.get(mls_system_code)


def _detect_and_skip_login(page: Page) -> bool:
    """
    Detect if user is already logged in using enhanced detection.
    
    Args:
        page: Playwright page object
        
    Returns:
        True if logged in, False otherwise
    """
    from services.api.services.mls_automation.login_handler import detect_login_state
    return detect_login_state(page, timeout=5.0)


def _wait_for_manual_login(page: Page, timeout: int = 300) -> None:
    """
    Wait for user to manually log in with enhanced monitoring.
    
    Args:
        page: Playwright page object
        timeout: Timeout in seconds (default 5 minutes)
    """
    from services.api.services.mls_automation.login_handler import wait_for_manual_login
    wait_for_manual_login(page, timeout=timeout)


def _discover_mls_fields(page: Page) -> List[MLSFieldSelector]:
    """
    Discover field mappings for new MLS system.
    
    Uses AI vision to detect form fields and map them to canonical JSON keys.
    
    Args:
        page: Playwright page object
        
    Returns:
        List of discovered field selectors
    """
    from services.api.services.mls_automation.field_discovery import discover_fields_from_page
    
    return discover_fields_from_page(page)


def _save_discovered_mappings(
    mls_system_code: str,
    page: Page,
    field_selectors: List[MLSFieldSelector]
) -> bool:
    """
    Save discovered field mappings for future use.
    
    Args:
        mls_system_code: MLS system code
        page: Playwright page object (for page structure)
        field_selectors: Discovered field selectors
        
    Returns:
        True if successful
    """
    from services.api.services.mls_automation.learning_service import save_mls_mapping_config
    
    # Extract page structure (save button, sections, etc.)
    page_structure = {
        "save_button": _find_save_button_selector(page),
        "upload_area": _find_upload_area_selector(page),
        # Could add more structure elements as needed
    }
    
    # Save with empty enum mappings (will be learned over time)
    return save_mls_mapping_config(
        mls_system_code=mls_system_code,
        field_selectors=field_selectors,
        page_structure=page_structure,
        enum_mappings={}
    )


def _find_save_button_selector(page: Page) -> Optional[str]:
    """Find save button selector for page structure."""
    try:
        save_button = page.locator('button:has-text("Save"), button:has-text("Save Draft")').first
        if save_button.count() > 0:
            # Try to get id or name
            button_id = save_button.get_attribute("id")
            if button_id:
                return f"#{button_id}"
            button_name = save_button.get_attribute("name")
            if button_name:
                return f"[name='{button_name}']"
            return "button:has-text('Save'), button:has-text('Save Draft')"
    except:
        pass
    return None


def _find_upload_area_selector(page: Page) -> Optional[str]:
    """Find upload area selector for page structure."""
    try:
        upload_area = page.locator('input[type="file"]').first
        if upload_area.count() > 0:
            upload_id = upload_area.get_attribute("id")
            if upload_id:
                return f"#{upload_id}"
            upload_name = upload_area.get_attribute("name")
            if upload_name:
                return f"[name='{upload_name}']"
            return "input[type='file']"
    except:
        pass
    return None


def _load_mls_mappings(mls_system_code: str) -> List[MLSFieldSelector]:
    """
    Load stored field mappings for known MLS system.
    
    Args:
        mls_system_code: MLS system code
        
    Returns:
        List of field selectors
    """
    # TODO: Load from database or config file
    return []


def _fill_mls_fields(
    page: Page,
    mapped_json: Dict[str, Any],
    field_mappings: List[MLSFieldSelector],
    mls_system_code: str
) -> Dict[str, Any]:
    """
    Fill MLS form fields using mapped JSON.
    
    Args:
        page: Playwright page object
        mapped_json: Mapped MLS JSON data (transformed_fields from mapping)
        field_mappings: Field selector mappings (optional, uses label-based if empty)
        mls_system_code: MLS system code for learning enum mappings
        
    Returns:
        Dictionary with filled/skipped counts and errors
    """
    from services.api.services.mls_automation.field_filler import (
        find_field_by_label,
        fill_text_field,
        fill_number_field,
        fill_dropdown_field,
        fill_checkbox_field,
        fill_radio_field,
        fill_date_field
    )
    
    filled = 0
    skipped = 0
    errors = []
    warnings = []
    
    # Extract transformed_fields if mapped_json contains nested structure
    if "transformed_fields" in mapped_json:
        fields_to_fill = mapped_json["transformed_fields"]
    else:
        fields_to_fill = mapped_json
    
    # Create mapping dictionary from field_mappings for quick lookup
    selector_map = {mapping.json_key: mapping for mapping in field_mappings}
    
    # Fill each field
    for field_name, field_value in fields_to_fill.items():
        if field_value is None or field_value == "":
            skipped += 1
            continue
        
        try:
            # Get field mapping if available
            mapping = selector_map.get(field_name)
            
            # Determine field type
            field_type = _infer_field_type(field_value, mapping)
            
            # Find field on page
            if mapping and mapping.selector:
                # Use stored selector
                try:
                    field_locator = page.locator(mapping.selector).first
                    if field_locator.count() == 0:
                        raise ValueError(f"Selector not found: {mapping.selector}")
                except:
                    # Fallback to label-based if selector fails
                    field_locator = find_field_by_label(page, field_name, field_type)
            else:
                # Use label-based discovery
                field_locator = find_field_by_label(page, field_name, field_type)
            
            if not field_locator or field_locator.count() == 0:
                skipped += 1
                warnings.append(f"Field not found: {field_name}")
                continue
            
            # Fill field based on type
            success = False
            if field_type == "text":
                success = fill_text_field(field_locator, field_value)
            elif field_type == "number":
                success = fill_number_field(field_locator, field_value)
            elif field_type == "dropdown" or field_type == "select":
                # Use AI matching for enums to handle semantic variations
                success, _ = fill_dropdown_field(page, field_locator, field_value, use_ai_matching=True, field_name=field_name)
            elif field_type == "checkbox":
                success = fill_checkbox_field(field_locator, field_value)
            elif field_type == "radio":
                # Radio buttons need name attribute
                field_name_attr = mapping.field_name if mapping else field_name
                success = fill_radio_field(page, field_name_attr, field_value)
            elif field_type == "date":
                success = fill_date_field(field_locator, field_value)
            else:
                # Default to text
                success = fill_text_field(field_locator, field_value)
            
            if success:
                filled += 1
            else:
                skipped += 1
                warnings.append(f"Failed to fill field: {field_name}")
                
        except Exception as e:
            skipped += 1
            error_msg = f"Error filling {field_name}: {str(e)}"
            errors.append(error_msg)
            print(error_msg)
    
    return {
        "filled": filled,
        "skipped": skipped,
        "errors": errors,
        "warnings": warnings
    }


def _infer_field_type(value: Any, mapping: Optional[MLSFieldSelector] = None) -> str:
    """
    Infer field type from value and mapping.
    
    Args:
        value: Field value
        mapping: Optional field mapping
        
    Returns:
        Field type string
    """
    if mapping and mapping.field_type:
        return mapping.field_type
    
    # Infer from value type
    if isinstance(value, bool):
        return "checkbox"
    elif isinstance(value, (int, float)):
        return "number"
    elif isinstance(value, list):
        return "dropdown"  # Multi-select
    elif isinstance(value, str):
        # Check if it looks like a date
        if "/" in value or "-" in value:
            try:
                from datetime import datetime
                datetime.strptime(value.split()[0], "%Y-%m-%d")
                return "date"
            except:
                pass
        return "text"
    
    return "text"  # Default


def _upload_mls_images(
    page: Page,
    listing_id: UUID,
    mls_system_code: str
) -> Dict[str, Any]:
    """
    Upload images to MLS listing after fields are filled.
    
    Args:
        page: Playwright page object
        listing_id: Listing ID
        mls_system_code: MLS system code
        
    Returns:
        Dictionary with upload results
    """
    from services.api.services.mls_automation.image_uploader import upload_images_to_mls, set_image_room_types
    
    # Upload images
    upload_result = upload_images_to_mls(page, listing_id)
    
    # Try to set room types (may not be supported by all MLS systems)
    try:
        room_type_result = set_image_room_types(page, listing_id)
        upload_result["room_types_set"] = room_type_result.get("set", 0)
    except:
        upload_result["room_types_set"] = 0
    
    return upload_result


def _save_mls_listing(page: Page, mls_system_code: str) -> bool:
    """
    Save MLS listing (never submit) with enhanced detection and validation.
    
    Args:
        page: Playwright page object
        mls_system_code: MLS system code
        
    Returns:
        True if save successful, False otherwise
    """
    from services.api.services.mls_automation.save_handler import save_mls_listing
    result = save_mls_listing(page, mls_system_code, timeout=30.0)
    return result.get("success", False)


def _take_screenshot(page: Page, listing_id: UUID, suffix: str) -> str:
    """
    Take screenshot and save to storage.
    
    Args:
        page: Playwright page object
        listing_id: Listing ID
        suffix: Suffix for filename (e.g., "final", "error")
        
    Returns:
        Relative path to screenshot
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{listing_id}_{suffix}_{timestamp}.png"
    rel_path = os.path.join("automation_screenshots", filename)
    abs_path = os.path.join(STORAGE_ROOT, rel_path)
    
    page.screenshot(path=abs_path)
    return rel_path

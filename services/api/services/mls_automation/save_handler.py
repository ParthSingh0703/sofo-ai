"""
Enhanced save detection and handling for MLS automation.
Supports multiple save strategies and robust success validation.
"""
import time
from typing import Optional, Dict, Any, List
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError


def find_and_click_save_button(page: Page, timeout: float = 10.0) -> bool:
    """
    Find and click save button using multiple strategies.
    
    Explicitly avoids Submit/Publish/Activate buttons.
    
    Args:
        page: Playwright page object
        timeout: Maximum time to wait for button (seconds)
        
    Returns:
        True if button found and clicked, False otherwise
    """
    save_patterns = [
        'button:has-text("Save"):not(:has-text("Submit"))',
        'button:has-text("Save Draft")',
        'button:has-text("Save Changes")',
        'button[type="submit"]:has-text("Save")',
        '[role="button"]:has-text("Save"):not(:has-text("Submit"))',
        'a:has-text("Save"):not(:has-text("Submit"))',
        'button[id*="save" i]:not([id*="submit" i])',
        'button[class*="save" i]:not([class*="submit" i])'
    ]
    
    # Exclude patterns that indicate submission
    exclude_patterns = [
        'button:has-text("Submit")',
        'button:has-text("Publish")',
        'button:has-text("Activate")',
        'button:has-text("Post")',
        'button[class*="submit" i]',
        'button[class*="publish" i]'
    ]
    
    for pattern in save_patterns:
        try:
            save_button = page.locator(pattern).first
            
            if save_button.count() > 0:
                # Check if visible and enabled
                if not save_button.is_visible(timeout=timeout * 1000):
                    continue
                
                if not save_button.is_enabled(timeout=timeout * 1000):
                    continue
                
                # Verify it's not in exclude list
                is_excluded = False
                for exclude_pattern in exclude_patterns:
                    excluded = page.locator(exclude_pattern).first
                    if excluded.count() > 0:
                        # Check if they're the same element
                        try:
                            save_bbox = save_button.bounding_box()
                            excluded_bbox = excluded.bounding_box()
                            if (save_bbox and excluded_bbox and
                                save_bbox['x'] == excluded_bbox['x'] and
                                save_bbox['y'] == excluded_bbox['y']):
                                is_excluded = True
                                break
                        except:
                            pass
                
                if is_excluded:
                    continue
                
                # Scroll into view if needed
                save_button.scroll_into_view_if_needed()
                time.sleep(0.3)
                
                # Click the button
                save_button.click(timeout=timeout * 1000)
                return True
        except Exception as e:
            continue
    
    return False


def wait_for_save_success(
    page: Page,
    timeout: float = 15.0,
    original_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Wait for save operation to complete and validate success.
    
    Checks multiple success indicators:
    1. Success messages/notifications
    2. URL changes (save redirect)
    3. Form state changes
    4. Error messages (validation failures)
    
    Args:
        page: Playwright page object
        timeout: Maximum time to wait (seconds)
        original_url: Original page URL before save
        
    Returns:
        Dictionary with:
        - success: bool
        - message: str (success/error message if found)
        - errors: List[str] (validation errors if any)
    """
    start_time = time.time()
    result = {
        "success": False,
        "message": "",
        "errors": []
    }
    
    # Wait a moment for UI to update
    time.sleep(1.0)
    
    while time.time() - start_time < timeout:
        # Check for success messages
        success_message = _check_success_messages(page)
        if success_message:
            result["success"] = True
            result["message"] = success_message
            return result
        
        # Check for error messages
        error_message = _check_error_messages(page)
        if error_message:
            result["errors"].append(error_message)
            # Continue checking - might be transient
        
        # Check for validation errors
        validation_errors = _check_validation_errors(page)
        if validation_errors:
            result["errors"].extend(validation_errors)
            # Continue checking - might be transient
        
        # Check URL change (if save redirects)
        if original_url:
            current_url = page.url
            if current_url != original_url and not current_url.endswith('#'):
                # URL changed - likely saved
                result["success"] = True
                result["message"] = "Save successful (redirect detected)"
                return result
        
        # Check for form state changes (disabled save button = processing)
        # If save button becomes enabled again, might indicate completion
        
        time.sleep(0.5)
    
    # Timeout - check final state
    if result["errors"]:
        result["success"] = False
        result["message"] = "Save completed with errors"
    elif result["message"]:
        # We have a message but no explicit success
        result["success"] = True
    else:
        result["message"] = "Save status unclear (timeout)"
    
    return result


def _check_success_messages(page: Page) -> Optional[str]:
    """Check for success notification messages."""
    try:
        success_patterns = [
            'text=/successfully.*saved|saved.*successfully/i',
            'text=/save.*successful|successful.*save/i',
            '[class*="success" i]:has-text("saved")',
            '[class*="alert-success" i]',
            '[role="alert"]:has-text("saved")',
            '.toast-success',
            '[id*="success" i]:has-text("saved")'
        ]
        
        for pattern in success_patterns:
            try:
                locator = page.locator(pattern).first
                if locator.count() > 0 and locator.is_visible(timeout=1000):
                    return locator.inner_text().strip()
            except:
                continue
        return None
    except:
        return None


def _check_error_messages(page: Page) -> Optional[str]:
    """Check for error notification messages."""
    try:
        error_patterns = [
            '[class*="error" i]',
            '[class*="alert-danger" i]',
            '[class*="alert-error" i]',
            '[role="alert"]:has-text("error")',
            '.toast-error',
            '[id*="error" i]',
            'text=/error.*occurred|failed.*save/i'
        ]
        
        for pattern in error_patterns:
            try:
                locator = page.locator(pattern).first
                if locator.count() > 0 and locator.is_visible(timeout=1000):
                    text = locator.inner_text().strip()
                    if text and len(text) < 500:  # Reasonable error message length
                        return text
            except:
                continue
        return None
    except:
        return None


def _check_validation_errors(page: Page) -> List[str]:
    """Check for form validation errors."""
    errors = []
    try:
        validation_patterns = [
            '[class*="invalid" i]',
            '[class*="validation-error" i]',
            '[class*="field-error" i]',
            '[aria-invalid="true"]',
            '.error-message',
            '[role="alert"]:near(input)'
        ]
        
        for pattern in validation_patterns:
            try:
                locators = page.locator(pattern).all()
                for locator in locators[:10]:  # Limit to 10 errors
                    if locator.is_visible(timeout=500):
                        text = locator.inner_text().strip()
                        if text and text not in errors:
                            errors.append(text)
            except:
                continue
        return errors
    except:
        return []


def save_mls_listing(page: Page, mls_system_code: str, timeout: float = 30.0) -> Dict[str, Any]:
    """
    Complete save operation with validation.
    
    Args:
        page: Playwright page object
        mls_system_code: MLS system code (for logging)
        timeout: Maximum time to wait (seconds)
        
    Returns:
        Dictionary with success status and details
    """
    original_url = page.url
    
    # Find and click save button
    button_clicked = find_and_click_save_button(page, timeout=10.0)
    
    if not button_clicked:
        return {
            "success": False,
            "message": "Save button not found or not clickable",
            "errors": []
        }
    
    # Wait for save to complete
    result = wait_for_save_success(page, timeout=timeout - 10.0, original_url=original_url)
    
    return result

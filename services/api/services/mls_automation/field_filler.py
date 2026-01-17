"""
Field filling utilities for MLS automation.
Handles finding and filling form fields using label-based discovery.
"""
from typing import Dict, Any, Optional, List, Tuple
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError
import time


def find_field_by_label(page: Page, label_text: str, field_type: Optional[str] = None) -> Optional[Locator]:
    """
    Find a form field by its label text.
    
    Supports various field label patterns:
    - <label for="field_id">Label</label> with <input id="field_id">
    - <label>Label <input></label>
    - Input with placeholder matching label
    - Input near label text
    
    Args:
        page: Playwright page object
        label_text: Label text to search for (case-insensitive partial match)
        field_type: Optional field type filter ("text", "number", "select", "checkbox", "radio")
        
    Returns:
        Locator for the field, or None if not found
    """
    label_lower = label_text.lower().strip()
    
    # Try multiple strategies
    strategies = [
        # Strategy 1: Label with "for" attribute
        lambda: _find_by_label_for(page, label_text),
        # Strategy 2: Label wrapping input
        lambda: _find_by_label_wrap(page, label_text),
        # Strategy 3: Input with aria-label
        lambda: _find_by_aria_label(page, label_text),
        # Strategy 4: Input with placeholder
        lambda: _find_by_placeholder(page, label_text),
        # Strategy 5: Input near label text (using XPath or proximity)
        lambda: _find_by_proximity(page, label_text, field_type),
    ]
    
    for strategy in strategies:
        try:
            locator = strategy()
            if locator and locator.count() > 0:
                return locator.first
        except:
            continue
    
    return None


def _find_by_label_for(page: Page, label_text: str) -> Optional[Locator]:
    """Find field using label's 'for' attribute."""
    try:
        label = page.locator(f'label:has-text("{label_text}")').first
        if label.count() > 0:
            for_attr = label.get_attribute("for")
            if for_attr:
                return page.locator(f'#{for_attr}, [name="{for_attr}"]')
    except:
        pass
    return None


def _find_by_label_wrap(page: Page, label_text: str) -> Optional[Locator]:
    """Find field wrapped inside label."""
    try:
        return page.locator(f'label:has-text("{label_text}") input, label:has-text("{label_text}") select, label:has-text("{label_text}") textarea')
    except:
        return None


def _find_by_aria_label(page: Page, label_text: str) -> Optional[Locator]:
    """Find field using aria-label attribute."""
    try:
        label_lower = label_text.lower()
        return page.locator(f'[aria-label*="{label_lower}" i], [aria-labelledby*="{label_lower}" i]')
    except:
        return None


def _find_by_placeholder(page: Page, label_text: str) -> Optional[Locator]:
    """Find field using placeholder attribute."""
    try:
        label_lower = label_text.lower()
        return page.locator(f'input[placeholder*="{label_lower}" i], textarea[placeholder*="{label_lower}" i]')
    except:
        return None


def _find_by_proximity(page: Page, label_text: str, field_type: Optional[str] = None) -> Optional[Locator]:
    """Find field by proximity to label text (XPath strategy)."""
    try:
        # Build XPath to find input/select/textarea near label text
        field_tags = ["input", "select", "textarea"]
        if field_type == "select":
            field_tags = ["select"]
        elif field_type in ["checkbox", "radio"]:
            field_tags = ['input[@type="checkbox"]', 'input[@type="radio"]']
        
        xpath = f'//label[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{label_text.lower()}")]/following-sibling::*[1][self::{"] or self::".join(field_tags)}]'
        
        # Try XPath
        locator = page.locator(f'xpath={xpath}')
        if locator.count() > 0:
            return locator
        
        # Fallback: Find any input/select near label
        label_lower = label_text.lower()
        return page.locator(f'label:has-text("{label_lower}"):near(input, select, textarea)')
    except:
        return None


def fill_text_field(locator: Locator, value: Any, retries: int = 2) -> bool:
    """
    Fill a text input field with enhanced error handling and retry logic.
    
    Args:
        locator: Locator for the field
        value: Value to fill (will be converted to string)
        retries: Number of retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    if value is None:
        return False
    
    value_str = str(value).strip()
    if not value_str:
        return False
    
    for attempt in range(retries + 1):
        try:
            # Wait for field to be visible and enabled
            locator.wait_for(state="visible", timeout=5000)
            if not locator.is_enabled():
                if attempt < retries:
                    time.sleep(0.5)
                    continue
                return False
            
            # Scroll into view if needed
            locator.scroll_into_view_if_needed()
            time.sleep(0.1)
            
            # Clear and fill
            locator.clear()
            time.sleep(0.1)
            locator.fill(value_str)
            time.sleep(0.2)  # Allow UI to update
            
            # Verify the value was set (optional check)
            try:
                current_value = locator.input_value()
                if current_value == value_str or str(current_value).strip() == value_str:
                    return True
            except:
                # If verification fails, assume success (some fields don't support input_value)
                return True
            
            return True
        except Exception as e:
            if attempt < retries:
                time.sleep(0.5)
                continue
            print(f"Error filling text field after {retries + 1} attempts: {str(e)}")
            return False
    
    return False


def fill_number_field(locator: Locator, value: Any, retries: int = 2) -> bool:
    """
    Fill a number input field with enhanced error handling and retry logic.
    
    Args:
        locator: Locator for the field
        value: Numeric value
        retries: Number of retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    if value is None:
        return False
    
    # Convert to number string (remove decimals if integer)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    
    value_str = str(value).strip()
    
    for attempt in range(retries + 1):
        try:
            # Wait for field to be visible and enabled
            locator.wait_for(state="visible", timeout=5000)
            if not locator.is_enabled():
                if attempt < retries:
                    time.sleep(0.5)
                    continue
                return False
            
            # Scroll into view if needed
            locator.scroll_into_view_if_needed()
            time.sleep(0.1)
            
            # Clear and fill
            locator.clear()
            time.sleep(0.1)
            locator.fill(value_str)
            time.sleep(0.2)
            
            return True
        except Exception as e:
            if attempt < retries:
                time.sleep(0.5)
                continue
            print(f"Error filling number field after {retries + 1} attempts: {str(e)}")
            return False
    
    return False


def fill_dropdown_field(
    page: Page,
    locator: Locator,
    value: Any,
    use_ai_matching: bool = False,
    field_name: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Fill a dropdown/select field.
    
    Tries exact match first, then normalized match, then AI semantic matching if enabled.
    
    Args:
        page: Playwright page object
        locator: Locator for the select element
        value: Value to select (can be string or list for multi-select)
        use_ai_matching: Whether to use AI for semantic matching
        field_name: Optional field name for AI context
        
    Returns:
        Tuple of (success, selected_value)
    """
    try:
        if value is None:
            return False, None
        
        # Handle multi-select
        is_multiple = locator.get_attribute("multiple") is not None
        values = value if isinstance(value, list) else [value]
        
        # Get available options
        options = locator.locator("option").all()
        option_texts = [opt.inner_text().strip() for opt in options]
        option_values = [opt.get_attribute("value") or opt.inner_text().strip() for opt in options]
        
        # Filter out empty options
        valid_indices = [i for i, (text, val) in enumerate(zip(option_texts, option_values)) if text and text.strip()]
        option_texts = [option_texts[i] for i in valid_indices]
        option_values = [option_values[i] for i in valid_indices]
        
        selected_values = []
        
        for target_value in values:
            target_str = str(target_value).strip()
            
            # Try exact match
            match_found = False
            for i, (opt_text, opt_value) in enumerate(zip(option_texts, option_values)):
                if opt_text.lower() == target_str.lower() or opt_value.lower() == target_str.lower():
                    if is_multiple:
                        locator.select_option(option=[opt_value])
                    else:
                        locator.select_option(value=opt_value)
                    selected_values.append(opt_value)
                    match_found = True
                    break
            
            if not match_found:
                # Try normalized match (remove special chars, lowercase)
                normalized_target = _normalize_string(target_str)
                for i, (opt_text, opt_value) in enumerate(zip(option_texts, option_values)):
                    normalized_opt = _normalize_string(opt_text)
                    if normalized_opt == normalized_target:
                        if is_multiple:
                            locator.select_option(option=[opt_value])
                        else:
                            locator.select_option(value=opt_value)
                        selected_values.append(opt_value)
                        match_found = True
                        break
            
            if not match_found and use_ai_matching and option_texts:
                # Use AI semantic matching
                from services.api.services.mls_automation.enum_matcher import match_enum_with_ai
                matched_option, confidence = match_enum_with_ai(target_str, option_texts, field_name)
                if matched_option and confidence > 0.5:
                    # Find the corresponding option value
                    for i, opt_text in enumerate(option_texts):
                        if opt_text == matched_option:
                            if is_multiple:
                                locator.select_option(option=[option_values[i]])
                            else:
                                locator.select_option(value=option_values[i])
                            selected_values.append(option_values[i])
                            match_found = True
                            break
        
        time.sleep(0.2)
        return len(selected_values) > 0, selected_values[0] if selected_values else None
        
    except Exception as e:
        print(f"Error filling dropdown field: {str(e)}")
        return False, None


def fill_checkbox_field(locator: Locator, value: bool, retries: int = 2) -> bool:
    """
    Fill a checkbox field with enhanced error handling.
    
    Args:
        locator: Locator for the checkbox
        value: Boolean value
        retries: Number of retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    if value is None:
        return False
    
    for attempt in range(retries + 1):
        try:
            # Wait for checkbox to be visible
            locator.wait_for(state="visible", timeout=5000)
            
            # Scroll into view if needed
            locator.scroll_into_view_if_needed()
            time.sleep(0.1)
            
            is_checked = locator.is_checked()
            target_checked = bool(value)
            
            if is_checked != target_checked:
                locator.click()
                time.sleep(0.2)
                
                # Verify the state changed
                new_checked = locator.is_checked()
                if new_checked == target_checked:
                    return True
            else:
                return True  # Already in correct state
            
        except Exception as e:
            if attempt < retries:
                time.sleep(0.5)
                continue
            print(f"Error filling checkbox field after {retries + 1} attempts: {str(e)}")
            return False
    
    return False


def fill_radio_field(page: Page, field_name: str, value: Any, retries: int = 2) -> bool:
    """
    Fill a radio button group with enhanced error handling.
    
    Args:
        page: Playwright page object
        field_name: Name attribute of radio group
        value: Value to select
        retries: Number of retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    if value is None:
        return False
    
    value_str = str(value).strip()
    
    for attempt in range(retries + 1):
        try:
            # Try exact value match first
            radio = page.locator(f'input[type="radio"][name="{field_name}"][value="{value_str}"]').first
            
            if radio.count() == 0:
                # Try case-insensitive value match
                all_radios = page.locator(f'input[type="radio"][name="{field_name}"]').all()
                for r in all_radios:
                    radio_value = r.get_attribute("value") or ""
                    if radio_value.strip().lower() == value_str.lower():
                        radio = r
                        break
                else:
                    if attempt < retries:
                        time.sleep(0.5)
                        continue
                    return False
            
            if radio.count() > 0:
                radio.wait_for(state="visible", timeout=5000)
                radio.scroll_into_view_if_needed()
                time.sleep(0.1)
                radio.click()
                time.sleep(0.2)
                
                # Verify selection
                if radio.is_checked():
                    return True
            
            if attempt < retries:
                time.sleep(0.5)
                continue
            
            return False
        except Exception as e:
            if attempt < retries:
                time.sleep(0.5)
                continue
            print(f"Error filling radio field after {retries + 1} attempts: {str(e)}")
            return False
    
    return False


def fill_date_field(locator: Locator, value: Any, date_format: str = "MM/DD/YYYY", retries: int = 2) -> bool:
    """
    Fill a date input field with enhanced error handling.
    
    Args:
        locator: Locator for the date field
        value: Date value (string, datetime, or date)
        date_format: Target date format (default: MM/DD/YYYY)
        retries: Number of retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    if value is None:
        return False
    
    # Convert value to target format
    date_str = _format_date_for_mls(value, date_format)
    if not date_str:
        return False
    
    for attempt in range(retries + 1):
        try:
            # Wait for field to be visible and enabled
            locator.wait_for(state="visible", timeout=5000)
            if not locator.is_enabled():
                if attempt < retries:
                    time.sleep(0.5)
                    continue
                return False
            
            # Scroll into view if needed
            locator.scroll_into_view_if_needed()
            time.sleep(0.1)
            
            # Clear and fill
            locator.clear()
            time.sleep(0.1)
            locator.fill(date_str)
            time.sleep(0.2)
            
            return True
        except Exception as e:
            if attempt < retries:
                time.sleep(0.5)
                continue
            print(f"Error filling date field after {retries + 1} attempts: {str(e)}")
            return False
    
    return False


def _normalize_string(s: str) -> str:
    """Normalize string for comparison (lowercase, remove special chars)."""
    import re
    return re.sub(r'[^\w\s]', '', s.lower()).strip()


def _format_date_for_mls(value: Any, target_format: str) -> Optional[str]:
    """
    Format date value for MLS form.
    
    Args:
        value: Date value (string, datetime, or date)
        target_format: Target format (e.g., "MM/DD/YYYY")
        
    Returns:
        Formatted date string or None
    """
    from datetime import datetime, date
    
    if value is None:
        return None
    
    # If already a string, try to parse and reformat
    if isinstance(value, str):
        # Try parsing common formats
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                break
            except:
                continue
        else:
            return value  # Return as-is if can't parse
    
    elif isinstance(value, (datetime, date)):
        dt = value if isinstance(value, datetime) else datetime.combine(value, datetime.min.time())
    else:
        return None
    
    # Format according to target
    if target_format == "MM/DD/YYYY":
        return dt.strftime("%m/%d/%Y")
    elif target_format == "YYYY-MM-DD":
        return dt.strftime("%Y-%m-%d")
    else:
        return dt.strftime("%m/%d/%Y")  # Default to US format

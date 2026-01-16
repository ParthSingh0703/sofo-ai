"""
Field discovery utilities for new MLS systems.
Uses AI vision to detect form fields and map them to canonical JSON keys.
"""
import base64
import os
import time
import re
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page

from services.api.services.mls_automation.models import MLSFieldSelector

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def discover_fields_from_page(page: Page) -> List[MLSFieldSelector]:
    """
    Discover form fields on the page using AI vision.
    
    This is a simplified implementation. A full implementation would:
    1. Take screenshot of the form
    2. Use Gemini Vision to identify fields and labels
    3. Extract selectors using Playwright's element inspection
    4. Map fields to canonical JSON keys using semantic matching
    
    Args:
        page: Playwright page object
        
    Returns:
        List of discovered field selectors
    """
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set, skipping field discovery")
        return []
    
    try:
        # Take screenshot of visible area
        screenshot_bytes = page.screenshot(type="png")
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
        
        # Use Gemini Vision to identify form fields
        import google.genai as genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = """Analyze this real estate MLS listing form screenshot.

Your task is to identify ALL form fields and map them to canonical MLS fields.

CANONICAL FIELD CATEGORIES:
1. Listing Location/Identifier: Street Address, Street #, Street Name, City, State, Zip Code, County, Country, Subdivision, Tax Legal Description, Tax Lot, Parcel Number
2. Listing Meta: List Price, Expiration Date, Listing Agreement, Listing Service, Special Listing Conditions, Listing Agreement Document, Flex Listing
3. Property: Property Sub Type, Ownership Type, Levels, Main Level Bedrooms, Other Level Bedrooms, Year Built, Bathrooms Full, Bathrooms Half, Living Area, Living Room, Dining Room, Garage Spaces, Parking Total, Direction Faces, Lot Size Acres, Property Condition, View, Flooring, Construction Material, Waterfront Features, Distance to Water, Restrictions, Foundation Details, Roof, Lot Features
4. Features: Interior Features, Exterior Features, Patio/Porch Features, Fireplaces, Accessibility Features, Horse Amenities, Other Structures, Appliances, Pool Features, Guest Accommodations, Window Features, Security Features, Laundry Location, Fencing, Community Features
5. Utilities: Utilities, Heating, Cooling, Water Source, Sewer, Documents Available, Disclosures
6. Financial: Association, Association Name, Association Fee, Acceptable Financing, Estimated Tax, Tax Year, Tax Annual Amount, Tax Assessed Value, Tax Rate, Buyer Incentive, Tax Exemptions, Possession, Seller Contributions, Intermediary
7. Schools: School District, Elementary School District, Middle/Junior School, High School
8. Showing: Occupant Type, Showing Requirements, Owner Name, Lockbox Type, Lockbox Location, Showing Instructions
9. Agents: Listing Agent, Co Listing Agent
10. Remarks: Directions, Private Remarks, Public Remarks, Syndication Remarks

For each field you identify, return:
{
    "label": "exact label text visible",
    "field_type": "text|number|dropdown|checkbox|radio|date|textarea",
    "canonical_key": "suggested canonical JSON key (e.g., 'location.street_address', 'listing_meta.list_price')",
    "order": 1
}

Return JSON array of all identified fields, ordered top to bottom.

Focus on main listing data entry fields. Ignore navigation, buttons, help text, and non-input elements."""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-exp",
            contents=[{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": screenshot_b64}}
                ]
            }]
        )
        
        response_text = response.text.strip() if hasattr(response, 'text') else str(response).strip()
        
        # Parse JSON response
        import json
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        discovered_fields = json.loads(response_text)
        
        # Convert to MLSFieldSelector objects by finding actual selectors
        field_selectors = []
        for field_info in discovered_fields:
            label = field_info.get("label", "")
            field_type = field_info.get("field_type", "text")
            suggested_json_key = field_info.get("canonical_key")  # AI-suggested mapping
            
            # Try to find the field on the page using label
            from services.api.services.mls_automation.field_filler import find_field_by_label
            locator = find_field_by_label(page, label, field_type)
            
            if locator and locator.count() > 0:
                # Try to get a stable selector
                try:
                    # Get multiple selector strategies
                    selector = _get_stable_selector(page, locator.first)
                    json_key = suggested_json_key or _map_label_to_json_key(label, field_type)
                    
                    # Extract enum values if dropdown/select
                    enum_values = None
                    if field_type in ["dropdown", "select"]:
                        enum_values = _extract_enum_values(locator.first)
                    
                    if selector:
                        field_selectors.append(MLSFieldSelector(
                            label=label,
                            selector=selector,
                            field_type=field_type,
                            json_key=json_key,
                            field_name=None,
                            enum_values=enum_values
                        ))
                    else:
                        # Use label-based discovery
                        field_selectors.append(MLSFieldSelector(
                            label=label,
                            selector=None,
                            field_type=field_type,
                            json_key=json_key,
                            field_name=None,
                            enum_values=enum_values
                        ))
                except Exception as e:
                    # If selector extraction fails, still add with label-based approach
                    json_key = suggested_json_key or _map_label_to_json_key(label, field_type)
                    field_selectors.append(MLSFieldSelector(
                        label=label,
                        selector=None,  # Will use label-based discovery
                        field_type=field_type,
                        json_key=json_key,
                        field_name=None,
                        enum_values=None
                    ))
        
        return field_selectors
        
    except Exception as e:
        print(f"Error in field discovery: {str(e)}")
        return []


def _get_stable_selector(page: Page, locator) -> Optional[str]:
    """
    Extract a stable CSS selector for an element.
    
    Args:
        page: Playwright page object
        locator: Element locator
        
    Returns:
        CSS selector string, or None if not extractable
    """
    try:
        # Try to get id first (most stable)
        element_id = locator.get_attribute("id")
        if element_id:
            return f"#{element_id}"
        
        # Try name attribute
        element_name = locator.get_attribute("name")
        if element_name:
            return f"[name='{element_name}']"
        
        # Try data attributes
        data_testid = locator.get_attribute("data-testid")
        if data_testid:
            return f"[data-testid='{data_testid}']"
        
        # Fallback: use Playwright's internal selector (less stable)
        # This would require evaluating JavaScript, which is complex
        # For now, return None to use label-based discovery
        
        return None
    except:
        return None


def _extract_enum_values(locator) -> Optional[List[str]]:
    """Extract enum values from dropdown/select element."""
    try:
        options = locator.locator("option").all()
        values = []
        for opt in options:
            text = opt.inner_text().strip()
            if text and text.lower() not in ['select', 'choose', '--', '']:
                values.append(text)
        return values if values else None
    except:
        return None


def _map_label_to_json_key(label: str, field_type: str = "text") -> str:
    """
    Map a field label to a canonical JSON key using pattern matching.
    
    Enhanced version with common MLS field mappings.
    
    Args:
        label: Field label text
        field_type: Field type for better matching
        
    Returns:
        Canonical JSON key path
    """
    import re
    label_lower = re.sub(r'[^\w\s]', '', label.lower()).strip()
    label_normalized = re.sub(r'\s+', '_', label_lower)
    
    # Common MLS field mappings (location.field_name or listing_meta.field_name, etc.)
    mappings = {
        # Location fields
        'street_address': 'location.street_address',
        'address': 'location.street_address',
        'street_number': 'location.street_number',
        'street_#': 'location.street_number',
        'street_name': 'location.street_name',
        'city': 'location.city',
        'state': 'location.state',
        'zip': 'location.zip_code',
        'zip_code': 'location.zip_code',
        'county': 'location.county',
        'subdivision': 'location.subdivision',
        
        # Listing meta fields
        'list_price': 'listing_meta.list_price',
        'price': 'listing_meta.list_price',
        'expiration_date': 'listing_meta.expiration_date',
        'listing_agreement': 'listing_meta.listing_agreement',
        'listing_service': 'listing_meta.listing_service',
        'special_listing_conditions': 'listing_meta.special_conditions',
        
        # Property fields (partial list - can be extended)
        'property_sub_type': 'property.property_sub_type',
        'property_type': 'property.property_sub_type',
        'bedrooms': 'property.main_level_bedrooms',
        'bathrooms': 'property.bathrooms_full',
        'living_area': 'property.living_area_sqft',
        'square_feet': 'property.living_area_sqft',
        'year_built': 'property.year_built',
        'garage': 'property.garage_spaces',
        'lot_size': 'property.lot_size_acres',
    }
    
    # Try exact match first
    if label_normalized in mappings:
        return mappings[label_normalized]
    
    # Try partial match
    for pattern, key in mappings.items():
        if pattern in label_normalized:
            return key
    
    # Default: return normalized key (will need manual mapping later)
    return label_normalized

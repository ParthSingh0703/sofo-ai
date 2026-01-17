"""
Generate attractive AI property description for frontend display.
Acts as a top Property Listing Agent to create compelling descriptions.
"""
import os
import json
import re
from typing import Optional, Dict, Any
from uuid import UUID
from services.api.models.canonical import CanonicalListing
from services.api.services.canonical_service import get_canonical, update_canonical


def generate_ai_property_description(listing_id: UUID) -> Dict[str, Any]:
    """
    Generate an attractive property description using AI.
    Acts as a top Property Listing Agent to create compelling descriptions.
    
    Args:
        listing_id: The listing ID to generate description for
        
    Returns:
        Dictionary with success status and description
    """
    # Get canonical listing
    canonical = get_canonical(listing_id)
    if not canonical:
        return {
            "success": False,
            "error": "Canonical listing not found"
        }
    
    # Check if API key is available
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY environment variable not set"
        }
    
    try:
        import google.genai as genai
    except ImportError:
        return {
            "success": False,
            "error": "google.genai library not installed"
        }
    
    # Initialize Gemini client
    client = genai.Client(api_key=api_key)
    
    # Extract property information for the prompt
    property_info = _extract_property_info(canonical)
    
    # Generate description using Gemini
    description = _generate_with_ai(client, property_info, api_key)
    
    if description:
        # Update canonical with AI property description
        canonical.remarks.ai_property_description = description
        update_canonical(listing_id, canonical)
        
        return {
            "success": True,
            "description": description
        }
    else:
        return {
            "success": False,
            "error": "Failed to generate property description"
        }


def _extract_property_info(canonical: CanonicalListing) -> Dict[str, Any]:
    """Extract relevant property information for description generation."""
    info = {
        "location": {
            "street_address": canonical.location.street_address,
            "city": canonical.location.city,
            "state": canonical.location.state,
            "zip_code": canonical.location.zip_code,
            "subdivision": canonical.location.subdivision,
            "county": canonical.location.county,
        },
        "property": {
            "property_sub_type": canonical.property.property_sub_type,
            "levels": canonical.property.levels,
            "main_level_bedrooms": canonical.property.main_level_bedrooms,
            "other_level_bedrooms": canonical.property.other_level_bedrooms,
            "bathrooms_full": canonical.property.bathrooms_full,
            "bathrooms_half": canonical.property.bathrooms_half,
            "living_area_sqft": canonical.property.living_area_sqft,
            "year_built": canonical.property.year_built,
            "property_condition": canonical.property.property_condition,
            "lot_size_acres": canonical.property.lot_size_acres,
            "garage_spaces": canonical.property.garage_spaces,
            "parking_total": canonical.property.parking_total,
            "direction_faces": canonical.property.direction_faces,
            "view": canonical.property.view,
            "distance_to_water": canonical.property.distance_to_water,
            "waterfront_features": canonical.property.waterfront_features,
        },
        "features": {
            "interior_features": canonical.features.interior_features,
            "exterior_features": canonical.features.exterior_features,
            "patio_porch_features": canonical.features.patio_porch_features,
            "fireplaces": canonical.features.fireplaces,
            "flooring": canonical.features.flooring,
            "appliances": canonical.features.appliances,
            "pool_features": canonical.features.pool_features,
            "window_features": canonical.features.window_features,
            "security_features": canonical.features.security_features,
            "community_features": canonical.features.community_features,
        },
        "property_details": {
            "construction_material": canonical.property.construction_material,
            "foundation_details": canonical.property.foundation_details,
            "roof": canonical.property.roof,
            "lot_features": canonical.property.lot_features,
        },
        "utilities": {
            "heating": canonical.utilities.heating,
            "cooling": canonical.utilities.cooling,
            "water_source": canonical.utilities.water_source,
            "sewer": canonical.utilities.sewer,
        },
        "financial": {
            "list_price": canonical.listing_meta.list_price,
            "tax_annual_amount": canonical.financial.tax_annual_amount,
            "tax_year": canonical.financial.tax_year,
            "association_fee": canonical.financial.association_fee,
        },
        "schools": {
            "elementary_school_district": canonical.schools.elementary_school_district,
            "middle_junior_school": canonical.schools.middle_junior_school,
            "high_school": canonical.schools.high_school,
            "school_district": canonical.schools.school_district,
        },
        "poi": canonical.location.poi,  # Points of interest from geo-intelligence
        "directions": canonical.remarks.directions,
    }
    
    # Remove None values and empty lists
    def clean_dict(d):
        if isinstance(d, dict):
            return {k: clean_dict(v) for k, v in d.items() if v is not None and v != []}
        elif isinstance(d, list):
            return [clean_dict(item) for item in d if item is not None]
        else:
            return d
    
    return clean_dict(info)


def _generate_with_ai(client, property_info: Dict[str, Any], api_key: str) -> Optional[str]:
    """Generate property description using Gemini AI."""
    prompt = _build_description_prompt(property_info)
    
    try:
        # Use Gemini 2.5 Flash for text generation
        model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        
        # Call Gemini
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        # Extract text from response
        description = response.text.strip()
        
        # Remove blank lines between paragraphs (replace double newlines with single space)
        description = re.sub(r'\n\s*\n', ' ', description)
        # Remove any remaining excessive whitespace
        description = re.sub(r'\s+', ' ', description)
        # Trim leading/trailing whitespace
        description = description.strip()
        
        # Ensure description is under 1500 characters
        if len(description) > 1200:
            description = description[:1197] + "..."
        
        return description
    
    except (ConnectionError, OSError) as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"AI property description generation failed: Network connection error - Cannot reach Gemini API. Check your internet connection and DNS settings.")
        else:
            print(f"AI property description generation failed: Network error - {error_msg}")
        return None
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"AI property description generation failed: Network connection error - Cannot reach Gemini API. Check your internet connection.")
        else:
            print(f"Error generating AI property description: {error_msg}")
        return None


def _build_description_prompt(property_info: Dict[str, Any]) -> str:
    """Build the prompt for AI property description generation."""
    info_json = json.dumps(property_info, indent=2)
    
    prompt = f"""You are a top Property Listing Agent with years of experience creating compelling property descriptions that attract buyers.

Your task is to create an attractive, professional property description based on the following property information. The description should be engaging, highlight key features, and appeal to potential buyers while remaining factual and accurate.

PROPERTY INFORMATION:
{info_json}

INSTRUCTIONS:
1. Act as a top Property Listing Agent - use your expertise to create a compelling description
2. Highlight the most attractive features of the property
3. Create an engaging narrative that makes the property appealing
4. Use professional real estate language
5. Mention location advantages, nearby amenities (from POI data), and property features
6. Keep the description under 1200 characters
7. Write in paragraph format (no bullet points)
8. CRITICAL: Do NOT include blank lines between paragraphs - paragraphs should flow continuously without line breaks
9. Be enthusiastic but factual - do not exaggerate or invent features
10. If POI (points of interest) data is available, naturally incorporate nearby amenities
11. If waterfront features or water proximity exists, highlight it appropriately
12. Mention schools if available and relevant
13. Include property condition, year built, and key statistics naturally

IMPORTANT:
- Only mention features that are present in the property information
- Do not invent or assume features not provided
- Keep it professional and MLS-appropriate
- Make it attractive and compelling while staying truthful

Generate the property description now:"""
    
    return prompt

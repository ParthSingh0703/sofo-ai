"""
Generate listing descriptions (public_remarks, syndication_remarks) from canonical data.
Text-only generation, no image analysis for factual content.
"""
import os
import json
import re
from typing import Literal, Optional, Dict, Any
from services.api.models.canonical import CanonicalListing


def generate_listing_descriptions(
    canonical: CanonicalListing
) -> Dict[str, str]:
    """
    Generate public_remarks and syndication_remarks from canonical listing data.
    AI automatically determines the appropriate tone based on property characteristics.
    
    Rules:
    - Do NOT add features not present in canonical
    - Must be MLS-safe and Fair Housing compliant
    - No demographic, lifestyle, or neighborhood claims
    - No investment or appreciation language
    - Paragraph format (no bullet highlights)
    - public_remarks ≤ 1500 characters
    - AI determines tone (neutral, luxury, family-friendly, etc.) based on property features
    - public_remarks and syndication_remarks MUST be identical (same content)
    - Do NOT generate private_remarks (user will provide this)
    - If property has only 1 level, all bedrooms are on the main level
    - Include appliance information if provided in canonical data
    
    Args:
        canonical: The canonical listing data
        
    Returns:
        Dictionary with public_remarks and syndication_remarks (identical content)
    """
    # Extract key information from canonical
    property_info = _extract_property_info(canonical)
    
    # Generate descriptions using LLM (if available) or template-based
    llm_enabled = os.getenv("GEMINI_API_KEY") is not None or os.getenv("LLM_API_KEY") is not None
    
    if llm_enabled:
        descriptions = _generate_with_llm(property_info)
    else:
        descriptions = _generate_template_based(property_info)
    
    # Ensure public_remarks is within character limit
    if len(descriptions.get("public_remarks", "")) > 1500:
        descriptions["public_remarks"] = descriptions["public_remarks"][:1497] + "..."
    
    return descriptions


def _extract_property_info(canonical: CanonicalListing) -> Dict[str, any]:
    """
    Extract relevant information from canonical for description generation.
    """
    return {
        "property_type": canonical.property.property_sub_type,
        "bedrooms": canonical.property.main_level_bedrooms,
        "bathrooms_full": canonical.property.bathrooms_full,
        "bathrooms_half": canonical.property.bathrooms_half,
        "living_area_sqft": canonical.property.living_area_sqft,
        "lot_size_acres": canonical.property.lot_size_acres,
        "year_built": canonical.property.year_built,
        "garage_spaces": canonical.property.garage_spaces,
        "location": {
            "city": canonical.location.city,
            "state": canonical.location.state,
            "subdivision": canonical.location.subdivision
        },
        "features": {
            "interior": canonical.features.interior_features,
            "exterior": canonical.features.exterior_features,
            "appliances": canonical.features.appliances,
            "utilities": canonical.utilities.utilities,
            "heating": canonical.utilities.heating,
            "cooling": canonical.utilities.cooling
        },
        "levels": canonical.property.levels,
        "main_level_bedrooms": canonical.property.main_level_bedrooms,
        "other_level_bedrooms": canonical.property.other_level_bedrooms,
        "list_price": canonical.listing_meta.list_price
    }


def _generate_with_llm(property_info: Dict) -> Dict[str, str]:
    """
    Generate descriptions using Gemini 2.5 Flash for text generation.
    AI automatically determines the appropriate tone based on property characteristics.
    """
    try:
        import google.genai as genai
        
        # Create Gemini client
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # Use Gemini 2.5 Flash for text generation
        model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        
        prompt = f"""Generate MLS listing descriptions based on the following property information.

Analyze the property characteristics and automatically determine the most appropriate writing tone:
- For luxury properties (high-end features, premium finishes): Use refined, elegant language
- For family-friendly properties (multiple bedrooms, yards, schools): Emphasize family-oriented features
- For investment properties: Focus on value and potential
- For standard properties: Use neutral, professional tone

CRITICAL RULES:
- Do NOT add features not present in the provided data
- Must be MLS-safe and Fair Housing compliant
- No demographic, lifestyle, or neighborhood claims
- No investment or appreciation language
- Paragraph format (no bullet points)
- public_remarks must be ≤ 1500 characters
- Choose tone naturally based on property features

IMPORTANT PROPERTY STRUCTURE NOTES:
- If the property has only 1 level (levels = 1), then the only floor is the main level
- In single-level properties, all bedrooms are on the main level (main_level_bedrooms includes all bedrooms)
- Do NOT reference "other levels" or "upper/lower levels" for single-level properties

APPLIANCE INFORMATION:
- Include appliance information if provided in the property data
- List specific appliances when available (e.g., "Kitchen features stainless steel appliances including refrigerator, dishwasher, and range")

REMARKS GENERATION:
- public_remarks and syndication_remarks MUST be identical (same content for both)
- Do NOT generate private_remarks - this will be provided by the user
- Focus on factual property features and characteristics

Property Information:
{_format_property_info(property_info)}

Generate descriptions:
1. public_remarks: Main description for public MLS listing (≤ 1500 chars)
2. syndication_remarks: MUST be identical to public_remarks (same content)

Return JSON:
{{
  "public_remarks": "string",
  "syndication_remarks": "string"
}}"""
        
        # Call Gemini
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        response_text = response.text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return _generate_template_based(property_info)
    
    except ImportError:
        # Fallback if google-genai not installed
        print("google-genai library not installed. Install with: pip install google-genai")
        return _generate_template_based(property_info)
    except (ConnectionError, OSError) as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"Gemini description generation failed: Network connection error - Cannot reach Gemini API. Check your internet connection and DNS settings. Using template-based fallback.")
        else:
            print(f"Gemini description generation failed: Network error - {error_msg}. Using template-based fallback.")
        return _generate_template_based(property_info)
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"Gemini description generation failed: Network connection error - Cannot reach Gemini API. Check your internet connection. Using template-based fallback.")
        else:
            print(f"Gemini description generation failed: {error_msg}. Using template-based fallback.")
        return _generate_template_based(property_info)
    
    # # OpenAI implementation (commented for testing with Groq)
    # try:
    #     from openai import OpenAI
    #     client = OpenAI(api_key=os.getenv("LLM_API_KEY"))
    #     
    #     tone_instruction = TONE_STYLES.get(tone, TONE_STYLES["neutral"])
    #     
    #     prompt = f"""Generate MLS listing descriptions based on the following property information.
    #
    # {tone_instruction}
    #
    # CRITICAL RULES:
    # - Do NOT add features not present in the provided data
    # - Must be MLS-safe and Fair Housing compliant
    # - No demographic, lifestyle, or neighborhood claims
    # - No investment or appreciation language
    # - Paragraph format (no bullet points)
    # - public_remarks must be ≤ 1500 characters
    #
    # Property Information:
    # {_format_property_info(property_info)}
    #
    # Generate two descriptions:
    # 1. public_remarks: Main description for public MLS listing (≤ 1500 chars)
    # 2. syndication_remarks: Additional remarks for syndication (can be longer)
    #
    # Return JSON:
    # {{
    #   "public_remarks": "string",
    #   "syndication_remarks": "string"
    # }}"""
    #     
    #     response = client.chat.completions.create(
    #         model=os.getenv("LLM_MODEL", "gpt-4"),
    #         messages=[
    #             {"role": "system", "content": "You are a real estate listing description writer. Generate MLS-compliant, factual descriptions."},
    #             {"role": "user", "content": prompt}
    #         ],
    #         max_tokens=2000,
    #         temperature=0.7
    #     )
    #     
    #     response_text = response.choices[0].message.content
    #     json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    #     if json_match:
    #         return json.loads(json_match.group())
    #     else:
    #         return _generate_template_based(property_info, tone)
    # 
    # except Exception as e:
    #     print(f"LLM description generation failed: {str(e)}")
    #     return _generate_template_based(property_info, tone)


def _generate_template_based(property_info: Dict) -> Dict[str, str]:
    """
    Generate descriptions using template-based approach (fallback).
    """
    parts = []
    
    # Address/Property type
    if property_info.get("location", {}).get("city"):
        parts.append(f"This {property_info.get('property_type', 'property')} is located in {property_info['location']['city']}")
        if property_info["location"].get("state"):
            parts[-1] += f", {property_info['location']['state']}"
        parts[-1] += "."
    
    # Size and layout
    if property_info.get("bedrooms") and property_info.get("bathrooms_full"):
        bed_bath = f"{property_info['bedrooms']} bedroom"
        if property_info['bedrooms'] != 1:
            bed_bath += "s"
        bed_bath += f", {property_info['bathrooms_full']} full bathroom"
        if property_info.get("bathrooms_half"):
            bed_bath += f", {property_info['bathrooms_half']} half bathroom"
        if property_info.get("bathrooms_half") and property_info['bathrooms_half'] != 1:
            bed_bath = bed_bath.replace("half bathroom", "half bathrooms")
        parts.append(f"The home features {bed_bath}.")
    
    # Square footage
    if property_info.get("living_area_sqft"):
        parts.append(f"Living area is approximately {property_info['living_area_sqft']:,} square feet.")
    
    # Lot size
    if property_info.get("lot_size_acres"):
        parts.append(f"Lot size is {property_info['lot_size_acres']} acres.")
    
    # Year built
    if property_info.get("year_built"):
        parts.append(f"Built in {property_info['year_built']}.")
    
    # Garage
    if property_info.get("garage_spaces"):
        parts.append(f"Garage space for {property_info['garage_spaces']} vehicle(s).")
    
    public_remarks = " ".join(parts)
    
    # Include appliances if available
    if property_info.get("features", {}).get("appliances"):
        appliances = ", ".join(property_info["features"]["appliances"])
        if appliances:
            public_remarks += f" Appliances include {appliances}."
    
    # Include interior features if available
    if property_info.get("features", {}).get("interior"):
        features = ", ".join(property_info["features"]["interior"][:5])  # Limit to 5 features
        if features:
            public_remarks += f" Interior features include {features}."
    
    # Public remarks and syndication remarks must be identical
    syndication_remarks = public_remarks
    
    return {
        "public_remarks": public_remarks[:1500],
        "syndication_remarks": syndication_remarks[:1500]  # Keep same length limit
    }


def _format_property_info(property_info: Dict) -> str:
    """
    Format property info as text for LLM prompt.
    """
    lines = []
    
    if property_info.get("property_type"):
        lines.append(f"Property Type: {property_info['property_type']}")
    
    # Handle levels and bedrooms
    levels = property_info.get("levels")
    if levels is not None:
        lines.append(f"Levels: {levels}")
        if levels == 1:
            lines.append("NOTE: Single-level property - all bedrooms are on the main level")
    
    if property_info.get("main_level_bedrooms") is not None:
        lines.append(f"Main Level Bedrooms: {property_info['main_level_bedrooms']}")
    if property_info.get("other_level_bedrooms") is not None and property_info.get("other_level_bedrooms", 0) > 0:
        lines.append(f"Other Level Bedrooms: {property_info['other_level_bedrooms']}")
    elif property_info.get("bedrooms"):  # Fallback for backward compatibility
        lines.append(f"Bedrooms: {property_info['bedrooms']}")
    
    if property_info.get("bathrooms_full"):
        lines.append(f"Full Bathrooms: {property_info['bathrooms_full']}")
    if property_info.get("bathrooms_half"):
        lines.append(f"Half Bathrooms: {property_info['bathrooms_half']}")
    if property_info.get("living_area_sqft"):
        lines.append(f"Living Area: {property_info['living_area_sqft']:,} sqft")
    if property_info.get("lot_size_acres"):
        lines.append(f"Lot Size: {property_info['lot_size_acres']} acres")
    if property_info.get("year_built"):
        lines.append(f"Year Built: {property_info['year_built']}")
    if property_info.get("garage_spaces"):
        lines.append(f"Garage Spaces: {property_info['garage_spaces']}")
    
    # Include appliances if available
    if property_info.get("features", {}).get("appliances"):
        appliances = ", ".join(property_info["features"]["appliances"])
        lines.append(f"Appliances: {appliances}")
    
    if property_info.get("location", {}).get("city"):
        lines.append(f"Location: {property_info['location'].get('city', '')}, {property_info['location'].get('state', '')}")
    if property_info.get("list_price"):
        lines.append(f"List Price: ${property_info['list_price']:,.0f}")
    
    return "\n".join(lines)

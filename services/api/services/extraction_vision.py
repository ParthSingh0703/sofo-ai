"""
Vision-based AI extraction service for image-based documents.
Uses vision models to extract structured data from document images.
"""
import os
import re
import json
import base64
import io
from typing import Dict, Any, Optional
from pathlib import Path
from services.api.models.extraction import ExtractedField, FieldProvenance, DocumentExtractionResult


def extract_with_vision(
    file_path: str,
    file_id: str,
    file_extension: str
) -> DocumentExtractionResult:
    """
    Extract data from document using vision-based AI.
    Converts document pages to images and uses vision model for extraction.
    
    Args:
        file_path: Path to document file
        file_id: Document UUID
        file_extension: File extension
        
    Returns:
        DocumentExtractionResult with extracted fields and provenance
    """
    # Convert document to images (one per page)
    page_images = _convert_document_to_images(file_path, file_extension)
    
    # Check if conversion produced any images
    if not page_images:
        raise ValueError(
            f"Failed to convert document to images. "
            f"File extension '{file_extension}' may not be supported for vision extraction. "
            f"Supported formats: .pdf"
        )
    
    # Extract structured data using vision model
    extracted_fields = _extract_with_vision_ai(page_images, file_id)
    
    return DocumentExtractionResult(
        document_id=file_id,
        extraction_method="vision",
        text_quality_score=None,  # Not applicable for vision extraction
        extracted_fields=extracted_fields,
        raw_text=None,  # Vision doesn't produce raw text
        page_texts={}  # Vision doesn't produce page texts
    )


def _convert_document_to_images(file_path: str, file_extension: str) -> Dict[int, bytes]:
    """
    Convert document pages to image bytes.
    Each page becomes a separate image.
    
    Returns:
        Dictionary mapping page_number -> image_bytes
    """
    page_images = {}
    ext = file_extension.lower()
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document file not found: {file_path}")
    
    try:
        if ext == '.pdf':
            # Convert PDF pages to images
            from pdf2image import convert_from_path
            from pdf2image.exceptions import PDFInfoNotInstalledError
            
            import shutil
            
            # Get Poppler path from environment or try to find it
            poppler_path = os.getenv("POPPLER_PATH")
            
            # If not set, try common Windows locations
            if not poppler_path:
                common_paths = [
                    r"C:\Program Files\poppler\Library\bin",
                    r"C:\poppler\bin",
                    r"C:\tools\poppler\bin",
                    os.path.join(os.path.expanduser("~"), "poppler", "bin"),
                ]
                
                # Check if pdftoppm is in PATH
                if shutil.which("pdftoppm"):
                    poppler_path = None  # Use system PATH
                else:
                    # Try to find poppler in common locations
                    for path in common_paths:
                        if os.path.exists(path) and os.path.exists(os.path.join(path, "pdftoppm.exe")):
                            poppler_path = path
                            break
            
            try:
                # Convert PDF pages to images
                if poppler_path:
                    images = convert_from_path(file_path, dpi=200, poppler_path=poppler_path)
                else:
                    images = convert_from_path(file_path, dpi=200)
                
                for page_num, image in enumerate(images, start=1):
                    img_bytes = io.BytesIO()
                    image.save(img_bytes, format='PNG')
                    page_images[page_num] = img_bytes.getvalue()
            except PDFInfoNotInstalledError as e:
                error_msg = (
                    f"Poppler is not found. Error: {str(e)}\n\n"
                    "Solutions:\n"
                    "1. Set POPPLER_PATH environment variable to Poppler bin directory\n"
                    "2. Add Poppler bin directory to your system PATH\n"
                    "3. Download from: https://github.com/oschwartz10612/poppler-windows/releases\n"
                    "4. Or install via: conda install -c conda-forge poppler\n\n"
                    f"Current PATH: {os.environ.get('PATH', 'Not set')[:200]}"
                )
                raise ValueError(error_msg)
        
        elif ext in ['.docx', '.doc']:
            # DOCX/DOC files are not yet supported for vision extraction
            # Would need conversion to PDF first, then to images
            raise ValueError(
                f"Vision extraction is not yet supported for {ext} files. "
                f"Please use 'native_text_only' method or convert to PDF first. "
                f"Supported formats for vision extraction: .pdf"
            )
        
        elif ext == '.txt':
            # TXT files don't need vision extraction - use native text instead
            raise ValueError(
                f"Vision extraction is not applicable for {ext} files. "
                f"Please use 'native_text_only' method instead. "
                f"Supported formats for vision extraction: .pdf"
            )
        
        else:
            # Unknown file extension
            raise ValueError(
                f"Unsupported file format for vision extraction: {ext}. "
                f"Supported formats: .pdf"
            )
        
        return page_images
    
    except ImportError as e:
        raise ImportError(f"Required library for vision extraction not installed: {e}")
    except (FileNotFoundError, ValueError):
        # Re-raise FileNotFoundError and ValueError as-is
        raise
    except Exception as e:
        raise Exception(f"Failed to convert document to images: {str(e)}")


def _extract_with_vision_ai(page_images: Dict[int, bytes], file_id: str) -> Dict[str, ExtractedField]:
    """
    Use vision AI model to extract structured data from page images.
    
    Args:
        page_images: Dictionary of page_number -> image_bytes
        file_id: Document UUID for provenance
        
    Returns:
        Dictionary of field_path -> ExtractedField
    """
    extracted_fields = {}
    
    # Check if vision API key is configured
    vision_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VISION_API_KEY")
    # Use Gemini 2.5 Flash for document extraction
    vision_model = os.getenv("VISION_MODEL", "gemini-2.5-flash")
    
    if not vision_api_key:
        # Fallback: Return empty if no API key configured
        # In production, you might want to raise an error or use default
        return extracted_fields
    
    # Process each page
    for page_number, image_bytes in page_images.items():
        try:
            # Encode image to base64 for API
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Call vision API (using Groq for testing)
            # Note: Groq models may not support vision. For full vision support, use OpenAI.
            page_fields = _call_vision_api(image_base64, vision_model, vision_api_key)
            
            # Add provenance to each field with confidence scores
            for field_path, field_data in page_fields.items():
                if isinstance(field_data, dict):
                    value = field_data.get("value")
                    confidence = field_data.get("confidence")
                else:
                    # Backward compatibility: if API returns simple value
                    value = field_data
                    confidence = None
                
                # Only include fields with non-null values
                if value is not None:
                    extracted_fields[field_path] = ExtractedField(
                        value=value,
                        provenance=FieldProvenance(
                            file_id=file_id,
                            page_number=page_number,
                            source_type="vision",
                            confidence=confidence
                        )
                    )
        
        except Exception as e:
            # Log error but continue with other pages
            print(f"Error processing page {page_number}: {str(e)}")
            continue
    
    return extracted_fields


def _call_vision_api(image_base64: str, model: str, api_key: str) -> Dict[str, Any]:
    """
    Call Gemini API to extract structured data from document image.
    Uses Gemini 2.5 Flash for vision-based extraction.
    
    Args:
        image_base64: Base64-encoded image
        model: Model name to use (default: gemini-2.5-flash)
        api_key: Gemini API key
        
    Returns:
        Dictionary of field_path -> {value, confidence}
    """
    try:
        import google.genai as genai
        
        # Create Gemini client
        client = genai.Client(api_key=api_key)
        
        # Use Gemini 2.5 Flash for document extraction
        model_name = model if model else "gemini-2.5-flash"
        
        # Detailed prompt matching specification
        prompt = _get_vision_extraction_prompt()
        
        # Decode base64 image and convert back to base64 for new API
        import io
        from PIL import Image
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # Convert PIL Image to base64 for new API format
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_base64_new = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        # Call Gemini with image and prompt
        response = client.models.generate_content(
            model=model_name,
            contents=[
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": img_base64_new}}
                ]}
            ]
        )
        
        # Parse response JSON
        response_text = response.text
        
        # Extract JSON from response (might be wrapped in markdown code blocks)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            extracted_data = json.loads(json_match.group())
            # Flatten the nested structure to field_path -> {value, confidence}
            return _flatten_vision_response(extracted_data)
        else:
            return {}
    
    except ImportError:
        raise ImportError("google-genai library required for vision extraction. Install with: pip install google-genai")
    except (ConnectionError, OSError) as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            raise Exception(f"Network connection failed: Cannot reach Gemini API. Check your internet connection and DNS settings. Error: {error_msg}")
        else:
            raise Exception(f"Network error during Gemini vision API call: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            raise Exception(f"Network connection failed: Cannot reach Gemini API. Check your internet connection. Error: {error_msg}")
        raise Exception(f"Gemini vision API call failed: {error_msg}")


def _get_vision_extraction_prompt() -> str:
    """
    Get the detailed vision extraction prompt matching the specification.
    """
    return """You are a vision-based document understanding system.

Your task is to extract structured MLS listing information from IMAGES of real estate documents
(scanned PDFs, screenshots, photos of MLS sheets, listing agreements, disclosures).

CRITICAL RULES:
- ONLY extract information that is CLEARLY VISIBLE in the image.
- DO NOT guess, infer, or fabricate values.
- If a value is not visible or not legible, return null.
- DO NOT perform OCR-style full text reconstruction.
- Output MUST be valid JSON matching the provided schema.
- This data will be reviewed and edited by a human before MLS submission.

----------------------------------------
DATE FORMAT INSTRUCTIONS
----------------------------------------
- All dates visible in the document will be in US format (MM/DD/YYYY), e.g., "04/02/2026" or "4/2/2026"
- Extract dates exactly as written in the document
- For expiration_date: You MUST output the date in date-time format (YYYY-MM-DDTHH:MM:SS)
- Convert US format dates to date-time format:
  * "04/02/2026" or "4/2/2026" → "2026-04-02T00:00:00"
  * "12/31/2025" → "2025-12-31T00:00:00"
  * Always use 4-digit year, 2-digit month, 2-digit day
  * Set time to 00:00:00 (midnight)
- If date is already in ISO format, keep it as date-time format
- Only extract if the date is clearly visible and legible in the image

----------------------------------------
SPECIAL CONDITIONS EXTRACTION
----------------------------------------
- special_conditions should ONLY be extracted if "short sale" is specifically mentioned in the document
- If "short sale" is mentioned, extract the relevant text about the short sale
- If "short sale" is NOT mentioned, return null (do NOT infer or guess)
- Do NOT extract other conditions unless they are explicitly about a short sale
- Only extract if clearly visible in the image

----------------------------------------
PROPERTY CONDITION EXTRACTION
----------------------------------------
- Check if the document indicates this is a "new construction" property
- Look for keywords like: "new construction", "new build", "newly constructed", "new home", "newly built", "under construction", "to be built", "pre-construction"
- If the document clearly indicates new construction, set property_condition to "new construction"
- If the document does NOT indicate new construction, set property_condition to "resale"
- Only extract if this information is clearly visible in the image

----------------------------------------
WATERFRONT FEATURES EXTRACTION
----------------------------------------
- waterfront_features should ONLY be extracted if the property is directly adjacent to a water body (lake, river, creek, pond, bay, ocean, etc.)
- If the document indicates the property is directly on or adjacent to water, extract the features of the water body:
  * Name of the water body (e.g., "Lake Travis", "Colorado River")
  * Type of water body (e.g., "Lake", "River", "Creek", "Pond", "Bay", "Ocean")
  * Any specific features mentioned (e.g., "sandy beach", "boat dock", "fishing access")
- Format: Combine name and type, e.g., "Lake Travis, Lake" or "Colorado River, River"
- If the property is NOT directly adjacent to water, return null
- Do NOT extract if only distance to water is mentioned (use distance_to_water field for that)
- Only extract if clearly visible in the image

----------------------------------------
TAX INFORMATION EXTRACTION
----------------------------------------
- When extracting tax information from tax documents, ALWAYS extract the LATEST/MOST RECENT year's tax data
- Look for multiple tax years visible in the document and identify the most recent one
- Extract tax_year, tax_annual_amount, tax_assessed_value, and tax_rate for the LATEST year only
- If multiple years are visible (e.g., "2023: $5,000" and "2024: $5,500"), extract the higher/newer year (2024)
- If only one year is visible, extract that year's information
- Do NOT extract older tax years - only the most recent/latest year
- Only extract if the tax information is clearly visible and legible in the image

----------------------------------------
INTERMEDIARY EXTRACTION
----------------------------------------
- First, check if intermediary information is already visible in the document text (e.g., "Intermediary: Yes", "Intermediary: No", "Intermediary Status: Yes")
- If intermediary information is found in visible text → extract that value (true/false)
- ONLY if intermediary information is NOT found in visible text, then look for it in LISTING AGREEMENT documents:
  * Look for a section or field labeled "Intermediary" or "Intermediary Status" in the listing agreement
  * Check for a checkbox, box, or field that is:
    - Checked (✓, X, checkmark visible)
    - Crossed (X, × visible)
    - Marked with any mark indicating selection (visible mark in the box)
  * If a box/checkbox under "Intermediary" is checked, crossed, or marked → set intermediary to true
  * If the box is empty, unchecked, or not marked → set intermediary to false
  * If the "Intermediary" section/field is not present or not visible in the listing agreement → return null
- Priority: Text information first, then checkbox/box in listing agreement if not found
- Only extract if the intermediary information or checkbox is clearly visible in the image

----------------------------------------
EXTRACTION STRATEGY
----------------------------------------
- Focus on MLS-relevant structured fields.
- Prefer exact values as written in the document.
- Preserve formatting for remarks if visible.
- If a section is not present in the document, return nulls for its fields.
- If the document is irrelevant, return an empty JSON object {}.

----------------------------------------
LIVING AREA EXTRACTION (CRITICAL - property.living_area_sqft)
----------------------------------------
- This is the INTERIOR HEATED/FINISHED square footage of the home, NOT lot size or garage size
- Extract the numeric value (integer) from ANY of these exact patterns visible in the document:
  * "Living Area: 2,500 sqft" → extract 2500
  * "Living Area Sqft: 2500" → extract 2500
  * "Total Living Area: 2,500" → extract 2500
  * "Heated Living Area: 2500 sq ft" → extract 2500
  * "Finished Living Area: 2,500 SF" → extract 2500
  * "Living Room Area: 2500" → extract 2500
  * "SFLA: 2500" or "SF LA: 2500" → extract 2500
  * "Square Feet: 2,500" (when context indicates living area) → extract 2500
  * "2,500 sqft" or "2500 sqft" (when labeled as living/heated/finished area) → extract 2500
- Look for these keywords near the number: "living", "heated", "finished", "interior", "SFLA", "SF LA"
- DO NOT extract: lot size, lot sqft, garage sqft, basement sqft (unless it's finished living space)
- Remove commas and extract ONLY the numeric value (e.g., "2,500" → 2500, "1,234.5" → 1234)
- If you see multiple living area values, prioritize in this order:
  1. "Heated Living Area" or "Heated Sqft"
  2. "Finished Living Area" or "Finished Sqft"
  3. "Total Living Area" or "Total Sqft"
  4. "Living Area" or "Living Sqft"
  5. Any other sqft value clearly indicating interior living space
- If the value includes decimals, round to nearest integer
- If units are in square meters, multiply by 10.764 to convert to square feet
- Only extract if the value is clearly visible and legible in the image

----------------------------------------
OUTPUT FORMAT
----------------------------------------
Return a SINGLE JSON object that conforms to the schema below.

Each extracted field must be an object:
{
  "value": <actual value or null>,
  "confidence": <number between 0 and 1>
}

Confidence guidelines:
- 0.9–1.0 → clearly visible, unambiguous
- 0.6–0.8 → visible but minor ambiguity
- <0.6 → weak visibility (still do NOT guess)

----------------------------------------
CANONICAL SCHEMA TO EXTRACT
----------------------------------------

{
  "listing_meta": {
    "flex_listing": { "value": boolean | null, "confidence": number },
    "listing_agreement": { "value": string | null, "confidence": number },
    "listing_agreement_document": { "value": string | null, "confidence": number },
    "listing_service": { "value": string | null, "confidence": number },
    "list_price": { "value": number | null, "confidence": number },
    "expiration_date": { "value": string | null, "confidence": number },
    "special_conditions": { "value": string | null, "confidence": number }
  },
  "location": {
    "street_number": { "value": string | null, "confidence": number },
    "street_name": { "value": string | null, "confidence": number },
    "street_address": { "value": string | null, "confidence": number },
    "city": { "value": string | null, "confidence": number },
    "county": { "value": string | null, "confidence": number },
    "state": { "value": string | null, "confidence": number },
    "country": { "value": string | null, "confidence": number },
    "zip_code": { "value": string | null, "confidence": number },
    "subdivision": { "value": string | null, "confidence": number },
    "tax_legal_description": { "value": string | null, "confidence": number },
    "tax_lot": { "value": string | null, "confidence": number },
    "parcel_number": { "value": string | null, "confidence": number },
    "additional_parcel": { "value": boolean | null, "confidence": number },
    "additional_parcel_description": { "value": string | null, "confidence": number },
    "mla_area": { "value": string | null, "confidence": number },
    "flood_plain": { "value": boolean | null, "confidence": number },
    "etj": { "value": boolean | null, "confidence": number },
    "latitude": { "value": number | null, "confidence": number },
    "longitude": { "value": number | null, "confidence": number }
  },
  "schools": {
    "elementary_school_district": { "value": string | null, "confidence": number },
    "middle_junior_school": { "value": string | null, "confidence": number },
    "high_school": { "value": string | null, "confidence": number },
    "school_district": { "value": string | null, "confidence": number }
  },
  "property": {
    "property_sub_type": { "value": string | null, "confidence": number },
    "ownership_type": { "value": string | null, "confidence": number },
    "levels": { "value": number | null, "confidence": number },
    "main_level_bedrooms": { "value": number | null, "confidence": number },
    "other_level_bedrooms": { "value": number | null, "confidence": number },
    "year_built": { "value": number | null, "confidence": number },
    "year_built_source": { "value": string | null, "confidence": number },
    "bathrooms_full": { "value": number | null, "confidence": number },
    "bathrooms_half": { "value": number | null, "confidence": number },
    "living_area_sqft": { "value": number | null, "confidence": number },
    "living_area_source": { "value": string | null, "confidence": number },
    "garage_spaces": { "value": number | null, "confidence": number },
    "parking_total": { "value": number | null, "confidence": number },
    "direction_faces": { "value": string | null, "confidence": number },
    "lot_size_acres": { "value": number | null, "confidence": number },
    "property_condition": { "value": string | null, "confidence": number },
    "view": { "value": string | null, "confidence": number },
    "distance_to_water": { "value": number | null, "confidence": number },
    "waterfront_features": { "value": string | null, "confidence": number },
    "restrictions": { "value": string | null, "confidence": number },
    "living_room": { "value": string | null, "confidence": number },
    "dining_room": { "value": string | null, "confidence": number },
    "construction_material": { "value": string[] | [], "confidence": number },
    "foundation_details": { "value": string[] | [], "confidence": number },
    "roof": { "value": string[] | [], "confidence": number },
    "lot_features": { "value": string[] | [], "confidence": number }
  },
  "features": {
    "interior_features": { "value": string[] | [], "confidence": number },
    "exterior_features": { "value": string[] | [], "confidence": number },
    "patio_porch_features": { "value": string[] | [], "confidence": number },
    "fireplaces": { "value": string[] | [], "confidence": number },
    "flooring": { "value": string[] | [], "confidence": number },
    "accessibility_features": { "value": string[] | [], "confidence": number },
    "horse_amenities": { "value": string[] | [], "confidence": number },
    "other_structures": { "value": string[] | [], "confidence": number },
    "appliances": { "value": string[] | [], "confidence": number },
    "pool_features": { "value": string[] | [], "confidence": number },
    "guest_accommodations": { "value": string | null, "confidence": number },
    "window_features": { "value": string[] | [], "confidence": number },
    "security_features": { "value": string[] | [], "confidence": number },
    "laundry_location": { "value": string | null, "confidence": number },
    "fencing": { "value": string | null, "confidence": number },
    "community_features": { "value": string[] | [], "confidence": number }
  },
  "utilities": {
    "utilities": { "value": string[] | [], "confidence": number },
    "heating": { "value": string[] | [], "confidence": number },
    "cooling": { "value": string[] | [], "confidence": number },
    "water_source": { "value": string[] | [], "confidence": number },
    "sewer": { "value": string[] | [], "confidence": number },
    "documents_available": { "value": string[] | [], "confidence": number },
    "disclosures": { "value": string[] | [], "confidence": number }
  },
  "green_energy": {
    "green_energy": { "value": string[] | [], "confidence": number },
    "green_sustainability": { "value": string[] | [], "confidence": number }
  },
  "financial": {
    "association": { "value": boolean | null, "confidence": number },
    "association_name": { "value": string | null, "confidence": number },
    "association_fee": { "value": number | null, "confidence": number },
    "association_amount": { "value": number | null, "confidence": number },
    "acceptable_financing": { "value": string[] | [], "confidence": number },
    "estimated_tax": { "value": number | null, "confidence": number },
    "tax_year": { "value": number | null, "confidence": number },
      // NOTE: Extract the LATEST/MOST RECENT year from tax documents. If multiple years visible, use the newest year.
    "tax_annual_amount": { "value": number | null, "confidence": number },
      // NOTE: Extract for the latest tax year only.
    "tax_assessed_value": { "value": number | null, "confidence": number },
      // NOTE: Extract for the latest tax year only.
    "tax_rate": { "value": number | null, "confidence": number },
    "buyer_incentive": { "value": string | null, "confidence": number },
    "tax_exemptions": { "value": string[] | [], "confidence": number },
    "possession": { "value": string | null, "confidence": number },
    "seller_contributions": { "value": boolean | null, "confidence": number },
    "intermediary": { "value": boolean | null, "confidence": number }
      // NOTE: First check visible text for intermediary info. If not found, then check listing agreement for checked/crossed box under "Intermediary" title. If checked/marked → true, if empty/unchecked → false, if not present → null.
  },
  "showing": {
    "occupant_type": { "value": string | null, "confidence": number },
    "showing_requirements": { "value": string[] | [], "confidence": number },
    "owner_name": { "value": string | null, "confidence": number },
    "lockbox_type": { "value": string | null, "confidence": number },
    "lockbox_location": { "value": string | null, "confidence": number },
    "showing_instructions": { "value": string | null, "confidence": number }
  },
  "agents": {
    "listing_agent": { "value": string | null, "confidence": number },
    "co_listing_agent": { "value": string | null, "confidence": number }
  },
  "remarks": {
    "directions": { "value": string | null, "confidence": number },
    "private_remarks": { "value": string | null, "confidence": number },
    "public_remarks": { "value": string | null, "confidence": number },
    "syndication_remarks": { "value": string | null, "confidence": number }
  },
  "media": {
    "branded_virtual_tour_url": { "value": string | null, "confidence": number },
    "unbranded_virtual_tour_url": { "value": string | null, "confidence": number },
    "branded_video_tour_url": { "value": string | null, "confidence": number },
    "unbranded_video_tour_url": { "value": string | null, "confidence": number }
  }
}"""


def _flatten_vision_response(extracted_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Flatten the nested vision API response structure.
    Converts from {section: {field: {value, confidence}}} to {section.field: {value, confidence}}.
    
    Args:
        extracted_data: Nested JSON response from vision API
        
    Returns:
        Dictionary mapping field_path -> {value, confidence}
    """
    flattened = {}
    
    for section_name, section_data in extracted_data.items():
        if not isinstance(section_data, dict):
            continue
        
        for field_name, field_data in section_data.items():
            if isinstance(field_data, dict) and "value" in field_data:
                field_path = f"{section_name}.{field_name}"
                flattened[field_path] = {
                    "value": field_data.get("value"),
                    "confidence": field_data.get("confidence", 0.5)
                }
    
    return flattened

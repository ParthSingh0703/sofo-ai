"""
Image-based material extraction service.
Extracts flooring, roof, construction material, and horse amenities from property photos.
"""
import os
import json
import re
import base64
import io
from typing import Dict, List, Optional, Any
from uuid import UUID
from PIL import Image
from services.api.models.extraction import ExtractedField, FieldProvenance
from services.api.database import get_db


def extract_materials_from_images(listing_id: UUID) -> Dict[str, ExtractedField]:
    """
    Extract material information (flooring, roof, construction material, horse amenities)
    from property photos using AI vision analysis.
    
    Args:
        listing_id: The listing ID to get images for
        
    Returns:
        Dictionary of field_path -> ExtractedField
    """
    # Get all images for this listing
    images = _get_listing_images(listing_id)
    
    if not images:
        return {}
    
    all_extracted_fields: Dict[str, ExtractedField] = {}
    
    # Analyze each image for materials
    for image in images:
        image_id = image['id']
        storage_path = image['storage_path']
        
        # Build full file path
        storage_root = os.getenv("STORAGE_ROOT", "storage")
        file_path = os.path.join(storage_root, storage_path)
        
        if not os.path.exists(file_path):
            continue
        
        try:
            # Extract materials from this image
            image_fields = _extract_materials_from_single_image(file_path, str(image_id), listing_id)
            
            # Merge fields (combine arrays, keep highest confidence for single values)
            for field_path, field in image_fields.items():
                if field_path in all_extracted_fields:
                    # Merge logic: for arrays, combine unique values; for single values, keep higher confidence
                    existing_field = all_extracted_fields[field_path]
                    
                    # Get confidence scores (default to 0.5 if not provided)
                    field_confidence = field.provenance.confidence if field.provenance.confidence is not None else 0.3
                    existing_confidence = existing_field.provenance.confidence if existing_field.provenance.confidence is not None else 0.3
                    
                    if isinstance(field.value, list) and isinstance(existing_field.value, list):
                        # Combine arrays, remove duplicates
                        combined = list(set(existing_field.value + field.value))
                        # Use provenance from field with higher confidence
                        if field_confidence > existing_confidence:
                            all_extracted_fields[field_path] = ExtractedField(
                                value=combined,
                                provenance=field.provenance
                            )
                        else:
                            all_extracted_fields[field_path] = ExtractedField(
                                value=combined,
                                provenance=existing_field.provenance
                            )
                    elif field_confidence > existing_confidence:
                        # Replace with higher confidence value
                        all_extracted_fields[field_path] = field
                    # Otherwise, keep existing field (already in all_extracted_fields)
                else:
                    all_extracted_fields[field_path] = field
        except Exception as e:
            print(f"Error extracting materials from image {image_id}: {str(e)}")
            continue
    
    return all_extracted_fields


def _get_listing_images(listing_id: UUID) -> List[Dict[str, Any]]:
    """Get all images for a listing from database."""
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id, storage_path, original_filename
            FROM listing_images
            WHERE listing_id = %s
            ORDER BY uploaded_at ASC
            """,
            (str(listing_id),)
        )
        
        rows = cur.fetchall()
        images = []
        for row in rows:
            images.append({
                'id': row[0],
                'storage_path': row[1],
                'original_filename': row[2]
            })
        
        return images


def _extract_materials_from_single_image(image_path: str, image_id: str, listing_id: UUID) -> Dict[str, ExtractedField]:
    """
    Extract material information from a single property photo.
    
    Returns:
        Dictionary of field_path -> ExtractedField
    """
    vision_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VISION_API_KEY")
    vision_model = os.getenv("IMAGE_VISION_MODEL", "gemini-2.5-flash")
    
    if not vision_api_key:
        return {}
    
    try:
        import google.genai as genai
        
        # Create Gemini client
        client = genai.Client(api_key=vision_api_key)
        model_name = vision_model if vision_model else "gemini-2.5-flash"
        
        # Read and encode image
        with open(image_path, 'rb') as img_file:
            image_bytes = img_file.read()
        
        # Determine MIME type from file extension
        img_ext = os.path.splitext(image_path)[1].lower()
        mime_type = "image/jpeg"
        if img_ext in ['.png']:
            mime_type = "image/png"
        elif img_ext in ['.gif']:
            mime_type = "image/gif"
        elif img_ext in ['.webp']:
            mime_type = "image/webp"
        
        # Convert to base64
        img_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Get extraction prompt
        prompt = _get_material_extraction_prompt()
        
        # Call Gemini API
        response = client.models.generate_content(
            model=model_name,
            contents=[
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": img_base64}}
                ]}
            ]
        )
        
        # Parse response
        response_text = response.text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if json_match:
            extracted_data = json.loads(json_match.group())
            return _convert_material_response_to_fields(extracted_data, image_id, listing_id)
        else:
            return {}
    
    except Exception as e:
        print(f"Error extracting materials from image: {str(e)}")
        return {}


def _get_material_extraction_prompt() -> str:
    """Get prompt for material extraction from property photos."""
    return """Analyze this property photo and extract material information.

CRITICAL RULES:
- ONLY extract information that is CLEARLY VISIBLE in the image
- DO NOT guess, infer, or fabricate materials that are not clearly visible
- If a material is not visible or ambiguous, return empty array []
- Follow the same extraction rules as document text extraction
- This data will be merged with text extraction results

EXTRACTION INSTRUCTIONS:

FLOORING MATERIAL (features.flooring):
- Identify visible flooring materials in interior photos
- Common types: Hardwood, Tile, Carpet, Laminate, Vinyl, Concrete, Marble, Granite, Bamboo, etc.
- Only extract if clearly visible and identifiable in the image
- Return as array of strings (e.g., ["Hardwood", "Tile"])
- If not visible or ambiguous, return empty array []

ROOF MATERIAL (property.roof):
- Identify roof material from exterior photos showing the roof
- Common types: Composition Shingle, Metal, Tile, Slate, Wood Shake, Asphalt, etc.
- Only extract from exterior photos where the roof is clearly visible
- Return as array of strings (e.g., ["Composition Shingle"])
- If roof is not visible or ambiguous, return empty array []

CONSTRUCTION MATERIAL (property.construction_material):
- Identify visible exterior construction/building materials
- Common types: Brick, Stucco, Wood, Stone, Siding, Concrete, Vinyl Siding, etc.
- Only extract if clearly visible in exterior photos
- Return as array of strings (e.g., ["Brick", "Stucco"])
- If not visible or ambiguous, return empty array []

HORSE AMENITIES (features.horse_amenities):
- Look for horse-related features: barns, stables, paddocks, horse trails, riding arenas, corrals, etc.
- Determine if this is an URBAN/CITY property:
  * Urban/City indicators: Dense housing, city setting, urban neighborhood, close proximity to other houses, city streets, no rural/open space
  * If URBAN/CITY → set is_urban_city to true and return empty array [] for horse_amenities
  * If RURAL/SUBURBAN with open space → set is_urban_city to false and extract visible horse amenities
- Only extract if horse amenities are clearly visible in the image
- Return as array of strings (e.g., ["Barn", "Stable", "Paddock"])
- If not visible or property is urban/city, return empty array []

OUTPUT FORMAT:
Return a JSON object:
{
  "flooring": ["Hardwood", "Tile"] or [],
  "roof": ["Composition Shingle"] or [],
  "construction_material": ["Brick", "Stucco"] or [],
  "horse_amenities": ["Barn", "Stable"] or [],
  "is_urban_city": boolean
}

IMPORTANT:
- If is_urban_city is true, horse_amenities MUST be empty array []
- Only include materials that are clearly visible and identifiable
- Do not guess or infer materials
"""


def _convert_material_response_to_fields(
    extracted_data: Dict[str, Any],
    image_id: str,
    listing_id: UUID
) -> Dict[str, ExtractedField]:
    """Convert AI response to ExtractedField format."""
    fields = {}
    
    # Extract flooring
    flooring = extracted_data.get("flooring", [])
    if flooring and isinstance(flooring, list):
        fields["features.flooring"] = ExtractedField(
            value=flooring,
            provenance=FieldProvenance(
                file_id=image_id,
                page_number=0,
                source_type="vision"
            )
        )
    
    # Extract roof
    roof = extracted_data.get("roof", [])
    if roof and isinstance(roof, list):
        fields["property.roof"] = ExtractedField(
            value=roof,
            provenance=FieldProvenance(
                file_id=image_id,
                page_number=0,
                source_type="vision"
            )
        )
    
    # Extract construction material
    construction_material = extracted_data.get("construction_material", [])
    if construction_material and isinstance(construction_material, list):
        fields["property.construction_material"] = ExtractedField(
            value=construction_material,
            provenance=FieldProvenance(
                file_id=image_id,
                page_number=0,
                source_type="vision"
            )
        )
    
    # Extract horse amenities (only if not urban/city)
    is_urban_city = extracted_data.get("is_urban_city", False)
    horse_amenities = extracted_data.get("horse_amenities", [])
    
    if is_urban_city:
        # Set to empty array for urban/city properties
        fields["features.horse_amenities"] = ExtractedField(
            value=[],
            provenance=FieldProvenance(
                file_id=image_id,
                page_number=0,
                source_type="vision"
            )
        )
    elif horse_amenities and isinstance(horse_amenities, list):
        fields["features.horse_amenities"] = ExtractedField(
            value=horse_amenities,
            provenance=FieldProvenance(
                file_id=image_id,
                page_number=0,
                source_type="vision"
            )
        )
    
    return fields

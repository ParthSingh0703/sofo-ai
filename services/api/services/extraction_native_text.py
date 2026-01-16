"""
Native text-based extraction service.
Extracts structured data from native text using deterministic + LLM-assisted parsing.
"""
import os
import re
from typing import Dict, Any, Optional
from services.api.models.extraction import ExtractedField, FieldProvenance, DocumentExtractionResult
from services.api.services.text_extraction_utils import extract_native_text
from services.api.services.text_quality_scorer import calculate_text_quality_score


def extract_with_native_text(
    file_path: str,
    file_id: str,
    file_extension: str,
    use_llm_assisted: bool = True
) -> DocumentExtractionResult:
    """
    Extract data from document using native text extraction.
    
    Args:
        file_path: Path to document file
        file_id: Document UUID
        file_extension: File extension (e.g., '.pdf')
        use_llm_assisted: Whether to use LLM for structured extraction
        
    Returns:
        DocumentExtractionResult with extracted fields and provenance
    """
    # Extract native text
    full_text, page_texts = extract_native_text(file_path, file_extension)
    
    # Calculate quality score
    quality_score = calculate_text_quality_score(full_text)
    
    # Store page texts in database for later reference
    _store_page_texts(file_id, page_texts)
    
    # Extract structured data
    if use_llm_assisted:
        extracted_fields = _extract_with_llm(full_text, file_id, page_texts)
    else:
        extracted_fields = _extract_deterministic(full_text, file_id, page_texts)
    
    return DocumentExtractionResult(
        document_id=file_id,
        extraction_method="native_text",
        text_quality_score=quality_score,
        extracted_fields=extracted_fields,
        raw_text=full_text,
        page_texts=page_texts
    )


def _store_page_texts(file_id: str, page_texts: dict[int, str]) -> None:
    """
    Store extracted page texts in document_pages table.
    """
    from services.api.database import get_db
    
    with get_db() as (conn, cur):
        for page_number, text in page_texts.items():
            cur.execute(
                """
                INSERT INTO document_pages (document_id, page_number, extracted_text)
                VALUES (%s, %s, %s)
                ON CONFLICT (document_id, page_number)
                DO UPDATE SET extracted_text = EXCLUDED.extracted_text;
                """,
                (file_id, page_number, text)
            )


def _extract_deterministic(text: str, file_id: str, page_texts: dict[int, str]) -> Dict[str, ExtractedField]:
    """
    Deterministic extraction using regex patterns.
    Basic pattern matching for common MLS fields.
    """
    extracted_fields = {}
    text_lower = text.lower()
    
    # Extract address patterns
    address_patterns = [
        (r'\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct)', 'location.street_address', 1),
        (r'(?i)(?:city|town)[\s:]+([A-Za-z\s]+)', 'location.city', 1),
        (r'(?i)(?:state)[\s:]+([A-Z]{2})', 'location.state', 1),
        (r'\b(\d{5}(?:-\d{4})?)\b', 'location.zip_code', 1),
    ]
    
    for pattern, field_path, group_num in address_patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(group_num) if group_num else match.group(0)
            if value:
                extracted_fields[field_path] = ExtractedField(
                    value=value.strip(),
                    provenance=FieldProvenance(
                        file_id=file_id,
                        page_number=_find_page_number(text, match.start(), page_texts),
                        source_type="text"
                    )
                )
    
    # Extract price
    price_pattern = r'(?i)(?:price|list\s*price|asking)[\s:$]*(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
    price_match = re.search(price_pattern, text)
    if price_match:
        price_str = re.sub(r'[^\d.]', '', price_match.group(1))
        if price_str:
            extracted_fields['listing_meta.list_price'] = ExtractedField(
                value=float(price_str),
                provenance=FieldProvenance(
                    file_id=file_id,
                    page_number=_find_page_number(text, price_match.start(), page_texts),
                    source_type="text"
                )
            )
    
    # Extract bedrooms/bathrooms
    bed_pattern = r'(?i)(?:bedrooms?|beds?)[\s:]+(\d+)'
    bed_match = re.search(bed_pattern, text)
    if bed_match:
        extracted_fields['property.main_level_bedrooms'] = ExtractedField(
            value=int(bed_match.group(1)),
            provenance=FieldProvenance(
                file_id=file_id,
                page_number=_find_page_number(text, bed_match.start(), page_texts),
                source_type="text"
            )
        )
    
    # Extract square footage
    sqft_pattern = r'(?i)(?:square\s*feet|sqft?|sq\s*ft)[\s:]+(\d{1,3}(?:,\d{3})*)'
    sqft_match = re.search(sqft_pattern, text)
    if sqft_match:
        sqft_str = re.sub(r'[^\d]', '', sqft_match.group(1))
        if sqft_str:
            extracted_fields['property.living_area_sqft'] = ExtractedField(
                value=int(sqft_str),
                provenance=FieldProvenance(
                    file_id=file_id,
                    page_number=_find_page_number(text, sqft_match.start(), page_texts),
                    source_type="text"
                )
            )
    
    return extracted_fields


def _extract_with_llm(text: str, file_id: str, page_texts: dict[int, str]) -> Dict[str, ExtractedField]:
    """
    LLM-assisted structured extraction.
    Uses Groq LLM to parse text and extract structured fields according to canonical schema.
    """
    llm_api_key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
    llm_model = os.getenv("LLM_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    
    if not llm_api_key:
        # Fallback to deterministic extraction
        return _extract_deterministic(text, file_id, page_texts)
    
    try:
        from groq import Groq
        client = Groq(api_key=llm_api_key)
        
        prompt = f"""Extract structured real estate listing information from the following text.

Extract fields matching the canonical listing schema:
- location (street_address, city, state, zip_code)
- listing_meta (list_price)
- property (main_level_bedrooms, bathrooms_full, living_area_sqft, year_built, property_sub_type)

Rules:
- Only extract information that is clearly present in the text
- Return null for missing fields
- Return JSON with field paths like "location.street_address"

Text to extract from:
{text[:5000]}  # Limit text length

Return JSON object with extracted fields:
{{
  "location.street_address": "value or null",
  "location.city": "value or null",
  "location.state": "value or null",
  "location.zip_code": "value or null",
  "listing_meta.list_price": number or null,
  "property.main_level_bedrooms": number or null,
  "property.bathrooms_full": number or null,
  "property.living_area_sqft": number or null,
  "property.year_built": number or null,
  "property.property_sub_type": "value or null"
}}"""
        
        response = client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": "You are a real estate data extraction system. Extract structured fields from listing text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.1
        )
        
        response_text = response.choices[0].message.content
        
        # Parse JSON from response
        import json
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            extracted_data = json.loads(json_match.group())
            
            # Convert to ExtractedField format
            extracted_fields = {}
            for field_path, value in extracted_data.items():
                if value is not None:
                    extracted_fields[field_path] = ExtractedField(
                        value=value,
                        provenance=FieldProvenance(
                            file_id=file_id,
                            page_number=_find_page_number(text, 0, page_texts),  # Approximate
                            source_type="text"
                        )
                    )
            
            # Merge with deterministic extraction (deterministic takes precedence for accuracy)
            deterministic_fields = _extract_deterministic(text, file_id, page_texts)
            deterministic_fields.update(extracted_fields)  # LLM fields fill in gaps
            
            return deterministic_fields
        else:
            # Fallback to deterministic
            return _extract_deterministic(text, file_id, page_texts)
    
    except ImportError:
        print("Groq library not installed. Using deterministic extraction.")
        return _extract_deterministic(text, file_id, page_texts)
    except Exception as e:
        print(f"LLM extraction failed: {str(e)}. Using deterministic extraction.")
        return _extract_deterministic(text, file_id, page_texts)
    
    # # OpenAI implementation (commented for testing with Groq)
    # # This would call an LLM API (OpenAI, Anthropic, etc.)
    # # For now, we'll use deterministic extraction as fallback
    # # TODO: Implement actual LLM call when API key is configured
    # 
    # llm_enabled = os.getenv("LLM_API_KEY") is not None
    # 
    # if llm_enabled:
    #     # TODO: Implement actual LLM extraction
    #     # For now, return deterministic extraction
    #     pass
    # 
    # return _extract_deterministic(text, file_id, page_texts)


def _find_page_number(full_text: str, char_position: int, page_texts: dict[int, str]) -> Optional[int]:
    """
    Find which page a character position belongs to.
    """
    current_pos = 0
    for page_num in sorted(page_texts.keys()):
        page_text = page_texts[page_num]
        current_pos += len(page_text) + 1  # +1 for newline
        if char_position < current_pos:
            return page_num
    return 1  # Default to first page

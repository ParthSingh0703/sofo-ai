"""
Main extraction pipeline that orchestrates AI-based document extraction.
All extraction is now AI-only using Gemini models.
Supports parallel document processing for improved performance.
"""
import os
import json
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.api.models.extraction import (
    ExtractionConfig,
    DocumentExtractionResult,
    ExtractedField,
    FieldProvenance
)
from services.api.models.canonical import CanonicalListing
from services.api.services.extraction_ai import extract_with_ai
from services.api.services.extraction_image_materials import extract_materials_from_images
from services.api.database import get_db


def extract_listing_from_documents(
    listing_id: UUID,
    config: ExtractionConfig = None
) -> CanonicalListing:
    """
    Main AI-based extraction pipeline with parallel document processing.
    Extracts data from all documents for a listing using Gemini models.
    
    Process:
    1. FIRST: Extract from documents in parallel using text extraction (Gemini 2.5 Flash)
       - Documents are processed concurrently (up to 5 workers by default)
       - Each document extraction runs independently
       - Results are merged thread-safely
    2. THEN: Extract materials from property photos (flooring, roof, construction material, horse amenities) using Gemini 2.5 Flash
    3. Merge results: Image extraction fills null fields or overrides when confidence is higher
    4. Merge extracted fields into canonical listing
    5. Preserve user edits from existing canonical
    
    Future Enhancement:
    - Document-specific agents will be implemented to extract specialized information
      from different document types (e.g., listing agreements, tax documents, etc.)
    - Each agent will have domain-specific extraction logic while maintaining
      the same parallel processing architecture
    
    Args:
        listing_id: The listing ID to extract data for
        config: Extraction configuration (currently unused, kept for compatibility)
        
    Returns:
        CanonicalListing with extracted fields and provenance
    """
    if config is None:
        config = ExtractionConfig()
    
    # STEP 1: Get all documents for this listing
    documents = _get_listing_documents(listing_id)
    
    if not documents:
        print(f"No documents found for listing {listing_id}")
        # Still proceed with image extraction
        all_extracted_fields: Dict[str, ExtractedField] = {}
    else:
        # STEP 2: Extract from documents in parallel using AI (text extraction FIRST)
        print(f"Processing {len(documents)} document(s) in parallel (max_workers=5)...")
        import time
        start_time = time.time()
        all_extracted_fields = _extract_documents_parallel(documents)
        elapsed_time = time.time() - start_time
        print(f"✓ Completed extraction from {len(documents)} document(s) in {elapsed_time:.2f} seconds")
        print(f"  Extracted {len(all_extracted_fields)} unique field(s)")
    
    # STEP 3: Extract materials from property photos (image analysis)
    # Only extract if material information is NOT already present in document extraction
    material_field_paths = [
        "features.flooring",
        "property.roof",
        "property.construction_material",
        "features.horse_amenities"
    ]
    
    # Check if any material fields are missing or empty from document extraction
    needs_image_extraction = False
    missing_material_fields = []
    
    for field_path in material_field_paths:
        if field_path not in all_extracted_fields:
            # Field not extracted from documents
            needs_image_extraction = True
            missing_material_fields.append(field_path)
        else:
            # Field exists, check if it's null/empty
            text_field = all_extracted_fields[field_path]
            text_value = text_field.value
            if text_value is None or text_value == [] or text_value == "":
                # Field is empty, need image extraction
                needs_image_extraction = True
                missing_material_fields.append(field_path)
    
    if needs_image_extraction:
        print(f"Material fields missing from documents: {missing_material_fields}")
        print("Extracting materials from property photos...")
        try:
            image_material_fields = extract_materials_from_images(listing_id)
            print(f"Extracted materials from {len(image_material_fields)} image fields")
            
            # Merge image-extracted fields with text-extracted fields
            # Only add fields that were missing from document extraction
            for field_path, image_field in image_material_fields.items():
                if field_path in missing_material_fields:
                    # This field was missing from documents, use image extraction
                    all_extracted_fields[field_path] = image_field
                elif field_path in all_extracted_fields:
                    # Field exists in both, but document extraction already has it
                    # Skip image extraction for this field (document extraction takes precedence)
                    print(f"Skipping image extraction for {field_path} - already present in documents")
                else:
                    # Field not in missing list but extracted from images, add it
                    all_extracted_fields[field_path] = image_field
        except Exception as e:
            print(f"Error extracting materials from images: {str(e)}")
            # Continue even if image extraction fails
    else:
        print("All material fields already present in document extraction - skipping image material extraction")
    
    if not all_extracted_fields:
        # Return empty canonical if no fields extracted
        return CanonicalListing()
    
    # Get existing canonical (if any) to preserve user edits
    from services.api.services.canonical_service import get_canonical
    existing_canonical = get_canonical(listing_id)
    
    # Build canonical listing from extracted fields
    canonical = _build_canonical_from_fields(all_extracted_fields, existing_canonical)
    
    return canonical


def _extract_single_document(document: Dict[str, Any]) -> Optional[Dict[str, ExtractedField]]:
    """
    Extract data from a single document.
    This function is designed to be called in parallel.
    
    Currently uses general extraction (extract_with_ai) for all document types.
    In the future, this will route to document-specific agents:
    - Listing Agreement Agent: Extracts listing agreement details, intermediary status, etc.
    - Tax Document Agent: Extracts tax information, assessed values, exemptions, etc.
    - Property Info Sheet Agent: Extracts property details, features, utilities, etc.
    - Disclosure Agent: Extracts disclosure information, special conditions, etc.
    
    Args:
        document: Dictionary with 'id', 'filename', 'storage_path'
        
    Returns:
        Dictionary of field_path -> ExtractedField, or None if extraction fails
    """
    document_id = document['id']
    storage_path = document['storage_path']
    filename = document['filename']
    
    try:
        # Build full file path
        storage_root = os.getenv("STORAGE_ROOT", "storage")
        file_path = os.path.join(storage_root, storage_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Warning: Document file not found: {file_path}")
            return None
        
        # Get file extension
        file_extension = os.path.splitext(filename)[1]
        
        # Extract using AI (handles both text and images from documents)
        extraction_result = extract_with_ai(
            file_path=file_path,
            file_id=str(document_id),
            file_extension=file_extension
        )
        
        # Return extracted fields as dictionary
        return extraction_result.extracted_fields
        
    except Exception as e:
        print(f"Error extracting from document {document_id} ({filename}): {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def _extract_documents_parallel(documents: List[Dict[str, Any]], max_workers: int = 5) -> Dict[str, ExtractedField]:
    """
    Extract data from multiple documents in parallel.
    
    Args:
        documents: List of document dictionaries
        max_workers: Maximum number of parallel workers (default: 5)
        
    Returns:
        Dictionary of field_path -> ExtractedField with merged results
    """
    all_extracted_fields: Dict[str, ExtractedField] = {}
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all extraction tasks
        future_to_document = {
            executor.submit(_extract_single_document, document): document
            for document in documents
        }
        
        # Process results as they complete
        for future in as_completed(future_to_document):
            document = future_to_document[future]
            document_id = document['id']
            filename = document['filename']
            
            try:
                extracted_fields = future.result()
                
                if extracted_fields:
                    # Merge extracted fields into all_extracted_fields
                    for field_path, field in extracted_fields.items():
                        if field_path not in all_extracted_fields:
                            # Field doesn't exist yet, add it
                            all_extracted_fields[field_path] = field
                        else:
                            # Field already exists, merge based on type
                            existing_field = all_extracted_fields[field_path]
                            _merge_extracted_field(
                                all_extracted_fields, 
                                field_path, 
                                existing_field, 
                                field
                            )
                    print(f"✓ Successfully extracted from document {document_id} ({filename})")
                else:
                    print(f"⚠ No fields extracted from document {document_id} ({filename})")
                    
            except Exception as e:
                print(f"✗ Error processing extraction result for document {document_id} ({filename}): {str(e)}")
                continue
    
    return all_extracted_fields


def _merge_extracted_field(
    all_extracted_fields: Dict[str, ExtractedField],
    field_path: str,
    existing_field: ExtractedField,
    new_field: ExtractedField
) -> None:
    """
    Merge a new extracted field with an existing field.
    
    Merging rules:
    1. If both are arrays, combine unique values
    2. If existing is empty/null, use new field
    3. If both have values, prefer higher confidence
    4. For non-arrays, prefer non-empty values
    
    Args:
        all_extracted_fields: Dictionary to update
        field_path: Path of the field being merged
        existing_field: Existing ExtractedField
        new_field: New ExtractedField to merge
    """
    existing_value = existing_field.value
    new_value = new_field.value
    
    # Get confidence scores (default to 0.5 if not provided)
    existing_confidence = existing_field.provenance.confidence if existing_field.provenance.confidence is not None else 0.5
    new_confidence = new_field.provenance.confidence if new_field.provenance.confidence is not None else 0.5
    
    # Case 1: Both are arrays - merge unique values
    if isinstance(existing_value, list) and isinstance(new_value, list):
        combined = list(set(existing_value + new_value))
        # Use provenance from field with higher confidence
        if new_confidence > existing_confidence:
            all_extracted_fields[field_path] = ExtractedField(
                value=combined,
                provenance=new_field.provenance
            )
        else:
            all_extracted_fields[field_path] = ExtractedField(
                value=combined,
                provenance=existing_field.provenance
            )
    
    # Case 2: Existing field is empty/null - use new field
    elif existing_value is None or existing_value == [] or existing_value == "":
        all_extracted_fields[field_path] = new_field
    
    # Case 3: New field is empty/null - keep existing
    elif new_value is None or new_value == [] or new_value == "":
        # Keep existing field, no change needed
        pass
    
    # Case 4: Both have values - prefer higher confidence
    elif new_confidence > existing_confidence:
        all_extracted_fields[field_path] = new_field
    
    # Case 5: Existing has higher confidence - keep existing
    else:
        # Keep existing field, no change needed
        pass


def _get_listing_documents(listing_id: UUID) -> List[Dict[str, Any]]:
    """
    Get all documents for a listing from database.
    """
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id, filename, storage_path
            FROM documents
            WHERE listing_id = %s
            ORDER BY uploaded_at ASC
            """,
            (str(listing_id),)
        )
        
        documents = []
        for row in cur.fetchall():
            documents.append({
                'id': row[0],
                'filename': row[1],
                'storage_path': row[2]
            })
        
        return documents


# _extract_document() function removed - now using extract_with_ai() directly


def _parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Parse a date string into a datetime object.
    Handles common date formats used in MLS documents.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    # Common date formats to try (US format prioritized)
    date_formats = [
        "%m/%d/%Y",            # 04/02/2026 (US format - most common in MLS documents)
        "%m/%d/%y",             # 04/02/26 (US format with 2-digit year)
        "%m-%d-%Y",             # 04-02-2026 (US format with dashes)
        "%m-%d-%y",             # 04-02-26 (US format with dashes, 2-digit year)
        "%Y-%m-%d",             # 2026-04-02 (ISO format)
        "%Y/%m/%d",             # 2026/04/02
        "%B %d, %Y",            # April 2, 2026
        "%b %d, %Y",            # Apr 2, 2026
        "%d %B %Y",             # 2 April 2026
        "%d %b %Y",             # 2 Apr 2026
    ]
    
    # Try parsing with specific formats first
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    # Try ISO format and other common formats
    try:
        # Try ISO format (2026-04-02T00:00:00 or 2026-04-02)
        if 'T' in date_str:
            return datetime.fromisoformat(date_str.strip().replace('Z', '+00:00'))
        else:
            # Try just the date part
            return datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except (ValueError, TypeError):
        # If all parsing fails, return None
        return None


def _build_canonical_from_fields(
    extracted_fields: Dict[str, ExtractedField],
    existing_canonical: Optional[CanonicalListing] = None
) -> CanonicalListing:
    """
    Build a CanonicalListing from extracted fields with provenance.
    
    Merging rules:
    - Vision-extracted fields override empty text-extracted fields
    - Never override user-edited fields (fields that already have values in existing_canonical)
    - Mark provenance.source_type = "vision" for vision-extracted fields
    
    Args:
        extracted_fields: Dictionary of field_path -> ExtractedField
        existing_canonical: Existing canonical listing (if any) to preserve user edits
        
    Returns:
        CanonicalListing with merged extracted fields
    """
    # Start with existing canonical or create new one
    if existing_canonical:
        canonical = existing_canonical
    else:
        canonical = CanonicalListing()
    
    # Map extracted fields to canonical structure
    for field_path, extracted_field in extracted_fields.items():
        value = extracted_field.value
        provenance = extracted_field.provenance
        
        # Skip null values
        if value is None:
            continue
        
        # Parse field path (e.g., "location.street_address")
        parts = field_path.split('.')
        
        if len(parts) != 2:
            # Skip fields with invalid path structure (should be "section.field")
            print(f"Warning: Invalid field path format '{field_path}'. Expected format: 'section.field'")
            continue
        
        section, field = parts
        try:
            section_obj = getattr(canonical, section, None)
            if not section_obj:
                print(f"Warning: Section '{section}' not found in canonical model for field '{field_path}'")
                continue
            
            if not hasattr(section_obj, field):
                print(f"Warning: Field '{field}' not found in section '{section}' for field path '{field_path}'")
                continue
            
            # Check if field already has a value (user-edited)
            existing_value = getattr(section_obj, field, None)
            
            # Parse date fields if value is a string
            if field == "expiration_date" and isinstance(value, str):
                value = _parse_date_string(value)
                if value is None:
                    print(f"Warning: Failed to parse expiration_date value: {extracted_field.value}")
                    continue
            
            # Merging logic:
            # - If field is empty/None, set the extracted value
            # - For arrays: merge unique values if both existing and new are arrays
            # - If field has value and it's not from user edit, allow override
            #   (We can't distinguish user edits vs previous extraction, so we allow override)
            if existing_value is None or existing_value == [] or existing_value == "":
                setattr(section_obj, field, value)
            elif isinstance(existing_value, list) and isinstance(value, list):
                # Merge arrays: combine unique values
                combined = list(set(existing_value + value))
                setattr(section_obj, field, combined)
            elif provenance.source_type == "vision" and existing_value is None:
                # Vision overrides empty fields
                setattr(section_obj, field, value)
        except Exception as e:
            # Log error but continue with other fields
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error setting field {field_path}: {error_trace}")
            continue
    
    return canonical


def save_extraction_results(
    listing_id: UUID,
    extraction_results: List[DocumentExtractionResult]
) -> None:
    """
    Save extraction results to extracted_field_facts table for tracking.
    """
    with get_db() as (conn, cur):
        for result in extraction_results:
            for field_path, extracted_field in result.extracted_fields.items():
                provenance = extracted_field.provenance
                
                cur.execute(
                    """
                    INSERT INTO extracted_field_facts (
                        listing_id,
                        canonical_path,
                        extracted_value,
                        source_type,
                        source_ref,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, 'proposed')
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        str(listing_id),
                        field_path,
                        json.dumps(extracted_field.value),
                        provenance.source_type,
                        f"{provenance.file_id}:page_{provenance.page_number or 1}"
                    )
                )

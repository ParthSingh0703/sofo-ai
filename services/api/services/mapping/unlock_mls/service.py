"""
Unlock MLS service - Main orchestration.
Combines mapping, transformation, and validation.
"""
from typing import Dict, Any
from services.api.models.canonical import CanonicalListing
from services.api.services.mapping.unlock_mls.mapping import get_all_mappings
from services.api.services.mapping.unlock_mls.transformer import transform_canonical_to_mls
from services.api.services.mapping.unlock_mls.validator import validate_mls_fields


def prepare_mls_fields(canonical: CanonicalListing) -> Dict[str, Any]:
    """
    Complete pipeline: Map, transform, and validate canonical listing for Unlock MLS.
    
    Args:
        canonical: The canonical listing to prepare
        
    Returns:
        Dictionary with:
        - field_mappings: Field mapping configuration
        - transformed_fields: Transformed MLS-ready fields
        - validation_result: Validation results
        - ready_for_autofill: Final readiness status
    """
    try:
        # Step 1: Get field mappings
        field_mappings = get_all_mappings()
        
        # Step 2: Transform canonical to MLS format
        transform_result = transform_canonical_to_mls(canonical)
        
        # Step 3: Validate transformed fields
        validation_result = validate_mls_fields(transform_result["unlock_mls_ready_fields"])
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in prepare_mls_fields: {error_trace}")
        raise
    
    return {
        "field_mappings": {
            section: {
                field_name: {
                    "canonical_path": mapping.canonical_path or "default",
                    "confidence": mapping.confidence,
                    "type": mapping.type
                }
                for field_name, mapping in fields.items()
            }
            for section, fields in field_mappings.items()
        },
        "transformed_fields": transform_result["unlock_mls_ready_fields"],
        "unmapped_required_fields": transform_result["unmapped_required_fields"],
        "mapping_notes": transform_result["mapping_notes"],
        "validation": validation_result,
        "ready_for_autofill": validation_result["ready_for_autofill"]
    }

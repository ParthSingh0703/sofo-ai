"""
Unlock MLS data transformation service.
Transforms CanonicalListing data to Unlock MLS-ready format.
"""
from typing import Dict, Any, List, Optional
from services.api.models.canonical import CanonicalListing
from services.api.services.mapping.unlock_mls.mapping import get_field_mapping, get_all_mappings, MLSFieldMapping


def transform_canonical_to_mls(canonical: CanonicalListing) -> Dict[str, Any]:
    """
    Transform CanonicalListing to Unlock MLS-ready fields.
    
    Args:
        canonical: The canonical listing to transform
        
    Returns:
        Dictionary with:
        - unlock_mls_ready_fields: Transformed field values
        - unmapped_required_fields: Fields that couldn't be mapped
        - mapping_notes: Notes about transformations
    """
    canonical_dict = canonical.model_dump()
    all_mappings = get_all_mappings()
    
    unlock_mls_fields = {}
    unmapped_required = []
    mapping_notes = []
    
    for section, fields in all_mappings.items():
        for mls_field_name, mapping in fields.items():
            value = None
            
            # Get value from canonical
            if mapping.canonical_path:
                value = _get_nested_value(canonical_dict, mapping.canonical_path)
            
            # Apply default if value is None
            if value is None and mapping.default_value is not None:
                value = mapping.default_value
                mapping_notes.append({
                    "mls_field": mls_field_name,
                    "canonical_source": mapping.canonical_path or "default",
                    "action": "used_default",
                    "confidence": mapping.confidence
                })
            
            # Transform value if needed
            if value is not None and mapping.transform_fn:
                original_value = value
                value = _apply_transform(value, mapping.transform_fn, canonical_dict)
                if value != original_value:
                    mapping_notes.append({
                        "mls_field": mls_field_name,
                        "canonical_source": mapping.canonical_path,
                        "action": "transformed",
                        "confidence": mapping.confidence * 0.9
                    })
            
            # Type conversion and validation
            if value is not None:
                value = _convert_type(value, mapping.type)
            
            # Only include non-null values (except for required fields with defaults)
            if value is not None or mapping.default_value is not None:
                unlock_mls_fields[mls_field_name] = value
            elif mapping.canonical_path:  # Field was expected but not found
                unmapped_required.append(mls_field_name)
    
    return {
        "unlock_mls_ready_fields": unlock_mls_fields,
        "unmapped_required_fields": unmapped_required,
        "mapping_notes": mapping_notes
    }


def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """Get value from nested dictionary using dot notation."""
    if not path:
        return None
    
    keys = path.split(".")
    value = data
    
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
        
        if value is None:
            return None
    
    return value


def _apply_transform(value: Any, transform_name: str, canonical_dict: Dict[str, Any]) -> Any:
    """Apply transformation function to value."""
    if transform_name == "format_date":
        # Date is already formatted by serializer, but ensure it's string
        return str(value) if value else None
    
    elif transform_name == "zip_to_number":
        # Convert zip code string to number
        if isinstance(value, str):
            # Remove non-numeric characters
            zip_clean = ''.join(filter(str.isdigit, value))
            if zip_clean:
                return int(zip_clean[:5])  # Take first 5 digits
        return int(value) if value else None
    
    elif transform_name == "string_to_number":
        # Convert string to number
        if isinstance(value, str):
            # Try to extract number from string
            import re
            numbers = re.findall(r'\d+', value)
            if numbers:
                return int(numbers[0])
        return int(value) if value else None
    
    elif transform_name == "string_to_multi_enum":
        # Convert string to list of enum values
        if isinstance(value, str):
            # Split by common delimiters
            values = [v.strip() for v in value.replace(';', ',').split(',')]
            return [v for v in values if v]
        return value if isinstance(value, list) else [value] if value else []
    
    elif transform_name == "count_fireplaces":
        # Count fireplaces from list
        if isinstance(value, list):
            return len(value)
        elif isinstance(value, str):
            # Try to extract number
            import re
            numbers = re.findall(r'\d+', value)
            return int(numbers[0]) if numbers else 0
        return int(value) if value else 0
    
    elif transform_name == "infer_ownership_type":
        # Infer ownership type from property sub type
        property_sub_type = _get_nested_value(canonical_dict, "property.property_sub_type")
        if property_sub_type:
            sub_type_lower = str(property_sub_type).lower()
            if "single family" in sub_type_lower or "residential" in sub_type_lower:
                return "Fee Simple"
            elif "condo" in sub_type_lower or "condominium" in sub_type_lower:
                return "Common"
        return value
    
    return value


def _convert_type(value: Any, target_type: str) -> Any:
    """Convert value to target type."""
    if value is None:
        return None
    
    if target_type == "string":
        return str(value)
    elif target_type == "number":
        if isinstance(value, (int, float)):
            return value
        try:
            return float(value) if '.' in str(value) else int(value)
        except (ValueError, TypeError):
            return None
    elif target_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("yes", "true", "1", "y")
        return bool(value)
    elif target_type == "enum":
        return str(value) if value else None
    elif target_type == "multi_enum":
        if isinstance(value, list):
            return [str(v) for v in value if v]
        elif value:
            return [str(value)]
        return []
    
    return value

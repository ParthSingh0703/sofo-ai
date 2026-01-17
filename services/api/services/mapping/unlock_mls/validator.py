"""
Unlock MLS field validation service.
Validates MLS-ready fields before browser automation.
"""
from typing import Dict, Any, List, Optional
from services.api.services.mapping.unlock_mls.mapping import get_all_mappings


def validate_mls_fields(mls_fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Unlock MLS fields before browser automation.
    
    Args:
        mls_fields: Dictionary of MLS field names to values
        
    Returns:
        Dictionary with:
        - ready_for_autofill: Boolean indicating if ready
        - blocking_issues: List of blocking validation errors
        - warnings: List of warnings (non-blocking)
    """
    all_mappings = get_all_mappings()
    blocking_issues = []
    warnings = []
    
    # Check required fields
    required_fields = _get_required_fields()
    for field_name in required_fields:
        if field_name not in mls_fields or mls_fields[field_name] is None:
            blocking_issues.append(f"Required field '{field_name}' is missing or null")
    
    # Validate field types and values
    for section, fields in all_mappings.items():
        for mls_field_name, mapping in fields.items():
            if mls_field_name not in mls_fields:
                continue
            
            value = mls_fields[mls_field_name]
            
            # Type validation
            type_issue = _validate_type(value, mapping.type, mls_field_name)
            if type_issue:
                blocking_issues.append(type_issue)
            
            # Enum validation
            if mapping.type in ("enum", "multi_enum") and mapping.enum_values:
                enum_issue = _validate_enum(value, mapping.enum_values, mls_field_name, mapping.type)
                if enum_issue:
                    warnings.append(enum_issue)
            
            # Field length validation
            if mapping.type == "string" and isinstance(value, str):
                if len(value) > 1000:  # Reasonable limit
                    warnings.append(f"Field '{mls_field_name}' exceeds 1000 characters")
    
    # Dependency validation
    dependency_issues = _validate_dependencies(mls_fields)
    blocking_issues.extend(dependency_issues)
    
    ready_for_autofill = len(blocking_issues) == 0
    
    return {
        "ready_for_autofill": ready_for_autofill,
        "blocking_issues": blocking_issues,
        "warnings": warnings
    }


def _get_required_fields() -> List[str]:
    """Get list of required MLS fields."""
    # These are typically required by MLS systems
    return [
        "Street Address",
        "List Price",
        "Property Sub Type",
        "City",
        "State",
        "Zip Code",
        "Country",
    ]


def _validate_type(value: Any, expected_type: str, field_name: str) -> Optional[str]:
    """Validate that value matches expected type."""
    if value is None:
        return None
    
    if expected_type == "string":
        if not isinstance(value, str):
            return f"Field '{field_name}' must be a string, got {type(value).__name__}"
    elif expected_type == "number":
        if not isinstance(value, (int, float)):
            return f"Field '{field_name}' must be a number, got {type(value).__name__}"
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            return f"Field '{field_name}' must be a boolean, got {type(value).__name__}"
    elif expected_type == "enum":
        if not isinstance(value, str):
            return f"Field '{field_name}' must be a string (enum), got {type(value).__name__}"
    elif expected_type == "multi_enum":
        if not isinstance(value, list):
            return f"Field '{field_name}' must be a list (multi_enum), got {type(value).__name__}"
        if value and not all(isinstance(v, str) for v in value):
            return f"Field '{field_name}' must be a list of strings"
    
    return None


def _validate_enum(value: Any, allowed_values: List[str], field_name: str, enum_type: str) -> Optional[str]:
    """Validate enum value against allowed values."""
    if not allowed_values:
        return None
    
    if enum_type == "enum":
        if isinstance(value, str) and value not in allowed_values:
            return f"Field '{field_name}' value '{value}' not in allowed values: {allowed_values}"
    elif enum_type == "multi_enum":
        if isinstance(value, list):
            invalid = [v for v in value if v not in allowed_values]
            if invalid:
                return f"Field '{field_name}' contains invalid values: {invalid}. Allowed: {allowed_values}"
    
    return None


def _validate_dependencies(mls_fields: Dict[str, Any]) -> List[str]:
    """Validate field dependencies."""
    issues = []
    
    # Association fields dependency
    if mls_fields.get("Association") is True:
        if not mls_fields.get("Association Name"):
            issues.append("Association Name is required when Association is Yes")
    
    # Additional Parcel dependency
    if mls_fields.get("Additional Parcel") is True:
        if not mls_fields.get("Additional Parcel Description"):
            issues.append("Additional Parcel Description is required when Additional Parcel is Yes")
    
    return issues

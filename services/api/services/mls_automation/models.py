"""
Data models for MLS automation.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class AutomationConfig(BaseModel):
    """Configuration for MLS automation."""
    listing_id: UUID
    mls_system_code: str
    mls_url: Optional[str] = None  # For new MLS discovery
    mapped_json: Dict[str, Any]  # Mapped MLS JSON
    mode: str = "SAVE_ONLY"  # Always SAVE_ONLY, never submit


class AutomationResult(BaseModel):
    """Result of MLS automation."""
    status: str  # "saved", "failed", "cancelled"
    login_skipped: bool = False
    new_mls: bool = False
    fields_filled: int = 0
    fields_skipped: int = 0
    enums_learned: int = 0
    images_updated: int = 0
    errors: List[str] = []
    warnings: List[str] = []
    screenshot_paths: List[str] = []
    completed_at: Optional[datetime] = None


class MLSFieldSelector(BaseModel):
    """Field selector configuration for an MLS."""
    label: str
    selector: Optional[str] = None  # CSS selector, XPath, or text-based
    field_type: str  # "text", "number", "dropdown", "checkbox", "radio", "multi-select", "date"
    json_key: str  # Key in mapped JSON
    field_name: Optional[str] = None  # Name attribute for radio buttons
    enum_values: Optional[List[str]] = None  # For dropdowns/selects


class MLSMappingConfig(BaseModel):
    """Stored mapping configuration for an MLS."""
    mls_system_code: str
    field_selectors: List[MLSFieldSelector]
    page_structure: Dict[str, Any]  # Page-specific selectors (buttons, sections)
    enum_mappings: Dict[str, Dict[str, str]]  # JSON value -> MLS enum value
    created_at: datetime
    updated_at: datetime

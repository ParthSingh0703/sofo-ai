"""
Learning and persistence service for MLS automation.
Stores discovered field mappings and enum translations for future use.
"""
import json
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from services.api.database import get_db
from services.api.services.mls_automation.models import MLSFieldSelector, MLSMappingConfig


def save_mls_mapping_config(
    mls_system_code: str,
    field_selectors: List[MLSFieldSelector],
    page_structure: Dict[str, Any],
    enum_mappings: Dict[str, Dict[str, str]]
) -> bool:
    """
    Save discovered/learned MLS mapping configuration.
    
    Args:
        mls_system_code: MLS system code
        field_selectors: List of discovered field selectors
        page_structure: Page-specific selectors (buttons, sections, etc.)
        enum_mappings: Learned enum translations (canonical_value -> mls_value)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db() as (conn, cur):
            # Get or create MLS system
            mls_system_id = _get_or_create_mls_system(cur, mls_system_code)
            
            # Convert field selectors to JSON
            field_selectors_json = [
                {
                    "label": fs.label,
                    "selector": fs.selector,
                    "field_type": fs.field_type,
                    "json_key": fs.json_key,
                    "field_name": fs.field_name,
                    "enum_values": fs.enum_values
                }
                for fs in field_selectors
            ]
            
            # Check if mapping config exists
            cur.execute(
                """
                SELECT id FROM mls_mapping_configs
                WHERE mls_system_id = %s
                """,
                (str(mls_system_id),)
            )
            existing = cur.fetchone()
            
            if existing:
                # Update existing
                cur.execute(
                    """
                    UPDATE mls_mapping_configs
                    SET 
                        field_selectors = %s,
                        page_structure = %s,
                        enum_mappings = %s,
                        updated_at = now()
                    WHERE mls_system_id = %s
                    """,
                    (
                        json.dumps(field_selectors_json, default=str),
                        json.dumps(page_structure, default=str),
                        json.dumps(enum_mappings, default=str),
                        str(mls_system_id)
                    )
                )
            else:
                # Insert new
                cur.execute(
                    """
                    INSERT INTO mls_mapping_configs (
                        mls_system_id,
                        field_selectors,
                        page_structure,
                        enum_mappings
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        str(mls_system_id),
                        json.dumps(field_selectors_json, default=str),
                        json.dumps(page_structure, default=str),
                        json.dumps(enum_mappings, default=str)
                    )
                )
            
            return True
    except Exception as e:
        print(f"Error saving MLS mapping config: {str(e)}")
        return False


def load_mls_mapping_config(mls_system_code: str) -> Optional[MLSMappingConfig]:
    """
    Load stored MLS mapping configuration.
    
    Args:
        mls_system_code: MLS system code
        
    Returns:
        MLSMappingConfig if found, None otherwise
    """
    try:
        with get_db() as (conn, cur):
            # Get MLS system ID
            cur.execute(
                "SELECT id FROM mls_systems WHERE code = %s AND is_active = TRUE",
                (mls_system_code,)
            )
            mls_system_row = cur.fetchone()
            
            if not mls_system_row:
                return None
            
            mls_system_id = mls_system_row[0]
            
            # Get mapping config
            cur.execute(
                """
                SELECT field_selectors, page_structure, enum_mappings, created_at, updated_at
                FROM mls_mapping_configs
                WHERE mls_system_id = %s
                """,
                (str(mls_system_id),)
            )
            
            row = cur.fetchone()
            if not row:
                return None
            
            field_selectors_json, page_structure, enum_mappings, created_at, updated_at = row
            
            # Parse JSON fields
            if isinstance(field_selectors_json, str):
                field_selectors_json = json.loads(field_selectors_json)
            if isinstance(page_structure, str):
                page_structure = json.loads(page_structure)
            if isinstance(enum_mappings, str):
                enum_mappings = json.loads(enum_mappings)
            
            # Convert to MLSFieldSelector objects
            field_selectors = [
                MLSFieldSelector(
                    label=fs["label"],
                    selector=fs.get("selector"),
                    field_type=fs["field_type"],
                    json_key=fs["json_key"],
                    field_name=fs.get("field_name"),
                    enum_values=fs.get("enum_values")
                )
                for fs in field_selectors_json
            ]
            
            return MLSMappingConfig(
                mls_system_code=mls_system_code,
                field_selectors=field_selectors,
                page_structure=page_structure or {},
                enum_mappings=enum_mappings or {},
                created_at=created_at,
                updated_at=updated_at
            )
    except Exception as e:
        print(f"Error loading MLS mapping config: {str(e)}")
        return None


def learn_enum_mapping(
    mls_system_code: str,
    field_name: str,
    canonical_value: str,
    mls_value: str
) -> bool:
    """
    Learn a new enum mapping (canonical -> MLS).
    
    Args:
        mls_system_code: MLS system code
        field_name: Field name
        canonical_value: Canonical/JSON value
        mls_value: MLS enum value
        
    Returns:
        True if successful
    """
    try:
        # Load existing config
        config = load_mls_mapping_config(mls_system_code)
        if not config:
            # Create new config with empty structures
            config = MLSMappingConfig(
                mls_system_code=mls_system_code,
                field_selectors=[],
                page_structure={},
                enum_mappings={},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        
        # Add enum mapping
        if field_name not in config.enum_mappings:
            config.enum_mappings[field_name] = {}
        
        config.enum_mappings[field_name][canonical_value] = mls_value
        
        # Save updated config
        return save_mls_mapping_config(
            mls_system_code,
            config.field_selectors,
            config.page_structure,
            config.enum_mappings
        )
    except Exception as e:
        print(f"Error learning enum mapping: {str(e)}")
        return False


def get_learned_enum_mapping(
    mls_system_code: str,
    field_name: str,
    canonical_value: str
) -> Optional[str]:
    """
    Get learned enum mapping if it exists.
    
    Args:
        mls_system_code: MLS system code
        field_name: Field name
        canonical_value: Canonical/JSON value
        
    Returns:
        MLS enum value if found, None otherwise
    """
    config = load_mls_mapping_config(mls_system_code)
    if not config:
        return None
    
    return config.enum_mappings.get(field_name, {}).get(canonical_value)


def _get_or_create_mls_system(cursor, code: str) -> UUID:
    """
    Get existing MLS system ID or create it if it doesn't exist.
    
    Args:
        cursor: Database cursor
        code: MLS system code
        
    Returns:
        MLS system UUID
    """
    # Try to get existing
    cursor.execute(
        "SELECT id FROM mls_systems WHERE code = %s",
        (code,)
    )
    row = cursor.fetchone()
    
    if row:
        return row[0]
    
    # Create new MLS system
    mls_name_map = {
        "unlock_mls": "Unlock MLS"
    }
    name = mls_name_map.get(code, code.replace('_', ' ').title())
    
    cursor.execute(
        """
        INSERT INTO mls_systems (code, name, is_active)
        VALUES (%s, %s, TRUE)
        RETURNING id
        """,
        (code, name)
    )
    
    return cursor.fetchone()[0]

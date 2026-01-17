"""
Service for storing and retrieving MLS field mappings.
Handles persistence of mapped MLS data for listings.
"""
import json
from uuid import UUID
from typing import Optional, Dict, Any
from services.api.database import get_db


def save_mls_mapping(
    listing_id: UUID,
    mls_system_code: str,
    mapped_fields: Dict[str, Any]
) -> bool:
    """
    Save or update MLS field mappings for a listing.
    
    Args:
        listing_id: The listing ID
        mls_system_code: MLS system code (e.g., 'unlock_mls')
        mapped_fields: The complete mapping result from prepare_mls_fields()
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db() as (conn, cur):
            # Get or create MLS system
            mls_system_id = _get_or_create_mls_system(cur, mls_system_code)
            
            # Insert or update mapping
            cur.execute(
                """
                INSERT INTO mls_field_mappings (listing_id, mls_system_id, mapped_fields, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (listing_id, mls_system_id)
                DO UPDATE SET
                    mapped_fields = EXCLUDED.mapped_fields,
                    updated_at = now()
                RETURNING id
                """,
                (str(listing_id), str(mls_system_id), json.dumps(mapped_fields, default=str))
            )
            
            return True
    except Exception as e:
        print(f"Error saving MLS mapping: {str(e)}")
        return False


def get_mls_mapping(
    listing_id: UUID,
    mls_system_code: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve stored MLS field mappings for a listing.
    
    Args:
        listing_id: The listing ID
        mls_system_code: MLS system code (e.g., 'unlock_mls')
        
    Returns:
        The mapped fields dictionary, or None if not found
    """
    with get_db() as (conn, cur):
        try:
            # Get MLS system ID
            cur.execute(
                "SELECT id FROM mls_systems WHERE code = %s AND is_active = TRUE",
                (mls_system_code,)
            )
            mls_system_row = cur.fetchone()
            
            if not mls_system_row:
                return None
            
            mls_system_id = mls_system_row[0]
            
            # Get mapping
            cur.execute(
                """
                SELECT mapped_fields
                FROM mls_field_mappings
                WHERE listing_id = %s AND mls_system_id = %s
                """,
                (str(listing_id), str(mls_system_id))
            )
            
            row = cur.fetchone()
            if row:
                mapped_fields = row[0]
                # Handle both dict (psycopg2 2.5+) and string (older versions)
                if isinstance(mapped_fields, str):
                    return json.loads(mapped_fields)
                return mapped_fields  # Already a dict
            return None
        except Exception as e:
            print(f"Error retrieving MLS mapping: {str(e)}")
            return None


def _get_or_create_mls_system(cursor, code: str) -> UUID:
    """
    Get existing MLS system ID or create it if it doesn't exist.
    
    Args:
        cursor: Database cursor
        code: MLS system code (e.g., 'unlock_mls')
        
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

"""
User management service.
Handles user validation, creation, and retrieval for listing operations.
"""
from uuid import UUID
from typing import Optional
from services.api.database import get_db


def get_or_create_test_user(user_id: UUID) -> UUID:
    """
    Get an existing user or create a test user if it doesn't exist.
    
    This is a development/testing utility. In production, users should be
    created through proper authentication/registration flows.
    
    Args:
        user_id: The user ID to check/create
        
    Returns:
        The user ID (existing or newly created)
        
    Raises:
        ValueError: If user_id is invalid
    """
    with get_db() as (conn, cur):
        # Check if user exists
        cur.execute(
            """
            SELECT id FROM users WHERE id = %s
            """,
            (str(user_id),)
        )
        row = cur.fetchone()
        
        if row:
            return UUID(row[0])
        
        # Create a test user (development/testing only)
        # In production, this should be handled by authentication service
        cur.execute(
            """
            INSERT INTO users (id, email, password_hash, full_name, role, is_active)
            VALUES (%s, %s, %s, %s, 'agent', true)
            ON CONFLICT (id) DO NOTHING
            RETURNING id
            """,
            (
                str(user_id),
                f"test_user_{user_id}@example.com",
                "test_hash_placeholder",  # In production, this should be a proper hash
                f"Test User {str(user_id)[:8]}"
            )
        )
        
        result = cur.fetchone()
        if result:
            return UUID(result[0])
        
        # If ON CONFLICT didn't return, user was created in another transaction
        # Fetch it again
        cur.execute(
            """
            SELECT id FROM users WHERE id = %s
            """,
            (str(user_id),)
        )
        row = cur.fetchone()
        if row:
            return UUID(row[0])
        
        raise ValueError(f"Failed to create or retrieve user with ID: {user_id}")


def validate_user_exists(user_id: UUID) -> bool:
    """
    Validate that a user exists in the database.
    
    Args:
        user_id: The user ID to validate
        
    Returns:
        True if user exists, False otherwise
    """
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT id FROM users WHERE id = %s AND is_active = true
            """,
            (str(user_id),)
        )
        return cur.fetchone() is not None


def create_listing_with_optional_user(user_id: Optional[UUID] = None) -> UUID:
    """
    Create a listing with optional user association.
    
    If user_id is provided, validates it exists (or creates test user in dev).
    If user_id is None, creates listing without user association.
    
    Args:
        user_id: Optional user ID. If None, listing is created without user association.
        
    Returns:
        The created listing ID
    """
    with get_db() as (conn, cur):
        if user_id:
            # Ensure user exists (create test user if in development)
            validated_user_id = get_or_create_test_user(user_id)
            cur.execute(
                """
                INSERT INTO listings (created_by)
                VALUES (%s)
                RETURNING id
                """,
                (str(validated_user_id),)
            )
        else:
            # Create listing without user association
            cur.execute(
                """
                INSERT INTO listings (created_by)
                VALUES (NULL)
                RETURNING id
                """,
            )
        
        listing_id = cur.fetchone()[0]
        return listing_id

from uuid import UUID
from datetime import datetime

from services.api.database import get_db
from services.api.models.canonical import CanonicalListing, CanonicalMode
from services.api.services.user_service import get_or_create_test_user


REQUIRED_FIELDS = [
    "location.street_address",
    "location.city",
    "location.state",
    "location.zip_code",
    "listing_meta.list_price",
    "property.property_sub_type",
]


def validate_canonical(listing_id: UUID, user_id: UUID) -> dict:
    """
    Validates a canonical listing and locks it if validation passes.
    Returns a dict with 'success' boolean and either 'errors' or 'validated_at'.
    
    Args:
        listing_id: The listing ID to validate
        user_id: The user ID performing the validation (will be validated/created if needed)
        
    Returns:
        Dictionary with 'success' boolean and either 'errors' list or 'validated_at' timestamp
    """
    # Ensure user exists (will create test user in development if needed)
    validated_user_id = get_or_create_test_user(user_id)
    
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT canonical_payload, locked
            FROM canonical_listings
            WHERE listing_id = %s
            """,
            (str(listing_id),)
        )

        row = cur.fetchone()
        if not row:
            return {"success": False, "errors": ["Canonical not found"]}

        payload, locked = row
        if locked:
            return {"success": False, "errors": ["Canonical already validated"]}

        canonical = CanonicalListing(**payload)

        errors = []

        for path in REQUIRED_FIELDS:
            parts = path.split(".")
            value = canonical
            for part in parts:
                value = getattr(value, part, None)
                if value is None:
                    errors.append(path)
                    break

        if errors:
            return {"success": False, "errors": errors}

        canonical.state.mode = CanonicalMode.LOCKED
        canonical.state.locked = True
        canonical.state.validated = True
        canonical.state.validated_at = datetime.utcnow()
        canonical.state.validated_by = str(validated_user_id)

        cur.execute(
            """
            UPDATE canonical_listings
            SET canonical_payload = %s,
                mode = 'locked',
                locked = true,
                validated_at = now(),
                validated_by = %s
            WHERE listing_id = %s
            """,
            (
                canonical.model_dump_json(),
                str(validated_user_id),
                str(listing_id)
            )
        )

        return {
            "success": True,
            "validated_at": canonical.state.validated_at
        }

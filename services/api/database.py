import os
import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection, cursor
from contextlib import contextmanager
from typing import Generator
import json
from uuid import UUID


# Connection pool configuration
_MIN_CONNECTIONS = 5
_MAX_CONNECTIONS = 50

# Global connection pool (initialized on first use)
_connection_pool: pool.ThreadedConnectionPool | None = None


def _get_pool() -> pool.ThreadedConnectionPool:
    """
    Initialize and return the connection pool.
    Uses lazy initialization to ensure it's created only when needed.
    """
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=_MIN_CONNECTIONS,
            maxconn=_MAX_CONNECTIONS,
            dbname=os.getenv("POSTGRES_DB", "mls"),
            user=os.getenv("POSTGRES_USER", "mls"),
            password=os.getenv("POSTGRES_PASSWORD", "mls@123"),
            host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
        )
    
    return _connection_pool


def get_connection() -> connection:
    """
    Get a connection from the pool.
    DEPRECATED: Use get_db() context manager instead for proper resource management.
    """
    pool = _get_pool()
    return pool.getconn()


@contextmanager
def get_db() -> Generator[tuple[connection, cursor], None, None]:
    """
    Context manager for database connections with automatic cleanup.
    
    Usage:
        with get_db() as (conn, cur):
            cur.execute("SELECT * FROM ...")
            result = cur.fetchone()
            conn.commit()
    
    Automatically handles:
    - Getting connection from pool
    - Creating cursor
    - Rolling back on exception
    - Closing cursor and returning connection to pool
    """
    pool = _get_pool()
    conn = None
    cur = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        yield (conn, cur)
        conn.commit()
    except Exception:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass  # Ignore rollback errors
        raise
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass  # Ignore close errors
        if conn:
            try:
                pool.putconn(conn)
            except Exception:
                pass  # Ignore putconn errors - connection may already be closed


def close_pool():
    """
    Close all connections in the pool.
    Should be called during application shutdown.
    """
    global _connection_pool
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None


# --------------------------------------------------
# LISTING (ROOT ENTITY)
# --------------------------------------------------

def create_listing() -> str:
    """
    Creates a new listing and returns its ID.
    """
    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO listings (status)
            VALUES ('draft')
            RETURNING id;
            """
        )
        listing_id = cur.fetchone()[0]
        return str(listing_id)


# --------------------------------------------------
# DRAFT CANONICAL
# --------------------------------------------------

def upsert_draft_canonical(listing_id: str, payload: dict):
    """
    Inserts or updates the draft canonical for a listing using canonical_listings.
    """
    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO canonical_listings
                (listing_id, schema_version, canonical_payload, mode)
            VALUES (%s, %s, %s, 'draft')
            ON CONFLICT (listing_id)
            DO UPDATE SET
                canonical_payload = EXCLUDED.canonical_payload,
                schema_version = EXCLUDED.schema_version,
                mode = 'draft',
                updated_at = now();
            """,
            (
                listing_id,
                payload["schema_version"],
                json.dumps(payload),
            )
        )


# --------------------------------------------------
# FETCH DRAFT CANONICAL
# --------------------------------------------------

def get_draft_canonical(listing_id: str) -> dict | None:
    """
    Fetches the draft canonical for a listing.
    """
    with get_db() as (conn, cur):
        cur.execute(
            """
            SELECT canonical_payload
            FROM canonical_listings
            WHERE listing_id = %s AND mode = 'draft';
            """,
            (listing_id,)
        )
        row = cur.fetchone()
        return row[0] if row else None

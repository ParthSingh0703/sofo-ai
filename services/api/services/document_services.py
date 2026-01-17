import os
import uuid
import shutil
from fastapi import UploadFile
from services.api.database import get_db
from services.api.services.file_validation import validate_document_file

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "storage")


async def save_document_file(listing_id, file: UploadFile) -> str:
    """
    Save a validated document file to disk and database.
    
    Args:
        listing_id: The listing ID to associate the document with
        file: The uploaded file (must be PDF, DOCX, or TXT)
        
    Returns:
        The document ID as a string
        
    Raises:
        HTTPException: If file validation fails
    """
    # 1) Validate file type and size
    validate_document_file(file)
    
    # 2) Build local path
    safe_name = f"{uuid.uuid4()}_{file.filename}"
    rel_dir = os.path.join("documents", str(listing_id))
    rel_path = os.path.join(rel_dir, safe_name)
    abs_dir = os.path.join(STORAGE_ROOT, rel_dir)
    abs_path = os.path.join(STORAGE_ROOT, rel_path)

    os.makedirs(abs_dir, exist_ok=True)

    # 3) Save file to disk
    with open(abs_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # 4) Insert DB row
    with get_db() as (conn, cur):
        cur.execute(
            """
            INSERT INTO documents (listing_id, filename, storage_path)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (str(listing_id), file.filename, rel_path),
        )
        document_id = cur.fetchone()[0]
        return str(document_id)


async def delete_document_file(listing_id, document_id: str) -> bool:
    """
    Delete a document file from disk and database.
    
    Args:
        listing_id: The listing ID (for validation)
        document_id: The document ID to delete
        
    Returns:
        True if deletion was successful, False otherwise
        
    Raises:
        HTTPException: If document not found or deletion fails
    """
    with get_db() as (conn, cur):
        # Get storage path before deletion
        cur.execute(
            """
            SELECT storage_path FROM documents
            WHERE id = %s AND listing_id = %s
            """,
            (document_id, str(listing_id))
        )
        row = cur.fetchone()
        
        if not row:
            return False
        
        storage_path = row[0]
        
        # Delete from database (CASCADE will handle document_pages)
        cur.execute(
            """
            DELETE FROM documents
            WHERE id = %s AND listing_id = %s
            """,
            (document_id, str(listing_id))
        )
        
        if cur.rowcount == 0:
            return False
        
        # Delete file from disk
        abs_path = os.path.join(STORAGE_ROOT, storage_path)
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception as e:
            print(f"Warning: Failed to delete file {abs_path}: {str(e)}")
            # Continue even if file deletion fails
        
        return True
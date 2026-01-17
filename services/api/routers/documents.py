"""
Document upload endpoints.
Handles document file uploads with validation.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from uuid import UUID
from services.api.services.document_services import save_document_file, delete_document_file

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/listings/{listing_id}")
async def upload_document(listing_id: UUID, file: UploadFile = File(...)):
    """
    Upload a document file for a listing.
    
    Allowed document types: PDF, DOCX, TXT
    Maximum file size: 50 MB
    
    Args:
        listing_id: The listing ID to associate the document with
        file: The document file to upload
        
    Returns:
        Dictionary containing the document_id
        
    Raises:
        HTTPException: If validation fails or upload error occurs
    """
    try:
        document_id = await save_document_file(listing_id, file)
        return {"document_id": document_id}
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@router.delete("/listings/{listing_id}/{document_id}")
async def delete_document(listing_id: UUID, document_id: UUID):
    """
    Delete a document file for a listing.
    
    Args:
        listing_id: The listing ID
        document_id: The document ID to delete
        
    Returns:
        Dictionary with success status
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        success = await delete_document_file(listing_id, str(document_id))
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"success": True, "message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
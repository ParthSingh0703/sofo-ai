"""
File validation utilities for secure file uploads.
Validates both MIME types and file extensions to prevent malicious uploads.
"""
import mimetypes
from pathlib import Path
from fastapi import UploadFile, HTTPException


# Allowed file types configuration
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",
}

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
}

# File size limits (in bytes)
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    pass


def get_file_extension(filename: str) -> str:
    """
    Extract file extension from filename.
    
    Args:
        filename: The filename to extract extension from
        
    Returns:
        Lowercase file extension including the dot (e.g., '.pdf')
    """
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def validate_file_type(
    file: UploadFile,
    allowed_extensions: set[str],
    allowed_mime_types: set[str],
    file_type_name: str = "file"
) -> None:
    """
    Validate that an uploaded file matches allowed extensions and MIME types.
    
    Args:
        file: The uploaded file to validate
        allowed_extensions: Set of allowed file extensions (e.g., {'.pdf', '.docx'})
        allowed_mime_types: Set of allowed MIME types (e.g., {'application/pdf'})
        file_type_name: Human-readable name for error messages (e.g., 'document', 'image')
        
    Raises:
        HTTPException: If file type is not allowed
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )
    
    # Get file extension
    extension = get_file_extension(file.filename)
    
    if not extension:
        raise HTTPException(
            status_code=400,
            detail=f"File must have a valid extension. Allowed {file_type_name} types: {', '.join(allowed_extensions)}"
        )
    
    # Check extension
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{extension}' is not allowed. Allowed {file_type_name} types: {', '.join(allowed_extensions)}"
        )
    
    # Check MIME type
    mime_type = file.content_type
    guessed_type, _ = mimetypes.guess_type(file.filename)
    
    # Accept if either the declared MIME type or guessed MIME type is allowed
    # This handles cases where browsers send different MIME types
    is_valid_mime = (
        (mime_type and mime_type in allowed_mime_types) or
        (guessed_type and guessed_type in allowed_mime_types)
    )
    
    if not is_valid_mime:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{mime_type or guessed_type or 'unknown'}' is not allowed. Allowed {file_type_name} MIME types: {', '.join(sorted(allowed_mime_types))}"
        )


def validate_file_size(
    file: UploadFile,
    max_size: int,
    file_type_name: str = "file"
) -> None:
    """
    Validate that an uploaded file does not exceed the maximum size.
    
    Note: This checks the content_length header. For more accurate validation,
    you may want to read the file and check its actual size.
    
    Args:
        file: The uploaded file to validate
        max_size: Maximum allowed file size in bytes
        file_type_name: Human-readable name for error messages
        
    Raises:
        HTTPException: If file size exceeds the limit
    """
    if file.size and file.size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {max_size_mb:.1f} MB for {file_type_name}s"
        )


def validate_document_file(file: UploadFile) -> None:
    """
    Validate that an uploaded file is an allowed document type.
    Allowed types: PDF, DOCX, TXT
    
    Args:
        file: The uploaded file to validate
        
    Raises:
        HTTPException: If file is not a valid document type
    """
    validate_file_type(
        file,
        allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS,
        allowed_mime_types=ALLOWED_DOCUMENT_MIME_TYPES,
        file_type_name="document"
    )
    validate_file_size(file, MAX_DOCUMENT_SIZE, "document")


def validate_image_file(file: UploadFile) -> None:
    """
    Validate that an uploaded file is an allowed image type.
    Allowed types: JPG, JPEG, PNG
    
    Args:
        file: The uploaded file to validate
        
    Raises:
        HTTPException: If file is not a valid image type
    """
    validate_file_type(
        file,
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        allowed_mime_types=ALLOWED_IMAGE_MIME_TYPES,
        file_type_name="image"
    )
    validate_file_size(file, MAX_IMAGE_SIZE, "image")

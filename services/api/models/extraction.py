"""
Models for document extraction with provenance tracking.
"""
from pydantic import BaseModel
from typing import Optional, Literal, Any


class FieldProvenance(BaseModel):
    """
    Tracks the source of extracted field values.
    Every field in the canonical listing should include provenance.
    """
    file_id: str  # Document UUID
    page_number: Optional[int] = None  # Page number if applicable
    source_type: Literal["text", "vision"]  # Extraction method used
    confidence: Optional[float] = None  # Optional confidence score (0.0-1.0)


class ExtractedField(BaseModel):
    """
    A field value with its provenance information.
    """
    value: Any  # The extracted value (string, number, etc.)
    provenance: FieldProvenance


class DocumentExtractionResult(BaseModel):
    """
    Result of extracting a single document using AI.
    """
    document_id: str
    extraction_method: Literal["ai"] = "ai"  # Always AI-based now
    extracted_fields: dict[str, ExtractedField]  # Field path -> ExtractedField
    raw_text: Optional[str] = None  # Full extracted text (if available)
    page_texts: dict[int, str] = {}  # Page number -> text content (if available)


class ExtractionConfig(BaseModel):
    """
    Configuration for AI-based extraction pipeline.
    All extraction is now AI-only using Gemini models.
    """
    # No configuration needed - always uses AI
    pass

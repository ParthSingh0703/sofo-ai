"""
Native text extraction utilities for PDF, DOCX, and TXT files.
No OCR - only extracts native text layers.
"""
import os
import math
from pathlib import Path
from typing import Optional


def extract_pdf_text(file_path: str) -> tuple[str, dict[int, str]]:
    """
    Extract text from PDF using native text layer (no OCR).
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Tuple of (full_text, page_texts_dict) where page_texts_dict maps page_number -> text
    """
    try:
        import PyPDF2
        
        full_text = []
        page_texts = {}
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        full_text.append(page_text)
                        page_texts[page_num] = page_text
                except Exception as e:
                    # Skip page if extraction fails
                    page_texts[page_num] = ""
                    continue
        
        return "\n".join(full_text), page_texts
    
    except ImportError:
        raise ImportError("PyPDF2 is required for PDF extraction. Install with: pip install PyPDF2")
    except Exception as e:
        raise Exception(f"Failed to extract PDF text: {str(e)}")


def extract_docx_text(file_path: str) -> tuple[str, dict[int, str]]:
    """
    Extract text from DOCX file.
    
    Args:
        file_path: Path to DOCX file
        
    Returns:
        Tuple of (full_text, page_texts_dict)
        Note: DOCX doesn't have explicit pages, so page_texts will have {1: full_text}
    """
    try:
        from docx import Document
        
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        full_text = "\n".join(paragraphs)
        
        # DOCX doesn't have explicit pages, treat as single page
        page_texts = {1: full_text}
        
        return full_text, page_texts
    
    except ImportError:
        raise ImportError("python-docx is required for DOCX extraction. Install with: pip install python-docx")
    except Exception as e:
        raise Exception(f"Failed to extract DOCX text: {str(e)}")


def extract_txt_text(file_path: str) -> tuple[str, dict[int, str]]:
    """
    Extract text from plain text file.
    
    Args:
        file_path: Path to TXT file
        
    Returns:
        Tuple of (full_text, page_texts_dict)
        Note: TXT doesn't have explicit pages, so page_texts will have {1: full_text}
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            full_text = file.read()
        
        # TXT doesn't have explicit pages, treat as single page
        page_texts = {1: full_text}
        
        return full_text, page_texts
    
    except Exception as e:
        raise Exception(f"Failed to extract TXT text: {str(e)}")


def extract_native_text(file_path: str, file_extension: str) -> tuple[str, dict[int, str]]:
    """
    Extract native text from a document based on file extension.
    
    Args:
        file_path: Path to the document file
        file_extension: File extension (e.g., '.pdf', '.docx', '.txt')
        
    Returns:
        Tuple of (full_text, page_texts_dict)
        
    Raises:
        ValueError: If file type is not supported
    """
    ext = file_extension.lower()
    
    if ext == '.pdf':
        return extract_pdf_text(file_path)
    elif ext in ['.docx', '.doc']:
        return extract_docx_text(file_path)
    elif ext == '.txt':
        return extract_txt_text(file_path)
    else:
        raise ValueError(f"Unsupported file type for native text extraction: {ext}")

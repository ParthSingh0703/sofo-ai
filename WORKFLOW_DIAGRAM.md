# Complete System Workflow Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                            │
│  (Frontend - Not implemented yet)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI API LAYER                         │
│  - Authentication (Future)                                   │
│  - Request Validation                                        │
│  - Response Formatting                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Documents  │ │   Images    │ │  Listings   │
│   Router    │ │   Router    │ │   Router    │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                             │
│  - File Validation                                           │
│  - File Storage                                              │
│  - Extraction Pipeline                                       │
│  - Enrichment Services                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│  - PostgreSQL (Structured Data)                             │
│  - File System (Documents & Images)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Workflow: Complete Listing Lifecycle

### Stage 1: INITIALIZATION

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ POST /api/listings?user_id={id}
       ▼
┌─────────────────────────────────────┐
│  Canonical Service                  │
│  - Create listing record            │
│  - Create empty canonical           │
│  - Set mode = 'draft'               │
│  - Set locked = false               │
└──────┬──────────────────────────────┘
       │
       │ Returns: listing_id
       ▼
┌─────────────┐
│  Database   │
│  - listings table                    │
│  - canonical_listings table          │
└─────────────┘
```

### Stage 2: FILE UPLOAD

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ├─► POST /api/documents/listings/{id}
       │   │
       │   ├─► File Validation Service
       │   │   - Check extension (.pdf, .docx, .txt)
       │   │   - Check MIME type
       │   │   - Check file size (max 50 MB)
       │   │
       │   ├─► Document Service
       │   │   - Generate safe filename
       │   │   - Save to: storage/documents/{listing_id}/
       │   │   - Insert into documents table
       │   │
       │   └─► Returns: document_id
       │
       └─► POST /api/images/listings/{id}
           │
           ├─► File Validation Service
           │   - Check extension (.jpg, .jpeg, .png)
           │   - Check MIME type
           │   - Check file size (max 10 MB)
           │
           ├─► Image Service
           │   - Generate safe filename
           │   - Save to: storage/images/{listing_id}/
           │   - Insert into listing_images table
           │
           └─► Returns: image_id
```

### Stage 3: DOCUMENT EXTRACTION

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ POST /api/extraction/listings/{id}/extract?method=auto
       ▼
┌─────────────────────────────────────────────────────────────┐
│  Extraction Pipeline                                        │
│                                                             │
│  1. Get all documents for listing                          │
│     └─► Query: SELECT * FROM documents WHERE listing_id    │
│                                                             │
│  2. For each document:                                     │
│     │                                                      │
│     ├─► Native Text Extraction                            │
│     │   │                                                 │
│     │   ├─► PDF: PyPDF2 (text layer only)               │
│     │   ├─► DOCX: python-docx                            │
│     │   └─► TXT: Direct read                              │
│     │                                                      │
│     ├─► Text Quality Scoring                              │
│     │   │                                                 │
│     │   ├─► Length Score (word/char count)              │
│     │   ├─► Entropy Score (meaningful text)             │
│     │   └─► Keyword Score (MLS terms)                    │
│     │                                                      │
│     ├─► Decision Point                                    │
│     │   │                                                 │
│     │   ├─► If quality ≥ 0.5:                            │
│     │   │   └─► Native Text Extraction                   │
│     │   │       ├─► Deterministic (regex patterns)      │
│     │   │       └─► LLM-assisted (Groq)                 │
│     │   │                                                 │
│     │   └─► If quality < 0.5 OR method=vision_only:      │
│     │       └─► Vision Extraction                        │
│     │           ├─► Convert PDF pages → images           │
│     │           └─► Groq Vision API (text-only for now)  │
│     │                                                      │
│     └─► Store Results                                     │
│         ├─► document_pages table (text per page)         │
│         └─► Extracted fields with provenance              │
│                                                             │
│  3. Merge extracted fields                                │
│     └─► Build CanonicalListing object                     │
│                                                             │
│  4. Update canonical_listings table                       │
└─────────────────────────────────────────────────────────────┘
       │
       │ Returns: CanonicalListing with extracted data
       ▼
┌─────────────┐
│  Database   │
│  - canonical_listings.canonical_payload updated            │
│  - document_pages populated                               │
│  - extracted_field_facts (optional tracking)              │
└─────────────┘
```

### Stage 4: IMAGE ENRICHMENT

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ POST /api/enrichment/listings/{id}/enrich
       ▼
┌─────────────────────────────────────────────────────────────┐
│  Enrichment Service                                         │
│                                                             │
│  TASK 1: Image Analysis                                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ For each image:                                     │  │
│  │                                                     │  │
│  │ 1. Filename Analysis                                │  │
│  │    └─► Extract label from filename                 │  │
│  │        (kitchen.jpg → "kitchen")                   │  │
│  │                                                     │  │
│  │ 2. If filename unclear:                            │  │
│  │    └─► Vision Analysis (Groq)                      │  │
│  │        ├─► Identify room/portion                   │  │
│  │        ├─► Determine photo_type                    │  │
│  │        └─► Generate description                    │  │
│  │                                                     │  │
│  │ 3. Store Results                                   │  │
│  │    ├─► listing_images.ai_suggested_label           │  │
│  │    ├─► image_ai_analysis.description              │  │
│  │    └─► image_ai_analysis.detected_features        │  │
│  │        (photo_type, room_label, etc.)              │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  TASK 2: Photo Sequencing                                  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 1. Get all images with labels                      │  │
│  │ 2. Sort by priority:                                │  │
│  │    - front_exterior (1st)                           │  │
│  │    - living_room (2nd)                              │  │
│  │    - kitchen (3rd)                                  │  │
│  │    - master_bedroom (4th)                           │  │
│  │    - bathrooms (5th)                                │  │
│  │    - other interior (6th)                           │  │
│  │    - backyard/patio (7th)                           │  │
│  │    - community (8th)                                │  │
│  │    - floor_plan/map (9th)                           │  │
│  │ 3. Update ai_suggested_order                        │  │
│  │ 4. Set is_primary for front_exterior              │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  TASK 3: Listing Descriptions                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 1. Get canonical listing                            │  │
│  │ 2. Extract property info                            │  │
│  │ 3. Generate with Groq LLM:                          │  │
│  │    ├─► public_remarks (≤ 1500 chars)               │  │
│  │    └─► syndication_remarks                          │  │
│  │ 4. Update canonical.remarks                        │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
       │
       │ Returns: Enrichment results
       ▼
┌─────────────┐
│  Database   │
│  - listing_images updated (labels, order, primary)         │
│  - image_ai_analysis populated                            │
│  - canonical_listings.remarks updated                     │
└─────────────┘
```

### Stage 5: USER REVIEW & EDIT

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ GET /api/listings/{id}/canonical
       ▼
┌─────────────────────────────────────┐
│  Canonical Service                  │
│  - Retrieve canonical_payload       │
│  - Return CanonicalListing object   │
└──────┬──────────────────────────────┘
       │
       │ User reviews in UI
       │ - Corrects extracted values
       │ - Edits image descriptions
       │ - Adjusts photo order
       │
       │ PUT /api/listings/{id}/canonical
       ▼
┌─────────────────────────────────────┐
│  Canonical Service                  │
│  - Check if locked (must be false) │
│  - Update canonical_payload        │
│  - Update updated_at timestamp      │
└──────┬──────────────────────────────┘
       │
       │ Returns: Updated CanonicalListing
       ▼
┌─────────────┐
│  Database   │
│  - canonical_listings updated       │
└─────────────┘
```

### Stage 6: VALIDATION & LOCK

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ POST /api/listings/{id}/validate?user_id={id}
       ▼
┌─────────────────────────────────────────────────────────────┐
│  Validation Service                                         │
│                                                             │
│  1. Check if canonical exists                              │
│  2. Check if already locked (reject if true)              │
│  3. Validate required fields:                             │
│     ├─► location.street_address                            │
│     ├─► location.city                                      │
│     ├─► location.state                                     │
│     ├─► location.zip_code                                  │
│     ├─► listing_meta.list_price                           │
│     └─► property.property_sub_type                         │
│                                                             │
│  4. If validation passes:                                  │
│     ├─► Set state.locked = true                           │
│     ├─► Set state.mode = "validated"                      │
│     ├─► Set validated_at = now()                          │
│     ├─► Set validated_by = user_id                        │
│     └─► Update canonical_listings table                   │
│                                                             │
│  5. If validation fails:                                   │
│     └─► Return list of missing fields                     │
└─────────────────────────────────────────────────────────────┘
       │
       │ Returns: Validation result
       ▼
┌─────────────┐
│  Database   │
│  - canonical_listings.locked = true                        │
│  - canonical_listings.mode = 'validated'                  │
│  - canonical_listings.validated_at set                    │
│  - canonical_listings.validated_by set                    │
└─────────────┘
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT LAYER                              │
│  Documents (PDF/DOCX/TXT) + Images (JPG/PNG)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROCESSING LAYER                            │
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │  Extraction  │────────►│  Enrichment  │                 │
│  │  Pipeline    │         │  Services    │                 │
│  └──────────────┘         └──────────────┘                 │
│         │                         │                          │
│         │                         │                          │
│         ▼                         ▼                          │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   Native     │         │    Vision    │                 │
│  │   Text       │         │    Analysis  │                 │
│  └──────────────┘         └──────────────┘                 │
│         │                         │                          │
│         └─────────────┬───────────┘                          │
│                       │                                      │
│                       ▼                                      │
│              ┌──────────────┐                               │
│              │     Groq     │                               │
│              │     LLM      │                               │
│              └──────────────┘                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                              │
│  CanonicalListing (Structured Data)                          │
│  - Extracted fields with provenance                          │
│  - Image labels and descriptions                             │
│  - Photo sequencing                                          │
│  - Generated remarks                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  STORAGE LAYER                               │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │  PostgreSQL  │         │  File System │                 │
│  │  - Metadata  │         │  - Documents │                 │
│  │  - Canonical │         │  - Images    │                 │
│  └──────────────┘         └──────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Provenance Tracking Flow

```
Document Upload
    │
    ├─► document_id stored
    │
Extraction
    │
    ├─► Field: location.street_address
    │   └─► Provenance:
    │       - file_id: document_id
    │       - page_number: 1
    │       - source_type: "text" or "vision"
    │       - confidence: 0.95
    │
    └─► Stored in:
        - canonical_listings.canonical_payload (value only)
        - extracted_field_facts (with full provenance)
```

---

## State Machine: Canonical Listing

```
┌─────────┐
│  DRAFT  │ ◄─── Initial state
└────┬────┘
     │
     │ User edits
     │ Extraction runs
     │ Enrichment runs
     │
     ▼
┌─────────┐
│  DRAFT  │ ◄─── Can be edited
└────┬────┘      (locked = false)
     │
     │ POST /validate
     │ (all required fields present)
     │
     ▼
┌─────────────┐
│  VALIDATED  │ ◄─── Locked state
└─────────────┘      (locked = true)
     │                Cannot be edited
     │                Image descriptions locked
     │
     └──► Ready for MLS submission
```

---

## Error Handling Flow

```
Request
  │
  ├─► Validation Error
  │   └─► HTTP 400: Invalid input
  │
  ├─► File Validation Error
  │   └─► HTTP 400: Invalid file type/size
  │
  ├─► Database Error
  │   └─► HTTP 500: Database operation failed
  │
  ├─► Extraction Error
  │   └─► HTTP 500: Extraction failed
  │       └─► Falls back to deterministic extraction
  │
  ├─► Enrichment Error
  │   └─► HTTP 500: Enrichment failed
  │       └─► Partial results returned
  │
  └─► Locked Error
      └─► HTTP 400: Canonical is locked
```

---

## Performance Considerations

### Extraction Pipeline
- **Native Text**: Fast (~100-500ms per document)
- **Vision Extraction**: Slower (~2-5s per page, depends on Groq API)
- **LLM-Assisted**: Moderate (~1-3s per document)

### Enrichment Pipeline
- **Image Analysis**: ~1-2s per image (Groq API)
- **Photo Sequencing**: Fast (~50ms, in-memory)
- **Description Generation**: ~2-4s (Groq API)

### Optimization Tips
1. Use `native_text_only` for faster extraction when documents have good text quality
2. Batch image analysis (process multiple images in parallel)
3. Cache Groq responses for similar documents
4. Use connection pooling (already implemented)

---

## Security Considerations

1. **File Validation**: Prevents malicious uploads
2. **File Size Limits**: Prevents DoS attacks
3. **Path Sanitization**: Prevents directory traversal
4. **Type Checking**: Ensures data integrity
5. **Locked State**: Prevents unauthorized edits

---

## Future Enhancements

1. **Authentication**: Add JWT/OAuth2
2. **Rate Limiting**: Prevent API abuse
3. **Background Jobs**: Async processing for large files
4. **Caching**: Cache extraction/enrichment results
5. **Webhooks**: Notify on completion
6. **Audit Logging**: Track all changes

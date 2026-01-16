# Complete System Workflow

## High-Level Overview

The MLS Automation System processes real estate listings through 5 main stages:

```
┌─────────────┐
│   INTAKE    │ → Upload documents & images
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ EXTRACTION  │ → Extract structured data from documents
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ ENRICHMENT  │ → Analyze images & generate descriptions
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   REVIEW    │ → User validates and edits
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ VALIDATION  │ → Lock canonical for MLS submission
└─────────────┘
```

---

## Stage 1: INTAKE - File Upload

### What Happens:

1. **Create Listing**
   - User creates a new listing via API
   - System creates:
     - `listings` table record
     - `canonical_listings` table record (empty, draft mode)
   - Returns `listing_id`

2. **Upload Documents**
   - User uploads PDF, DOCX, or TXT files
   - System validates:
     - File extension (.pdf, .docx, .txt)
     - MIME type
     - File size (max 50 MB)
   - System saves:
     - File to disk: `storage/documents/{listing_id}/{uuid}_{filename}`
     - Metadata to `documents` table
   - Returns `document_id` for each file

3. **Upload Images**
   - User uploads JPG, JPEG, or PNG files
   - System validates:
     - File extension (.jpg, .jpeg, .png)
     - MIME type
     - File size (max 10 MB)
   - System saves:
     - File to disk: `storage/images/{listing_id}/{uuid}_{filename}`
     - Metadata to `listing_images` table
   - Returns `image_id` for each file

### Data Flow:
```
User → API → File Validation → File Storage → Database
```

---

## Stage 2: EXTRACTION - Document Processing

### What Happens:

1. **Trigger Extraction**
   - User calls extraction endpoint
   - System fetches all documents for the listing

2. **For Each Document:**

   **A. Native Text Extraction**
   - Extract text from:
     - PDF: Uses PyPDF2 (text layer only, no OCR)
     - DOCX: Uses python-docx
     - TXT: Direct file read
   - Store page-by-page text in `document_pages` table

   **B. Text Quality Scoring**
   - Calculate three scores:
     - **Length Score**: Word/character count (normalized)
     - **Entropy Score**: Measures meaningful text vs garbage
     - **Keyword Score**: Presence of MLS-relevant keywords
   - Combined score: `(length * 0.3) + (entropy * 0.4) + (keywords * 0.3)`

   **C. Extraction Method Decision**
   - If `method = "auto"`:
     - Quality ≥ threshold (0.5): Use native text extraction
     - Quality < threshold: Use vision extraction
   - If `method = "native_text_only"`: Always use native text
   - If `method = "vision_only"`: Always use vision

   **D. Field Extraction**
   
   **Native Text Path:**
   - Run deterministic regex patterns:
     - Address patterns
     - Price patterns
     - Bed/bath patterns
     - Square footage patterns
   - Optionally use Groq LLM for structured extraction:
     - Send full text to LLM
     - Request structured JSON matching canonical schema
     - Parse and extract fields
   
   **Vision Path:**
   - Convert PDF pages to images (one per page)
   - For each page image:
     - Encode to base64
     - Send to Groq Vision API (currently text-only prompt)
     - Extract structured fields with confidence scores
     - Parse JSON response

   **E. Provenance Tracking**
   - Each extracted field includes:
     - `value`: The extracted data
     - `provenance`:
       - `file_id`: Which document it came from
       - `page_number`: Which page (if applicable)
       - `source_type`: "text" or "vision"
       - `confidence`: 0.0-1.0 (for vision extraction)

3. **Merge Results**
   - Combine all extracted fields from all documents
   - Build `CanonicalListing` object
   - Preserve existing user edits (don't overwrite)
   - Update `canonical_listings` table

### Data Flow:
```
Documents → Native Text / Vision → Field Extraction → CanonicalListing
```

### Example Extraction:
```json
{
  "location": {
    "street_address": {
      "value": "123 Main St",
      "provenance": {
        "file_id": "doc-uuid-1",
        "page_number": 1,
        "source_type": "text",
        "confidence": null
      }
    }
  },
  "listing_meta": {
    "list_price": {
      "value": 450000,
      "provenance": {
        "file_id": "doc-uuid-1",
        "page_number": 1,
        "source_type": "vision",
        "confidence": 0.95
      }
    }
  }
}
```

---

## Stage 3: ENRICHMENT - Image Analysis & Description Generation

### What Happens:

**Task 1: Image Analysis**

For each uploaded image:

1. **Filename Analysis (Precedence Rule)**
   - Check if filename contains room/portion name:
     - `kitchen.jpg` → "kitchen"
     - `front_exterior_1.jpg` → "front_exterior"
     - `living_room.jpg` → "living_room"
   - If filename is clear, use it and skip vision analysis

2. **Vision Analysis (if filename unclear)**
   - Send image to Groq Vision API
   - Identify:
     - `room_label`: front_exterior, kitchen, living_room, etc.
     - `photo_type`: interior, exterior, floor_plan, map, other
   - Generate short description (1-2 sentences)

3. **Store Results**
   - Update `listing_images` table:
     - `ai_suggested_label`: Room/portion label
     - `final_label`: User can override
   - Insert into `image_ai_analysis` table:
     - `description`: AI-generated description
     - `detected_features`: JSONB with `photo_type`, `room_label`, etc.

**Task 2: Photo Sequencing**

1. **Get All Images with Labels**
2. **Sort by MLS Priority:**
   ```
   1. Front exterior (primary)
   2. Living area / Family room
   3. Kitchen
   4. Primary bedroom / Master bedroom
   5. Bathrooms
   6. Other interior rooms
   7. Backyard / Patio / Deck
   8. Community / Amenities
   9. Floor plans / Maps
   10. Other
   ```
3. **Update Database:**
   - `ai_suggested_order`: Recommended order
   - `display_order`: Final order (user can override)
   - `is_primary`: True for best front exterior

**Task 3: Listing Descriptions**

1. **Get Canonical Listing** (property data only, no images)
2. **Extract Property Information:**
   - Address, price, beds, baths, sqft
   - Features, amenities
   - Property type, year built
3. **Generate with Groq LLM:**
   - `public_remarks`: ≤ 1500 characters, MLS-safe
   - `syndication_remarks`: Additional details
   - Tone options: neutral, luxury, family_friendly, investor
4. **Update Canonical:**
   - Store in `canonical_listings.canonical_payload.remarks`

### Data Flow:
```
Images → Vision Analysis → Labels & Descriptions → Photo Sequence → CanonicalListing
CanonicalListing → LLM → Public/Syndication Remarks → CanonicalListing
```

---

## Stage 4: REVIEW - User Validation & Editing

### What Happens:

1. **Get Canonical**
   - User retrieves full canonical listing
   - Reviews all extracted fields
   - Reviews image descriptions
   - Reviews photo sequence
   - Reviews generated remarks

2. **Make Edits**
   - User corrects extracted values
   - User edits image descriptions
   - User adjusts photo order
   - User modifies listing descriptions

3. **Update Canonical**
   - System checks: `locked = false` (must be true to allow edits)
   - Updates `canonical_listings` table
   - Updates `updated_at` timestamp

### Data Flow:
```
CanonicalListing → User Review → Edits → Updated CanonicalListing
```

---

## Stage 5: VALIDATION - Lock for MLS Submission

### What Happens:

1. **Validation Check**
   - System checks if canonical exists
   - System checks if already locked (reject if true)
   - System validates required fields:
     - `location.street_address`
     - `location.city`
     - `location.state`
     - `location.zip_code`
     - `listing_meta.list_price`
     - `property.property_sub_type`

2. **If Validation Passes:**
   - Set `state.locked = true`
   - Set `state.mode = "validated"`
   - Set `validated_at = now()`
   - Set `validated_by = user_id`
   - **Lock canonical** - no more edits allowed
   - **Lock image descriptions** - cannot be changed

3. **If Validation Fails:**
   - Return list of missing required fields
   - Canonical remains editable

### Data Flow:
```
CanonicalListing → Validation Check → Locked CanonicalListing (Ready for MLS)
```

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT                                │
│  Documents (PDF/DOCX/TXT) + Images (JPG/PNG)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  FILE VALIDATION & STORAGE                   │
│  - Validate file type, size                                  │
│  - Save to disk: storage/{documents|images}/{listing_id}/   │
│  - Store metadata in database                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  EXTRACTION  │ │  ENRICHMENT  │ │   REVIEW    │
│   PIPELINE   │ │   SERVICES   │ │   & EDIT    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       │                │                │
       ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING                               │
│                                                             │
│  Native Text Extraction  →  Field Extraction               │
│  Vision Extraction       →  Field Extraction               │
│  Image Analysis          →  Labels & Descriptions         │
│  Photo Sequencing        →  Recommended Order              │
│  LLM Generation          →  Listing Descriptions            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    CANONICAL LISTING                         │
│  - Extracted fields with provenance                          │
│  - Image labels, descriptions, sequence                      │
│  - Generated remarks                                          │
│  - User edits                                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    VALIDATION                                │
│  - Check required fields                                      │
│  - Lock canonical                                             │
│  - Ready for MLS submission                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## State Machine: Canonical Listing

```
┌─────────┐
│  DRAFT  │ ◄─── Initial state (after listing creation)
└────┬────┘      - locked = false
     │           - mode = "draft"
     │           - Can be edited
     │
     │ User uploads files
     │ Extraction runs
     │ Enrichment runs
     │ User edits
     │
     │ (still in DRAFT)
     │
     ▼
┌─────────┐
│  DRAFT  │ ◄─── Still editable
└────┬────┘      - locked = false
     │           - mode = "draft"
     │
     │ POST /validate
     │ (all required fields present)
     │
     ▼
┌─────────────┐
│  VALIDATED  │ ◄─── Locked state
└─────────────┘      - locked = true
     │                - mode = "validated"
     │                - Cannot be edited
     │                - Image descriptions locked
     │
     └──► Ready for MLS submission
```

---

## Key Concepts

### Provenance Tracking
Every extracted field knows where it came from:
- **file_id**: Which document
- **page_number**: Which page
- **source_type**: "text" or "vision"
- **confidence**: How confident (0.0-1.0)

### Method Switching
You can test different extraction methods:
- **auto**: Smart choice based on text quality
- **native_text_only**: Fast, for text-based documents
- **vision_only**: For image-based documents or comparison

### Filename Precedence
Image labels use filename first:
- `kitchen.jpg` → automatically labeled "kitchen"
- `photo1.jpg` → needs vision analysis

### Locking Mechanism
Once validated:
- Canonical cannot be edited
- Image descriptions cannot be changed
- Ensures data integrity for MLS submission

---

## Performance Characteristics

### Extraction Speed:
- **Native Text**: ~100-500ms per document
- **Vision Extraction**: ~2-5s per page (depends on Groq API)
- **LLM-Assisted**: ~1-3s per document

### Enrichment Speed:
- **Image Analysis**: ~1-2s per image (Groq API)
- **Photo Sequencing**: ~50ms (in-memory)
- **Description Generation**: ~2-4s (Groq API)

### Optimization Tips:
1. Use `native_text_only` for faster extraction when documents have good text
2. Batch process multiple images in parallel (future enhancement)
3. Cache Groq responses for similar documents (future enhancement)

---

## Error Handling

### File Validation Errors:
- Invalid file type → HTTP 400
- File too large → HTTP 400
- Malformed file → HTTP 400

### Extraction Errors:
- Extraction fails → Falls back to deterministic patterns
- LLM fails → Falls back to regex-only extraction
- Vision fails → Returns partial results

### Database Errors:
- Connection pool exhausted → HTTP 503
- Transaction fails → Rollback, HTTP 500

### Lock Errors:
- Trying to edit locked canonical → HTTP 400
- Trying to validate already validated → HTTP 400

---

## Security Considerations

1. **File Validation**: Prevents malicious uploads
2. **File Size Limits**: Prevents DoS attacks
3. **Path Sanitization**: Prevents directory traversal
4. **Type Checking**: Ensures data integrity
5. **Locked State**: Prevents unauthorized edits

---

## Future Enhancements

1. **Authentication**: JWT/OAuth2 for user authentication
2. **Background Jobs**: Async processing for large files
3. **Caching**: Cache extraction/enrichment results
4. **Webhooks**: Notify on completion
5. **Audit Logging**: Track all changes
6. **Rate Limiting**: Prevent API abuse
7. **Parallel Processing**: Process multiple images/documents simultaneously

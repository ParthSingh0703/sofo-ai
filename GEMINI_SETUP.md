# Gemini API Configuration

This project now uses Google Gemini models for AI-powered features:

## Models Used

**Gemini 2.5 Flash** (`gemini-2.5-flash`)
   - Document extraction (vision-based text extraction from PDFs)
   - Listing description generation (text-only)
   - Image vision-based labeling (room/portion identification)
   - Image description generation

## Setup Instructions

### 1. Install Dependencies

```bash
pip install google-genai>=0.2.0
```

Or install all requirements:
```bash
pip install -r services/api/requirements.txt
```

### 2. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the API key

### 3. Configure Environment Variables

Add to your `.env` file or set as environment variables:

```bash
# Required: Gemini API Key (used for all Gemini features)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Override default models
VISION_MODEL=gemini-2.5-flash            # For document extraction (default: gemini-2.5-flash)
IMAGE_VISION_MODEL=gemini-2.5-flash      # For image analysis (default: gemini-2.5-flash)
LLM_MODEL=gemini-2.5-flash               # For text generation (default: gemini-2.5-flash)

# Optional: Poppler path (if not in PATH)
POPPLER_PATH=C:\path\to\poppler\bin      # Path to Poppler bin directory (Windows)
```

### 4. Backward Compatibility

The code still checks for these environment variables for backward compatibility:
- `VISION_API_KEY` (falls back to `GEMINI_API_KEY`)
- `LLM_API_KEY` (falls back to `GEMINI_API_KEY`)

## Features Using Gemini

### Document Extraction (`extraction_vision.py`)
- **Model**: Gemini 1.0 Pro
- **Purpose**: Extract structured data from document images (PDFs converted to images)
- **Endpoint**: `POST /api/extraction/listings/{listing_id}/extract?method=vision_only`

### Image Analysis (`enrichment_image_analysis.py`)
- **Model**: Gemini 2.5 Flash
- **Purpose**: 
  - Room/portion identification (front_exterior, kitchen, bedroom, etc.)
  - Photo type classification (interior, exterior, floor_plan, etc.)
  - Image description generation (1-2 sentences)
- **Endpoint**: `POST /api/enrichment/listings/{listing_id}/enrich?analyze_images=true`

### Listing Descriptions (`enrichment_listing_descriptions.py`)
- **Model**: Gemini 1.0 Pro
- **Purpose**: Generate MLS-compliant listing descriptions (public_remarks, syndication_remarks)
- **Endpoint**: `POST /api/enrichment/listings/{listing_id}/enrich?generate_descriptions=true`

## Model Selection

You can override the default models using environment variables:

- `VISION_MODEL`: For document extraction (default: `gemini-2.5-flash`)
- `IMAGE_VISION_MODEL`: For image analysis (default: `gemini-2.5-flash`)
- `LLM_MODEL`: For text generation (default: `gemini-2.5-flash`)
- `POPPLER_PATH`: Path to Poppler bin directory if not in PATH (Windows only)

## Error Handling

If the Gemini API key is not configured:
- Document extraction will fail with a clear error message
- Image analysis will return default values (room_label: "other", empty description)
- Listing descriptions will fall back to template-based generation

## Testing

After setup, test the endpoints:

1. **Document Extraction**:
   ```bash
   POST /api/extraction/listings/{listing_id}/extract?method=vision_only
   ```

2. **Image Analysis**:
   ```bash
   POST /api/enrichment/listings/{listing_id}/enrich?analyze_images=true
   ```

3. **Description Generation**:
   ```bash
   POST /api/enrichment/listings/{listing_id}/enrich?generate_descriptions=true
   ```

## Notes

- This project uses the new `google-genai` package (replaces deprecated `google-generativeai`)
- All tasks use Gemini 2.5 Flash for optimal speed and cost-effectiveness
- Gemini 2.5 Flash supports both text and vision/image inputs natively
- The API automatically handles image encoding and prompt formatting
- Install the new package: `pip install google-genai>=0.2.0`
- For Poppler (PDF to image conversion), set `POPPLER_PATH` environment variable if not in PATH
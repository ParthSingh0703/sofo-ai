# MLS Automation Service

Playwright-based browser automation for MLS form autofill.

## Overview

This service provides browser automation capabilities to autofill MLS listing forms using mapped JSON data. It supports both known MLS systems (with stored mappings) and new MLS systems (with dynamic discovery).

## Architecture

### Components

1. **`models.py`**: Data models for automation configuration and results
   - `AutomationConfig`: Configuration for automation run
   - `AutomationResult`: Results and statistics from automation
   - `MLSFieldSelector`: Field selector configuration
   - `MLSMappingConfig`: Stored mapping configuration

2. **`automation_service.py`**: Main automation service
   - `prepare_automation_config()`: Validates canonical and loads mapping
   - `start_automation()`: Orchestrates the automation flow
   - Helper functions for login detection, field filling, image upload, etc.

3. **API Endpoint**: `POST /api/automation/listings/{listing_id}/start`
   - Triggered by user clicking "Start Automation"
   - Requires validated canonical and prepared MLS mapping

## Workflow

1. **Prerequisites**:
   - Canonical listing must be validated (locked)
   - MLS mapping must be prepared via `GET /api/listings/{listing_id}/mls-fields`

2. **User Action**: User selects MLS system and clicks "Start Automation"

3. **Automation Flow**:
   - Launch Playwright browser (headed mode)
   - Detect and skip login if already logged in
   - Navigate to MLS listing form
   - Fill fields from mapped JSON
   - Upload images with room types and descriptions
   - Save listing (never submit)
   - Return results

## Implementation Status

### ✅ Completed

- [x] Data models structure
- [x] API endpoint structure
- [x] Basic automation service skeleton
- [x] Login detection skeleton
- [x] Validation checks (canonical must be validated)

### 🚧 In Progress / Placeholders

- [ ] Full login detection logic (detect logged-in state)
- [ ] Manual login wait logic
- [ ] MLS field discovery (for new MLS systems)
- [ ] Field mapping loading (for known MLS systems)
- [ ] Field filling logic (text, number, dropdown, checkbox, etc.)
- [ ] Enum handling with AI assistance
- [ ] Image upload with room types
- [ ] Save button detection and clicking
- [ ] Error handling and retry logic
- [ ] Learning and persistence for new MLS systems

## Next Steps

1. **Field Mapping Implementation**:
   - Implement `_fill_mls_fields()` to fill form fields
   - Handle different field types (text, number, dropdown, checkbox, radio, multi-select, date)
   - Map JSON keys to form selectors

2. **Enum Handling**:
   - Read available options from dropdowns
   - Match against mapped JSON values
   - Use AI for semantic similarity matching
   - Handle confidence thresholds

3. **Image Upload**:
   - Navigate to media/photos section
   - Upload images from canonical
   - Set room types and descriptions
   - Set primary image

4. **MLS-Specific Mappings**:
   - Create mapping configurations for known MLS systems (starting with Unlock MLS)
   - Store selectors and field mappings
   - Support learning and persistence for new MLS systems

5. **Testing**:
   - Test with known MLS systems
   - Test login detection
   - Test field filling
   - Test image upload
   - Test save (not submit) logic

## Dependencies

- `playwright>=1.40.0`: Browser automation library
- Requires: `playwright install chromium` after installation

## Usage

```python
from services.api.services.mls_automation.automation_service import (
    prepare_automation_config,
    start_automation
)

# Prepare config (validates canonical is validated)
config = prepare_automation_config(listing_id, "unlock_mls")

# Start automation (must be called after user clicks "Start Automation")
result = start_automation(config)

# Check results
print(f"Status: {result.status}")
print(f"Fields filled: {result.fields_filled}")
print(f"Images uploaded: {result.images_updated}")
```

## API Usage

```bash
# 1. Validate canonical (prerequisite)
POST /api/listings/{listing_id}/validate

# 2. Prepare MLS mapping (prerequisite)
GET /api/listings/{listing_id}/mls-fields?mls_system=unlock_mls

# 3. Start automation (after user clicks "Start Automation")
POST /api/automation/listings/{listing_id}/start?mls_system=unlock_mls
```

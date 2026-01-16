# Frontend Application Flow Documentation

## Overview
This document outlines the complete user flow and state management for the MLS Automation frontend application.

## Technology Stack
- **React** - UI framework
- **Redux Toolkit** - State management
- **React Router** - Navigation/routing
- **TanStack Query** - Data fetching and caching
- **Axios** - HTTP client
- **Tailwind CSS** - Styling
- **TypeScript** - Type safety

## Application Flow

### 1. Create Listing Page (`/`)
**Purpose**: Initial landing page where users create a new listing

**User Actions**:
- User clicks "Create New Listing" button
- System creates a new listing via API (`POST /api/listings?user_id={userId}`)
- On success, user is redirected to Upload Documents page

**State Changes**:
- `listingsSlice.currentListingId` - Set to newly created listing ID
- `listingsSlice.isLoading` - Set to true during creation, false after

**Navigation**:
- On success: Navigate to `/upload/{listingId}`
- On error: Stay on page, show error toast

**API Endpoint**:
- `POST /api/listings?user_id={userId}`
- Response: `{ listing_id: string, status: "draft" }`

---

### 2. Upload Documents Page (`/upload/:listingId`)
**Purpose**: Upload documents and images for extraction

**User Actions**:
- Upload documents (PDF, TXT, DOCX)
- Upload images (JPG, JPEG, PNG)
- Click "Start AI Engine" button

**State Changes**:
- `listingsSlice.uploadedFiles` - Track uploaded files
- `listingsSlice.uploadProgress` - Track upload progress per file

**Navigation**:
- On "Start AI Engine": Navigate to `/processing/{listingId}`

**API Endpoints**:
- `POST /api/documents/listings/{listingId}` - Upload document
- `POST /api/images/listings/{listingId}` - Upload image
- `POST /api/extraction/listings/{listingId}/extract` - Start extraction

---

### 3. Processing Page (`/processing/:listingId`)
**Purpose**: Show extraction and enrichment progress

**User Actions**:
- View progress of AI extraction
- View progress of enrichment (geo-intelligence, image analysis, descriptions)

**State Changes**:
- `listingsSlice.extractionStatus` - Track extraction progress
- `listingsSlice.enrichmentStatus` - Track enrichment progress

**Navigation**:
- On completion: Auto-navigate to `/review/{listingId}`

**API Endpoints**:
- `POST /api/extraction/listings/{listingId}/extract` - Extraction
- `POST /api/enrichment/listings/{listingId}/enrich` - Enrichment

---

### 4. Review Canonical Page (`/review/:listingId`)
**Purpose**: Review and edit extracted canonical data

**User Actions**:
- Review all extracted fields
- Edit any field values
- Validate the canonical (locks it for MLS mapping)

**State Changes**:
- `listingsSlice.canonical` - Store canonical data
- `listingsSlice.isValidated` - Track validation status

**Navigation**:
- On "Validate": Navigate to `/media/{listingId}`
- On "Save Changes": Stay on page, update canonical

**API Endpoints**:
- `GET /api/listings/{listingId}/canonical` - Get canonical
- `PUT /api/listings/{listingId}/canonical` - Update canonical
- `POST /api/listings/{listingId}/validate?user_id={userId}` - Validate canonical

---

### 5. Media Management Page (`/media/:listingId`)
**Purpose**: Review and edit image labels, descriptions, and room types

**User Actions**:
- Review AI-suggested labels and descriptions
- Edit image labels
- Edit image descriptions
- Edit room types
- Reorder images

**State Changes**:
- `listingsSlice.mediaImages` - Store image metadata
- `listingsSlice.imageSequence` - Track image order

**Navigation**:
- On "Continue": Navigate to `/mls/{listingId}`

**API Endpoints**:
- `GET /api/images/listings/{listingId}` - Get all images
- `PUT /api/listings/{listingId}/canonical` - Update image metadata in canonical

---

### 6. MLS Mapping & Automation Page (`/mls/:listingId`)
**Purpose**: Select MLS system, review mapping, and trigger automation

**User Actions**:
- Select MLS system (e.g., Unlock MLS)
- Review mapped fields
- Click "Start Automation" button
- Monitor automation progress

**State Changes**:
- `listingsSlice.selectedMLS` - Selected MLS system
- `listingsSlice.mlsMapping` - Mapped fields for selected MLS
- `listingsSlice.automationStatus` - Automation progress

**Navigation**:
- On automation start: Show progress modal
- On completion: Show success message

**API Endpoints**:
- `GET /api/listings/{listingId}/mls-fields?mls_system={system}` - Get MLS mapping
- `GET /api/listings/{listingId}/mls-mapping/{mlsSystem}` - Get saved mapping
- `POST /api/automation/listings/{listingId}/start?mls_system={system}&mls_url={url}` - Start automation

---

## Redux State Structure

```typescript
interface ListingsState {
  currentListingId: string | null;
  isLoading: boolean;
  error: string | null;
  canonical: CanonicalListing | null;
  isValidated: boolean;
  uploadedFiles: FileItem[];
  uploadProgress: Record<string, number>;
  extractionStatus: 'idle' | 'extracting' | 'complete' | 'error';
  enrichmentStatus: 'idle' | 'enriching' | 'complete' | 'error';
  mediaImages: MediaImage[];
  selectedMLS: string | null;
  mlsMapping: any | null;
  automationStatus: AutomationStatus | null;
}

interface UIState {
  toasts: Toast[];
  sidebarOpen: boolean;
}
```

## Navigation Flow Diagram

```
[Create Listing] (/)
    ↓ (Create listing)
[Upload Documents] (/upload/:listingId)
    ↓ (Start AI Engine)
[Processing] (/processing/:listingId)
    ↓ (Auto-navigate on completion)
[Review Canonical] (/review/:listingId)
    ↓ (Validate)
[Media Management] (/media/:listingId)
    ↓ (Continue)
[MLS Automation] (/mls/:listingId)
    ↓ (Start Automation)
[Automation Progress Modal]
    ↓ (Complete)
[Success Screen]
```

## Key State Management Rules

1. **Listing ID**: Always stored in Redux and URL params for consistency
2. **Canonical Data**: Fetched and cached using TanStack Query
3. **File Uploads**: Tracked in Redux with progress updates
4. **Validation**: Once canonical is validated, it becomes read-only
5. **Navigation**: Always use React Router's `navigate()` with replace option when appropriate

## Error Handling

- All API errors are caught and displayed as toast notifications
- Network errors show user-friendly messages
- Validation errors are shown inline on forms
- Critical errors trigger error boundaries

## Loading States

- Each page shows loading spinners during API calls
- Progress indicators for file uploads
- Progress bars for extraction/enrichment processes
- Disabled buttons during operations

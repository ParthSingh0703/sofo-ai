# Review Page Field Mapping

This document maps the UI fields in the Review Page to the canonical JSON structure.

## Header Stats

| UI Field | Canonical Path | Type | Notes |
|----------|---------------|------|-------|
| listPrice | `listing_meta.list_price` | number | Format as currency (e.g., $1.85M) |
| agreementType | `listing_meta.listing_agreement` | string | "Right To Sell" or other values |
| expirationDate | `listing_meta.expiration_date` | date-time | Format as MM/DD/YYYY |
| yearBuilt | `property.year_built` | integer | Display as year |
| ownership | `property.ownership_type` | string | Display as-is |

## 1. Agreement & Listing Services

| UI Field | Canonical Path | Type | Notes |
|----------|---------------|------|-------|
| listingServices | `listing_meta.listing_service` | string | "Full Service" or other values |
| specialConditions | `listing_meta.special_conditions` | string | "None" if null/empty |
| propertySubType | `property.property_sub_type` | string | "Condo", "Single Family", etc. |
| listingAgent | `agents.listing_agent` | string | Agent name |

## 2. Property Identity & Location

| UI Field | Canonical Path | Type | Notes |
|----------|---------------|------|-------|
| zipCode | `location.zip_code` | string | 5-digit zip code |
| parcelNumber | `location.parcel_number` | string | Parcel identifier |
| subdivision | `location.subdivision` | string | Subdivision name |
| legalDescription | `location.tax_legal_description` | string | Legal description text |

**NOT MAPPED (Available in canonical but not in UI):**
- `location.street_number`
- `location.street_name`
- `location.street_address` (used in header)
- `location.city` (used in header)
- `location.county` (used in header)
- `location.state` (used in header)
- `location.tax_lot`
- `location.mla_area`
- `location.flood_plain`
- `location.etj`
- `location.poi` (array of POIs)

## 3. Physical & Architectural Specs

| UI Field | Canonical Path | Type | Notes |
|----------|---------------|------|-------|
| constructionType | `property.construction_material` | array | Join array items with ", " (e.g., "Steel & Concrete") |
| foundation | `property.foundation_details` | array | Join array items with ", " (e.g., "Slab on Grade") |
| roofType | `property.roof` | array | Join array items with ", " (e.g., "Standing Seam Metal") |
| propertyCondition | `property.property_condition` | string | "Excellent", "Good", "Resale", "New Construction", etc. |
| lotSizeAcres | `property.lot_size_acres` | number | Format as decimal (e.g., "0.25") |
| directionFaces | `property.direction_faces` | string | "North", "South", etc. |
| garageSpaces | `property.garage_spaces` | number | Display as integer |
| totalParking | `property.parking_total` | number | Display as integer |

**NOT MAPPED (Available in canonical but not in UI):**
- `property.levels` (used in header specs)
- `property.main_level_bedrooms` (used in header specs)
- `property.other_level_bedrooms` (used in header specs)
- `property.bathrooms_full` (used in header specs)
- `property.bathrooms_half` (used in header specs)
- `property.living_area_sqft` (used in header specs)
- `property.view`
- `property.distance_to_water`
- `property.waterfront_features`
- `property.restrictions`
- `property.lot_features` (array)

## 4. Interior & Rooms

| UI Field | Canonical Path | Type | Notes |
|----------|---------------|------|-------|
| livingRoom | `property.living_room` | string | "1" or description |
| diningRoom | `property.dining_room` | string | "1" or description |
| fireplaces | `features.fireplaces` | array | Join array items with ", " (e.g., "1") |
| appliances | `features.appliances` | array | Join array items with ", " (e.g., "Sub-Zero Fridge, Wolf Range") |
| waterSource | `utilities.water_source` | array | Join array items with ", " (e.g., "Public") |
| sewer | `utilities.sewer` | array | Join array items with ", " (e.g., "Public Sewer") |
| heating | `utilities.heating` | array | Join array items with ", " (e.g., "Central") |
| cooling | `utilities.cooling` | array | Join array items with ", " (e.g., "Central Air") |
| flooring | `features.flooring` | array | Join array items with ", " (e.g., "Hardwood, Polished Concrete") |

**NOT MAPPED (Available in canonical but not in UI):**
- `features.interior_features` (array)
- `features.exterior_features` (array)
- `features.patio_porch_features` (array)
- `features.accessibility_features` (array)
- `features.horse_amenities` (array)
- `features.other_structures` (array)
- `features.pool_features` (array)
- `features.guest_accommodations` (string)
- `features.window_features` (array)
- `features.security_features` (array)
- `features.laundry_location` (string)
- `features.fencing` (string)
- `features.community_features` (array)
- `utilities.utilities` (array)
- `utilities.documents_available` (array)
- `utilities.disclosures` (array)
- `green_energy.green_energy` (array)
- `green_energy.green_sustainability` (array)

## 5. Financials

| UI Field | Canonical Path | Type | Notes |
|----------|---------------|------|-------|
| association | `financial.association` | boolean | Display as "Yes" or "No" |
| associationName | `financial.association_name` | string | HOA name |
| associationFee | `financial.association_fee` | number | Format as currency (e.g., "$150") |
| associationAmount | `financial.association_amount` | number | Format as currency/year (e.g., "$1800/yr") |
| acceptableFinancing | `financial.acceptable_financing` | array | Join array items with ", " (e.g., "Conventional, Cash, VA") |
| estimatedTax | `financial.estimated_tax` | number | Format as currency (e.g., "$24,500") |
| taxYear | `financial.tax_year` | integer | Display as year (e.g., "2023") |
| taxAnnualAmount | `financial.tax_annual_amount` | number | Format as currency (e.g., "$24,500") |
| taxAssessedValue | `financial.tax_assessed_value` | number | Format as currency (e.g., "$1,200,000") |
| taxRate | `financial.tax_rate` | number | Format as percentage (e.g., "1.98%") |
| occupantType | `showing.occupant_type` | string | "Owner", "Tenant", etc. |
| ownerName | `showing.owner_name` | string | Owner's name |
| lockboxType | `showing.lockbox_type` | string | "Supra", etc. |
| showingInstructions | `showing.showing_instructions` | string | Instructions text |

**NOT MAPPED (Available in canonical but not in UI):**
- `financial.buyer_incentive` (string)
- `financial.tax_exemptions` (array)
- `financial.possession` (string)
- `financial.seller_contributions` (boolean)
- `financial.intermediary` (boolean)
- `showing.showing_requirements` (array)
- `showing.lockbox_location` (string)

## 6. Location & Environmental

| UI Field | Canonical Path | Type | Notes |
|----------|---------------|------|-------|
| latitude | `location.latitude` | number | Display as decimal (e.g., "30.2672") |
| longitude | `location.longitude` | number | Display as decimal (e.g., "-97.7431") |
| propertyDescription | `remarks.ai_property_description` | string | AI-generated property description |

**NOT MAPPED (Available in canonical but not in UI):**
- `location.poi` (array) - Points of Interest
- `remarks.directions` (string)

## 7. Marketing Remarks

| UI Field | Canonical Path | Type | Notes |
|----------|---------------|------|-------|
| publicRemarks | `remarks.public_remarks` | string | Public marketing remarks |
| privateRemarks | `remarks.private_remarks` | string | Private agent remarks |

**NOT MAPPED (Available in canonical but not in UI):**
- `remarks.syndication_remarks` (string)

## Summary

### Total Fields Mapped: 40
### Total Fields in Canonical (not mapped): ~50+

### Notes:
1. Array fields are joined with ", " separator for display
2. Number fields may need formatting (currency, percentage, etc.)
3. Boolean fields are displayed as "Yes"/"No"
4. Date-time fields are formatted as MM/DD/YYYY
5. Header stats combine multiple canonical fields (bedrooms, bathrooms, sqft, floors)

### Header Address & Specs:
- Address: `location.street_address`
- County, City, State: `location.county`, `location.city`, `location.state`
- Specs: Calculated from `property.main_level_bedrooms + property.other_level_bedrooms`, `property.bathrooms_full + property.bathrooms_half`, `property.living_area_sqft`, `property.levels`

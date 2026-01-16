from pydantic import BaseModel, Field, HttpUrl, field_serializer, field_validator
from typing import Optional, List, Union, Dict, Any
from datetime import datetime
from enum import Enum


def _parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Parse a date string into a datetime object.
    Handles common date formats used in MLS documents, prioritizing US format.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    # Common date formats to try (US format prioritized)
    date_formats = [
        "%m/%d/%Y",            # 01/10/2026 (US format - most common in MLS documents)
        "%m/%d/%y",             # 01/10/26 (US format with 2-digit year)
        "%m-%d-%Y",             # 01-10-2026 (US format with dashes)
        "%m-%d-%y",             # 01-10-26 (US format with dashes, 2-digit year)
        "%Y-%m-%d",             # 2026-01-10 (ISO format)
        "%Y/%m/%d",             # 2026/01/10
        "%B %d, %Y",            # January 10, 2026
        "%b %d, %Y",            # Jan 10, 2026
        "%d %B %Y",             # 10 January 2026
        "%d %b %Y",             # 10 Jan 2026
    ]
    
    # Try parsing with specific formats first
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    # Try ISO format and other common formats
    try:
        # Try ISO format (2026-01-10T00:00:00 or 2026-01-10)
        if 'T' in date_str:
            return datetime.fromisoformat(date_str.strip().replace('Z', '+00:00'))
        else:
            # Try just the date part
            return datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except (ValueError, TypeError):
        # If all parsing fails, return None
        return None


# ===============================
# STATE / LIFECYCLE
# ===============================

class CanonicalMode(str, Enum):
    DRAFT = "draft"
    LOCKED = "locked"


class CanonicalState(BaseModel):
    mode: CanonicalMode = CanonicalMode.DRAFT
    validated: bool = False
    locked: bool = False

    validated_at: Optional[datetime] = None
    validated_by: Optional[str] = None  # user_id
    
    @field_validator('validated_at', mode='before')
    @classmethod
    def parse_validated_at(cls, value: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse validated_at from US format (MM/DD/YYYY) or other formats."""
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return _parse_date_string(value)
        return value
    
    @field_serializer('validated_at')
    def serialize_validated_at(self, value: Optional[datetime], _info) -> Optional[str]:
        """Serialize validated_at to US format (MM/DD/YYYY)."""
        if value is None:
            return None
        return value.strftime("%m/%d/%Y")


# ===============================
# LISTING META
# ===============================

class ListingMeta(BaseModel):
    flex_listing: Optional[bool] = None
    listing_agreement: Optional[str] = None
    listing_agreement_document: Optional[str] = None
    listing_service: Optional[str] = None
    list_price: Optional[float] = None
    expiration_date: Optional[datetime] = None
    special_conditions: Optional[str] = None
    listing_special_conditions: List[str] = []
    tentative_close_date: Optional[datetime] = None
    auction_date: Optional[datetime] = None
    
    @field_validator('expiration_date', mode='before')
    @classmethod
    def parse_expiration_date(cls, value: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse expiration_date from US format (MM/DD/YYYY) or other formats."""
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return _parse_date_string(value)
        return value
    
    @field_validator('tentative_close_date', mode='before')
    @classmethod
    def parse_tentative_close_date(cls, value: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse tentative_close_date from US format (MM/DD/YYYY) or other formats."""
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return _parse_date_string(value)
        return value
    
    @field_validator('auction_date', mode='before')
    @classmethod
    def parse_auction_date(cls, value: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse auction_date from US format (MM/DD/YYYY) or other formats."""
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return _parse_date_string(value)
        return value
    
    @field_serializer('expiration_date')
    def serialize_expiration_date(self, value: Optional[datetime], _info) -> Optional[str]:
        """Serialize expiration_date to US format (MM/DD/YYYY)."""
        if value is None:
            return None
        return value.strftime("%m/%d/%Y")
    
    @field_serializer('tentative_close_date')
    def serialize_tentative_close_date(self, value: Optional[datetime], _info) -> Optional[str]:
        """Serialize tentative_close_date to date format (YYYY-MM-DD)."""
        if value is None:
            return None
        return value.strftime("%Y-%m-%d")
    
    @field_serializer('auction_date')
    def serialize_auction_date(self, value: Optional[datetime], _info) -> Optional[str]:
        """Serialize auction_date to date format (YYYY-MM-DD)."""
        if value is None:
            return None
        return value.strftime("%Y-%m-%d")


# ===============================
# LOCATION
# ===============================

class Location(BaseModel):
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    street_suffix: Optional[str] = None
    street_address: Optional[str] = None

    city: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None

    subdivision: Optional[str] = None
    tax_legal_description: Optional[str] = None
    tax_lot: Optional[str] = None
    parcel_number: Optional[str] = None

    additional_parcel: Optional[bool] = None
    additional_parcel_description: Optional[str] = None

    mla_area: Optional[str] = None
    flood_plain: Optional[bool] = None
    etj: Optional[bool] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    poi: List[Dict[str, Any]] = []  # Points of interest from geo-intelligence


# ===============================
# SCHOOLS
# ===============================

class Schools(BaseModel):
    elementary_school_district: Optional[str] = None
    middle_junior_school: Optional[str] = None
    high_school: Optional[str] = None
    school_district: Optional[str] = None


# ===============================
# PROPERTY
# ===============================

class Property(BaseModel):
    property_sub_type: Optional[str] = None
    ownership_type: Optional[str] = None

    levels: Optional[int] = None
    main_level_bedrooms: Optional[int] = None
    other_level_bedrooms: Optional[int] = None
    bedrooms_total: Optional[int] = None

    year_built: Optional[int] = None
    year_built_source: Optional[str] = None

    bathrooms_full: Optional[int] = None
    bathrooms_half: Optional[int] = None
    bathrooms_total: Optional[float] = None

    living_area_sqft: Optional[int] = None
    living_area_source: Optional[str] = None

    garage_spaces: Optional[float] = None
    parking_total: Optional[float] = None
    direction_faces: Optional[str] = None

    lot_size_acres: Optional[float] = None
    property_condition: Optional[str] = None
    view: Optional[str] = None
    distance_to_water: Optional[float] = None
    waterfront_features: Optional[str] = None
    restrictions: Optional[str] = None
    
    living_room: Optional[str] = None
    dining_room: Optional[str] = None

    construction_material: List[str] = []
    foundation_details: List[str] = []
    roof: List[str] = []
    lot_features: List[str] = []


# ===============================
# FEATURES
# ===============================

class Features(BaseModel):
    interior_features: List[str] = []
    exterior_features: List[str] = []

    patio_porch_features: List[str] = []
    fireplaces: List[str] = []
    flooring: List[str] = []

    accessibility_features: List[str] = []
    horse_amenities: List[str] = []
    other_structures: List[str] = []

    appliances: List[str] = []
    pool_features: List[str] = []
    guest_accommodations: Optional[str] = None

    window_features: List[str] = []
    security_features: List[str] = []
    laundry_location: Optional[str] = None
    fencing: Optional[str] = None
    community_features: List[str] = []
    parking_features: List[str] = []


# ===============================
# UTILITIES
# ===============================

class Utilities(BaseModel):
    utilities: List[str] = []
    heating: List[str] = []
    cooling: List[str] = []
    water_source: List[str] = []
    sewer: List[str] = []
    documents_available: List[str] = []
    disclosures: List[str] = []


# ===============================
# GREEN ENERGY
# ===============================

class GreenEnergy(BaseModel):
    green_energy: List[str] = []
    green_sustainability: List[str] = []


# ===============================
# FINANCIAL
# ===============================

class Financial(BaseModel):
    association: Optional[bool] = None
    association_name: Optional[str] = None
    association_fee: Optional[float] = None
    association_amount: Optional[float] = None

    acceptable_financing: List[str] = []

    estimated_tax: Optional[float] = None
    tax_year: Optional[int] = None
    tax_annual_amount: Optional[float] = None
    tax_assessed_value: Optional[float] = None
    tax_rate: Optional[float] = None

    buyer_incentive: Optional[str] = None
    tax_exemptions: List[str] = []

    possession: Optional[str] = None
    seller_contributions: Optional[bool] = None
    intermediary: Optional[bool] = None


# ===============================
# SHOWING
# ===============================

class Showing(BaseModel):
    occupant_type: Optional[str] = None
    showing_requirements: List[str] = []

    owner_name: Optional[str] = None
    lockbox_type: Optional[str] = None
    lockbox_location: Optional[str] = None

    showing_instructions: Optional[str] = None


# ===============================
# AGENTS
# ===============================

class Agents(BaseModel):
    listing_agent: Optional[str] = None
    co_listing_agent: Optional[str] = None


# ===============================
# REMARKS & MEDIA
# ===============================

class Remarks(BaseModel):
    directions: Optional[str] = None
    private_remarks: Optional[str] = None
    public_remarks: Optional[str] = None
    syndication_remarks: Optional[str] = None
    ai_property_description: Optional[str] = None  # AI-generated attractive property description (< 1500 chars)


class ImageMedia(BaseModel):
    """
    Image media information with AI-suggested and user-edited descriptions, labels, and room types.
    When canonical is locked (validated), descriptions, labels, and room types cannot be edited.
    """
    image_id: str  # UUID reference to listing_images.id
    ai_suggested_description: Optional[str] = None  # From image_ai_analysis.description
    description: Optional[str] = None  # User-edited final description
    ai_suggested_label: Optional[str] = None  # From listing_images.ai_suggested_label
    label: Optional[str] = None  # User-edited final label
    ai_suggested_room_type: Optional[str] = None  # From enrichment room_label (detected room/portion)
    room_type: Optional[str] = None  # User-edited final room type
    is_primary: bool = False
    display_order: int = 0


class Media(BaseModel):
    branded_virtual_tour_url: Optional[HttpUrl] = None
    unbranded_virtual_tour_url: Optional[HttpUrl] = None
    branded_video_tour_url: Optional[HttpUrl] = None
    unbranded_video_tour_url: Optional[HttpUrl] = None
    media_images: List[ImageMedia] = []  # List of images with descriptions


# ===============================
# INTERNET
# ===============================

class InternetSettings(BaseModel):
    internet_entire_listing_display: Optional[bool] = None
    internet_automated_valuation_display: Optional[bool] = None
    internet_consumer_comment: Optional[bool] = None
    internet_address_display: Optional[bool] = None


# ===============================
# MASTER CANONICAL LISTING
# ===============================

class CanonicalListing(BaseModel):
    schema_version: str = "1.0"

    state: CanonicalState = CanonicalState()

    listing_meta: ListingMeta = ListingMeta()
    location: Location = Location()
    schools: Schools = Schools()
    property: Property = Property()
    features: Features = Features()
    utilities: Utilities = Utilities()
    green_energy: GreenEnergy = GreenEnergy()
    financial: Financial = Financial()
    showing: Showing = Showing()
    agents: Agents = Agents()
    remarks: Remarks = Remarks()
    media: Media = Media()
    internet_settings: InternetSettings = InternetSettings()

    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('updated_at', mode='before')
    @classmethod
    def parse_updated_at(cls, value: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse updated_at from US format (MM/DD/YYYY) or other formats."""
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            parsed = _parse_date_string(value)
            # If parsing fails, use current time as fallback
            return parsed if parsed is not None else datetime.utcnow()
        return value
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, value: datetime, _info) -> str:
        """Serialize updated_at to US format (MM/DD/YYYY)."""
        return value.strftime("%m/%d/%Y")
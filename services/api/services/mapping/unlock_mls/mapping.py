"""
Unlock MLS field mapping configuration.
Maps CanonicalListing fields to Unlock MLS form fields.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class MLSFieldMapping:
    """Mapping configuration for a single MLS field."""
    canonical_path: str
    confidence: float
    type: str  # string, number, boolean, enum, multi_enum
    enum_values: Optional[List[str]] = None
    default_value: Optional[Any] = None
    transform_fn: Optional[str] = None  # Name of transformation function
    notes: Optional[str] = None


# Field mappings organized by MLS section
UNLOCK_MLS_FIELD_MAPPINGS: Dict[str, Dict[str, MLSFieldMapping]] = {
    "listing_location": {
        "Street Address": MLSFieldMapping(
            canonical_path="location.street_address",
            confidence=0.95,
            type="string"
        ),
        "Flex Listing": MLSFieldMapping(
            canonical_path=None,
            confidence=1.0,
            type="boolean",
            default_value=False
        ),
        "Listing Agreement": MLSFieldMapping(
            canonical_path="listing_meta.listing_agreement",
            confidence=0.9,
            type="enum"
        ),
        "Listing Service": MLSFieldMapping(
            canonical_path="listing_meta.listing_service",
            confidence=0.9,
            type="enum"
        ),
        "List Price": MLSFieldMapping(
            canonical_path="listing_meta.list_price",
            confidence=0.95,
            type="number"
        ),
        "Expiration Date": MLSFieldMapping(
            canonical_path="listing_meta.expiration_date",
            confidence=0.9,
            type="string",
            transform_fn="format_date"
        ),
        "Tentative Close Date": MLSFieldMapping(
            canonical_path="listing_meta.tentative_close_date",
            confidence=0.85,
            type="string",
            transform_fn="format_date"
        ),
        "Auction Date": MLSFieldMapping(
            canonical_path="listing_meta.auction_date",
            confidence=0.85,
            type="string",
            transform_fn="format_date"
        ),
        # "Special Listing Conditions": MLSFieldMapping(
        #     canonical_path="listing_meta.special_conditions",
        #     confidence=0.85,
        #     type="enum"
        # ),
        "Listing Special Conditions": MLSFieldMapping(
            canonical_path="listing_meta.listing_special_conditions",
            confidence=0.85,
            type="multi_enum"
        ),
        "Listing Agreement Document": MLSFieldMapping(
            canonical_path="listing_meta.listing_agreement_document",
            confidence=0.9,
            type="enum"
        ),
        "Street #": MLSFieldMapping(
            canonical_path="location.street_number",
            confidence=0.9, 
            type="string"
        ),
        "Street Name": MLSFieldMapping(
            canonical_path="location.street_name",
            confidence=0.9,
            type="string"
        ),
        "Street Suffix": MLSFieldMapping(
            canonical_path="location.street_suffix",
            confidence=0.9,
            type="string"
        ),
        "County": MLSFieldMapping(
            canonical_path="location.county",
            confidence=0.9,
            type="enum"
        ),
        "City": MLSFieldMapping(
            canonical_path="location.city",
            confidence=0.95,
            type="enum"
        ),
        "State": MLSFieldMapping(
            canonical_path="location.state",
            confidence=0.95,
            type="enum"
        ),
        "Country": MLSFieldMapping(
            canonical_path=None,
            confidence=1.0,
            type="enum",
            default_value="United States of America"
        ),
        "Zip Code": MLSFieldMapping(
            canonical_path="location.zip_code",
            confidence=0.95,
            type="number",
            transform_fn="zip_to_number"
        ),
        "Subdivision": MLSFieldMapping(
            canonical_path="location.subdivision",
            confidence=0.85,
            type="string"
        ),
        "Tax Legal Description": MLSFieldMapping(
            canonical_path="location.tax_legal_description",
            confidence=0.8,
            type="string"
        ),
        "Tax Lot": MLSFieldMapping(
            canonical_path="location.tax_lot",
            confidence=0.85,
            type="number",
            transform_fn="string_to_number"
        ),
        "Parcel Number (PID)": MLSFieldMapping(
            canonical_path="location.parcel_number",
            confidence=0.85,
            type="number",
            transform_fn="string_to_number"
        ),
        "Additional Parcel": MLSFieldMapping(
            canonical_path="location.additional_parcel",
            confidence=0.9,
            type="boolean"
        ),
        "Additional Parcel Description": MLSFieldMapping(
            canonical_path="location.additional_parcel_description",
            confidence=0.8,
            type="string"
        ),
        "MLA Area": MLSFieldMapping(
            canonical_path="location.mla_area",
            confidence=0.85,
            type="enum"
        ),
        "FEMA Flood Plain": MLSFieldMapping(
            canonical_path="location.flood_plain",
            confidence=0.9,
            type="boolean"
        ),
        "ETJ": MLSFieldMapping(
            canonical_path="location.etj",
            confidence=0.8,
            type="enum",
            default_value="See Remarks",
            notes="Default to 'See Remarks' if not provided"
        ),
        "Latitude": MLSFieldMapping(
            canonical_path="location.latitude",
            confidence=0.95,
            type="number"
        ),
        "Longitude": MLSFieldMapping(
            canonical_path="location.longitude",
            confidence=0.95,
            type="number"
        ),
        "School District": MLSFieldMapping(
            canonical_path="schools.school_district",
            confidence=0.9,
            type="enum"
        ),
        "Elementary": MLSFieldMapping(
            canonical_path="schools.elementary_school_district",
            confidence=0.9,
            type="string"
        ),
        "Middle or Junior": MLSFieldMapping(
            canonical_path="schools.middle_junior_school",
            confidence=0.9,
            type="string"
        ),
        "High School": MLSFieldMapping(
            canonical_path="schools.high_school",
            confidence=0.9,
            type="string"
        ),
    },
    
    "general": {
        "Property Sub Type": MLSFieldMapping(
            canonical_path="property.property_sub_type",
            confidence=0.95,
            type="enum"
        ),
        "Ownership Type": MLSFieldMapping(
            canonical_path="property.ownership_type",
            confidence=0.9,
            type="enum",
            transform_fn="infer_ownership_type"
        ),
        "Levels": MLSFieldMapping(
            canonical_path="property.levels",
            confidence=0.9,
            type="number"
        ),
        "Main Level Bedrooms": MLSFieldMapping(
            canonical_path="property.main_level_bedrooms",
            confidence=0.9,
            type="number"
        ),
        "Other Level Beds": MLSFieldMapping(
            canonical_path="property.other_level_bedrooms",
            confidence=0.9,
            type="number"
        ),
        "Total Bedrooms": MLSFieldMapping(
            canonical_path="property.bedrooms_total",
            confidence=0.95,
            type="number"
        ),
        "Year Built": MLSFieldMapping(
            canonical_path="property.year_built",
            confidence=0.9,
            type="number"
        ),
        "Year Built Source": MLSFieldMapping(
            canonical_path="property.year_built_source",
            confidence=0.85,
            type="enum",
            default_value="Public Records"
        ),
        "Bathrooms Full": MLSFieldMapping(
            canonical_path="property.bathrooms_full",
            confidence=0.9,
            type="number"
        ),
        "Bathrooms Half": MLSFieldMapping(
            canonical_path="property.bathrooms_half",
            confidence=0.9,
            type="number"
        ),
        "Total Bathrooms": MLSFieldMapping(
            canonical_path="property.bathrooms_total",
            confidence=0.95,
            type="number"
        ),
        "Living Room": MLSFieldMapping(
            canonical_path="property.living_room",
            confidence=0.85,
            type="number",
            transform_fn="string_to_number"
        ),
        "Dining Room": MLSFieldMapping(
            canonical_path="property.dining_room",
            confidence=0.85,
            type="number",
            transform_fn="string_to_number"
        ),
        "Living Area": MLSFieldMapping(
            canonical_path="property.living_area_sqft",
            confidence=0.95,
            type="number"
        ),
        "Living Area Source": MLSFieldMapping(
            canonical_path="property.living_area_source",
            confidence=0.85,
            type="enum",
            default_value="Public Records"
        ),
        "Garage Spaces": MLSFieldMapping(
            canonical_path="property.garage_spaces",
            confidence=0.9,
            type="number"
        ),
        "Parking Total": MLSFieldMapping(
            canonical_path="property.parking_total",
            confidence=0.9,
            type="number"
        ),
        "Direction Faces": MLSFieldMapping(
            canonical_path="property.direction_faces",
            confidence=0.85,
            type="enum"
        ),
        "Lot Size Acres": MLSFieldMapping(
            canonical_path="property.lot_size_acres",
            confidence=0.9,
            type="number"
        ),
        "Property Condition": MLSFieldMapping(
            canonical_path="property.property_condition",
            confidence=0.9,
            type="enum"
        ),
        "View": MLSFieldMapping(
            canonical_path="property.view",
            confidence=0.85,
            type="multi_enum",
            transform_fn="string_to_multi_enum"
        ),
        "Flooring": MLSFieldMapping(
            canonical_path="features.flooring",
            confidence=0.9,
            type="multi_enum"
        ),
        "Construction Material": MLSFieldMapping(
            canonical_path="property.construction_material",
            confidence=0.9,
            type="multi_enum"
        ),
        "Waterfront Features": MLSFieldMapping(
            canonical_path="property.waterfront_features",
            confidence=0.85,
            type="multi_enum",
            transform_fn="string_to_multi_enum"
        ),
        "Distance to Water Access": MLSFieldMapping(
            canonical_path="property.distance_to_water",
            confidence=0.9,
            type="number"
        ),
        "Parking Features": MLSFieldMapping(
            canonical_path="features.parking_features",
            confidence=0.8,
            type="multi_enum"
        ),
        "Restrictions": MLSFieldMapping(
            canonical_path="property.restrictions",
            confidence=0.85,
            type="multi_enum",
            transform_fn="string_to_multi_enum"
        ),
        "Foundation Details": MLSFieldMapping(
            canonical_path="property.foundation_details",
            confidence=0.9,
            type="multi_enum"
        ),
        "Roof": MLSFieldMapping(
            canonical_path="property.roof",
            confidence=0.9,
            type="multi_enum"
        ),
        "Lot Features": MLSFieldMapping(
            canonical_path="property.lot_features",
            confidence=0.9,
            type="multi_enum"
        ),
    },
    
    "additional": {
        "Interior Features": MLSFieldMapping(
            canonical_path="features.interior_features",
            confidence=0.9,
            type="multi_enum"
        ),
        "Exterior Features": MLSFieldMapping(
            canonical_path="features.exterior_features",
            confidence=0.9,
            type="multi_enum"
        ),
        "Patio and Porch Features": MLSFieldMapping(
            canonical_path="features.patio_porch_features",
            confidence=0.9,
            type="multi_enum"
        ),
        "Fireplaces": MLSFieldMapping(
            canonical_path="features.fireplaces",
            confidence=0.9,
            type="number",
            transform_fn="count_fireplaces"
        ),
        "Accessibility Features": MLSFieldMapping(
            canonical_path="features.accessibility_features",
            confidence=0.9,
            type="multi_enum"
        ),
        "Horse Amenities": MLSFieldMapping(
            canonical_path="features.horse_amenities",
            confidence=0.85,
            type="multi_enum"
        ),
        "Other Structures": MLSFieldMapping(
            canonical_path="features.other_structures",
            confidence=0.9,
            type="multi_enum"
        ),
        "Appliances": MLSFieldMapping(
            canonical_path="features.appliances",
            confidence=0.9,
            type="multi_enum"
        ),
        "Pool Features": MLSFieldMapping(
            canonical_path="features.pool_features",
            confidence=0.9,
            type="multi_enum"
        ),
        "Guest Accommodations": MLSFieldMapping(
            canonical_path="features.guest_accommodations",
            confidence=0.85,
            type="multi_enum",
            transform_fn="string_to_multi_enum"
        ),
        "Window Features": MLSFieldMapping(
            canonical_path="features.window_features",
            confidence=0.9,
            type="multi_enum"
        ),
        "Security Features": MLSFieldMapping(
            canonical_path="features.security_features",
            confidence=0.85,
            type="multi_enum",
            default_value=["None"]
        ),
        "Laundry Location": MLSFieldMapping(
            canonical_path="features.laundry_location",
            confidence=0.9,
            type="enum"
        ),
        "Fencing": MLSFieldMapping(
            canonical_path="features.fencing",
            confidence=0.85,
            type="multi_enum",
            transform_fn="string_to_multi_enum"
        ),
        "Community Features": MLSFieldMapping(
            canonical_path="features.community_features",
            confidence=0.9,
            type="multi_enum"
        ),
    },
    
    "documents_utilities": {
        "Disclosures": MLSFieldMapping(
            canonical_path="utilities.disclosures",
            confidence=0.9,
            type="enum"
        ),
        "Utilities": MLSFieldMapping(
            canonical_path="utilities.utilities",
            confidence=0.9,
            type="multi_enum"
        ),
        "Documents Available": MLSFieldMapping(
            canonical_path="utilities.documents_available",
            confidence=0.9,
            type="multi_enum"
        ),
        "Heating": MLSFieldMapping(
            canonical_path="utilities.heating",
            confidence=0.9,
            type="multi_enum"
        ),
        "Cooling": MLSFieldMapping(
            canonical_path="utilities.cooling",
            confidence=0.9,
            type="multi_enum"
        ),
        "Water Source": MLSFieldMapping(
            canonical_path="utilities.water_source",
            confidence=0.9,
            type="multi_enum"
        ),
        "Sewer": MLSFieldMapping(
            canonical_path="utilities.sewer",
            confidence=0.9,
            type="multi_enum"
        ),
    },
    
    "green_energy": {
        "Green Energy": MLSFieldMapping(
            canonical_path="green_energy.green_energy",
            confidence=0.85,
            type="multi_enum",
            default_value=["None"]
        ),
        "Green Sustainability": MLSFieldMapping(
            canonical_path="green_energy.green_sustainability",
            confidence=0.85,
            type="multi_enum",
            default_value=["None"]
        ),
    },
    
    "financial": {
        "Association": MLSFieldMapping(
            canonical_path="financial.association",
            confidence=0.9,
            type="boolean"
        ),
        "Association Name": MLSFieldMapping(
            canonical_path="financial.association_name",
            confidence=0.9,
            type="string"
        ),
        "Association Amount": MLSFieldMapping(
            canonical_path="financial.association_amount",
            confidence=0.9,
            type="number"
        ),
        "Association Fee": MLSFieldMapping(
            canonical_path="financial.association_fee",
            confidence=0.9,
            type="number"
        ),
        "Acceptable Financing": MLSFieldMapping(
            canonical_path="financial.acceptable_financing",
            confidence=0.9,
            type="multi_enum"
        ),
        "Estimated Tax": MLSFieldMapping(
            canonical_path="financial.estimated_tax",
            confidence=0.9,
            type="number"
        ),
        "Tax Year": MLSFieldMapping(
            canonical_path="financial.tax_year",
            confidence=0.9,
            type="number"
        ),
        "Tax Annual Amount": MLSFieldMapping(
            canonical_path="financial.tax_annual_amount",
            confidence=0.9,
            type="number"
        ),
        "Tax Assessed Value": MLSFieldMapping(
            canonical_path="financial.tax_assessed_value",
            confidence=0.9,
            type="number"
        ),
        "Tax Rate": MLSFieldMapping(
            canonical_path="financial.tax_rate",
            confidence=0.9,
            type="number"
        ),
        "Buyer Incentive": MLSFieldMapping(
            canonical_path="financial.buyer_incentive",
            confidence=0.85,
            type="enum",
            default_value="None"
        ),
        "Tax Exemptions": MLSFieldMapping(
            canonical_path="financial.tax_exemptions",
            confidence=0.9,
            type="multi_enum"
        ),
        "Possession": MLSFieldMapping(
            canonical_path="financial.possession",
            confidence=0.9,
            type="multi_enum",
            transform_fn="string_to_multi_enum"
        ),
        "Seller Contributions": MLSFieldMapping(
            canonical_path="financial.seller_contributions",
            confidence=0.9,
            type="boolean"
        ),
        "Intermediary": MLSFieldMapping(
            canonical_path="financial.intermediary",
            confidence=0.9,
            type="boolean"
        ),
    },
    
    "showing": {
        "Occupant Type": MLSFieldMapping(
            canonical_path="showing.occupant_type",
            confidence=0.9,
            type="enum"
        ),
        "Showing Requirements": MLSFieldMapping(
            canonical_path="showing.showing_requirements",
            confidence=0.9,
            type="multi_enum"
        ),
        "Owner Name": MLSFieldMapping(
            canonical_path="showing.owner_name",
            confidence=0.9,
            type="string"
        ),
        "Lockbox Type": MLSFieldMapping(
            canonical_path="showing.lockbox_type",
            confidence=0.9,
            type="enum"
        ),
        "Lockbox Location": MLSFieldMapping(
            canonical_path="showing.lockbox_location",
            confidence=0.9,
            type="string"
        ),
        "Showing Instructions": MLSFieldMapping(
            canonical_path="showing.showing_instructions",
            confidence=0.9,
            type="string"
        ),
    },
    
    "agent_office": {
        "Listing Agent": MLSFieldMapping(
            canonical_path="agents.listing_agent",
            confidence=0.95,
            type="string"
        ),
        "Co List Agent": MLSFieldMapping(
            canonical_path="agents.co_listing_agent",
            confidence=0.9,
            type="string"
        ),
    },
    
    "remarks": {
        "Directions": MLSFieldMapping(
            canonical_path="remarks.directions",
            confidence=0.9,
            type="string"
        ),
        "Private Remarks": MLSFieldMapping(
            canonical_path="remarks.private_remarks",
            confidence=0.9,
            type="string"
        ),
        "Public Remarks": MLSFieldMapping(
            canonical_path="remarks.public_remarks",
            confidence=0.9,
            type="string"
        ),
        "Syndication Remarks": MLSFieldMapping(
            canonical_path="remarks.syndication_remarks",
            confidence=0.9,
            type="string"
        ),
        "Branded Virtual Tour URL": MLSFieldMapping(
            canonical_path="media.branded_virtual_tour_url",
            confidence=0.9,
            type="string"
        ),
        "Unbranded Virtual Tour URL": MLSFieldMapping(
            canonical_path="media.unbranded_virtual_tour_url",
            confidence=0.9,
            type="string"
        ),
        "Branded Video Tour URL": MLSFieldMapping(
            canonical_path="media.branded_video_tour_url",
            confidence=0.9,
            type="string"
        ),
        "Unbranded Video Tour URL": MLSFieldMapping(
            canonical_path="media.unbranded_video_tour_url",
            confidence=0.9,
            type="string"
        ),
    },
    
    "internet": {
        "Internet Entire Listing Display": MLSFieldMapping(
            canonical_path=None,
            confidence=1.0,
            type="boolean",
            default_value=True
        ),
        "Internet Automated Valuation Display": MLSFieldMapping(
            canonical_path=None,
            confidence=1.0,
            type="boolean",
            default_value=False
        ),
        "Internet Consumer Comment": MLSFieldMapping(
            canonical_path=None,
            confidence=1.0,
            type="boolean",
            default_value=False
        ),
        "Internet Address Display": MLSFieldMapping(
            canonical_path=None,
            confidence=1.0,
            type="boolean",
            default_value=True
        ),
    },
}


def get_field_mapping(section: str, field_name: str) -> Optional[MLSFieldMapping]:
    """Get mapping for a specific MLS field."""
    return UNLOCK_MLS_FIELD_MAPPINGS.get(section, {}).get(field_name)


def get_all_mappings() -> Dict[str, Dict[str, MLSFieldMapping]]:
    """Get all field mappings."""
    return UNLOCK_MLS_FIELD_MAPPINGS

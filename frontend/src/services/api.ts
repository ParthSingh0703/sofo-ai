import { apiClient } from '../lib/api-client';

// Re-export apiClient for direct use
export { apiClient };

export interface CreateListingResponse {
  listing_id: string;
  status: 'draft';
}

export interface CanonicalListing {
  [key: string]: unknown; // Full canonical structure
}

export interface ReviewFields {
  street_address?: string;
  county?: string;
  city?: string;
  state?: string;
  bedrooms_total?: number;
  bathrooms_total?: number;
  living_area_sqft?: number;
  levels?: number;
  list_price?: number;
  listing_agreement?: string;
  expiration_date?: string;
  year_built?: number;
  ownership_type?: string;
  listing_service?: string;
  special_conditions?: string;
  property_sub_type?: string;
  zip_code?: string;
  parcel_number?: string;
  subdivision?: string;
  mla_area?: string;
  tax_legal_description?: string;
  construction_material?: string[];
  foundation_details?: string[];
  roof?: string[];
  property_condition?: string;
  lot_size_acres?: number;
  direction_faces?: string;
  garage_spaces?: number;
  parking_total?: number;
  living_room?: string;
  dining_room?: string;
  fireplaces?: string[];
  appliances?: string[];
  water_source?: string[];
  sewer?: string[];
  heating?: string[];
  cooling?: string[];
  flooring?: string[];
  association?: boolean;
  association_name?: string;
  association_fee?: number;
  association_amount?: number;
  acceptable_financing?: string[];
  estimated_tax?: number;
  tax_year?: number;
  tax_annual_amount?: number;
  tax_assessed_value?: number;
  tax_rate?: number;
  occupant_type?: string;
  owner_name?: string;
  lockbox_type?: string;
  showing_instructions?: string;
  private_remarks?: string;
  public_remarks?: string;
  poi?: Array<{ name: string; category: string }>;
  directions?: string;
  latitude?: number;
  longitude?: number;
  ai_property_description?: string;
  media_images?: Array<{
    image_id: string;
    ai_suggested_description?: string;
    description?: string;
    ai_suggested_room_type?: string;
    room_type?: string;
    label?: string;
    ai_suggested_label?: string;
  }>;
}

export const listingsApi = {
  create: async (userId: string): Promise<CreateListingResponse> => {
    return apiClient.post(`/listings?user_id=${userId}`);
  },
  
  getCanonical: async (listingId: string): Promise<CanonicalListing> => {
    return apiClient.get(`/listings/${listingId}/canonical`);
  },
  
  updateCanonical: async (listingId: string, canonical: Partial<CanonicalListing>): Promise<CanonicalListing> => {
    return apiClient.put(`/listings/${listingId}/canonical`, canonical);
  },
  
  validateCanonical: async (listingId: string, userId: string): Promise<{ status: string; validated_at: string }> => {
    return apiClient.post(`/listings/${listingId}/validate?user_id=${userId}`);
  },
};

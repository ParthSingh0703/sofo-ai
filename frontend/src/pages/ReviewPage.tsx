import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { listingsApi } from '../services/api';
import { useAppDispatch } from '../store/hooks';
import { addToast } from '../store/slices/uiSlice';
import PropertyMap from '../components/PropertyMap/PropertyMap';
import '../styles/reviewPage.css';

interface FieldConfig {
  key: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'boolean' | 'array' | 'poi' | 'coordinates';
  path: string[];
}


const FIELD_CONFIGS: FieldConfig[] = [
  { key: 'street_address', label: 'Street Address', type: 'text', path: ['location', 'street_address'] },
  { key: 'county', label: 'County', type: 'text', path: ['location', 'county'] },
  { key: 'city', label: 'City', type: 'text', path: ['location', 'city'] },
  { key: 'state', label: 'State', type: 'text', path: ['location', 'state'] },
  { key: 'bedrooms_total', label: 'Bedrooms Total', type: 'number', path: ['property', 'main_level_bedrooms', 'other_level_bedrooms'] },
  { key: 'bathrooms_total', label: 'Bathrooms Total', type: 'number', path: ['property', 'bathrooms_full', 'bathrooms_half'] },
  { key: 'living_area_sqft', label: 'Living Area SQFT', type: 'number', path: ['property', 'living_area_sqft'] },
  { key: 'levels', label: 'Levels', type: 'number', path: ['property', 'levels'] },
  { key: 'list_price', label: 'Listing Price', type: 'number', path: ['listing_meta', 'list_price'] },
  { key: 'listing_agreement', label: 'Listing Agreement', type: 'text', path: ['listing_meta', 'listing_agreement'] },
  { key: 'expiration_date', label: 'Expiration Date', type: 'date', path: ['listing_meta', 'expiration_date'] },
  { key: 'year_built', label: 'Year Built', type: 'number', path: ['property', 'year_built'] },
  { key: 'ownership_type', label: 'Ownership Type', type: 'text', path: ['property', 'ownership_type'] },
  { key: 'listing_service', label: 'Listing Service', type: 'text', path: ['listing_meta', 'listing_service'] },
  { key: 'listing_agent', label: 'Listing Agent', type: 'text', path: ['agents', 'listing_agent'] },
  { key: 'special_conditions', label: 'Special Listing', type: 'text', path: ['listing_meta', 'special_conditions'] },
  { key: 'property_sub_type', label: 'Property Sub Type', type: 'text', path: ['property', 'property_sub_type'] },
  { key: 'zip_code', label: 'Zip Code', type: 'text', path: ['location', 'zip_code'] },
  { key: 'parcel_number', label: 'Parcel Number', type: 'text', path: ['location', 'parcel_number'] },
  { key: 'subdivision', label: 'Subdivision', type: 'text', path: ['location', 'subdivision'] },
  { key: 'mla_area', label: 'MLA Area', type: 'text', path: ['location', 'mla_area'] },
  { key: 'tax_legal_description', label: 'Tax Legal Description', type: 'text', path: ['location', 'tax_legal_description'] },
  { key: 'construction_material', label: 'Construction Material', type: 'array', path: ['property', 'construction_material'] },
  { key: 'foundation_details', label: 'Foundation Material', type: 'array', path: ['property', 'foundation_details'] },
  { key: 'roof', label: 'Roof', type: 'array', path: ['property', 'roof'] },
  { key: 'property_condition', label: 'Property Condition', type: 'text', path: ['property', 'property_condition'] },
  { key: 'lot_size_acres', label: 'Lot Size Acres', type: 'number', path: ['property', 'lot_size_acres'] },
  { key: 'direction_faces', label: 'Direction Faces', type: 'text', path: ['property', 'direction_faces'] },
  { key: 'garage_spaces', label: 'Garage Spaces', type: 'number', path: ['property', 'garage_spaces'] },
  { key: 'parking_total', label: 'Parking Total', type: 'number', path: ['property', 'parking_total'] },
  { key: 'living_room', label: 'Living Room', type: 'text', path: ['property', 'living_room'] },
  { key: 'dining_room', label: 'Dining Room', type: 'text', path: ['property', 'dining_room'] },
  { key: 'fireplaces', label: 'Fireplaces', type: 'array', path: ['features', 'fireplaces'] },
  { key: 'appliances', label: 'Appliances', type: 'array', path: ['features', 'appliances'] },
  { key: 'water_source', label: 'Water Source', type: 'array', path: ['utilities', 'water_source'] },
  { key: 'sewer', label: 'Sewer', type: 'array', path: ['utilities', 'sewer'] },
  { key: 'heating', label: 'Heating', type: 'array', path: ['utilities', 'heating'] },
  { key: 'cooling', label: 'Cooling', type: 'array', path: ['utilities', 'cooling'] },
  { key: 'flooring', label: 'Flooring', type: 'array', path: ['features', 'flooring'] },
  { key: 'association', label: 'Association', type: 'boolean', path: ['financial', 'association'] },
  { key: 'association_name', label: 'Association Name', type: 'text', path: ['financial', 'association_name'] },
  { key: 'association_fee', label: 'Association Fee', type: 'number', path: ['financial', 'association_fee'] },
  { key: 'association_amount', label: 'Association Amount', type: 'number', path: ['financial', 'association_amount'] },
  { key: 'acceptable_financing', label: 'Acceptable Financing', type: 'array', path: ['financial', 'acceptable_financing'] },
  { key: 'estimated_tax', label: 'Estimated Tax', type: 'number', path: ['financial', 'estimated_tax'] },
  { key: 'tax_year', label: 'Tax Year', type: 'number', path: ['financial', 'tax_year'] },
  { key: 'tax_annual_amount', label: 'Tax Annual Amount', type: 'number', path: ['financial', 'tax_annual_amount'] },
  { key: 'tax_assessed_value', label: 'Tax Assessed Value', type: 'number', path: ['financial', 'tax_assessed_value'] },
  { key: 'tax_rate', label: 'Tax Rate', type: 'number', path: ['financial', 'tax_rate'] },
  { key: 'occupant_type', label: 'Occupant Type', type: 'text', path: ['showing', 'occupant_type'] },
  { key: 'owner_name', label: 'Owner Name', type: 'text', path: ['showing', 'owner_name'] },
  { key: 'lockbox_type', label: 'Lockbox Type', type: 'text', path: ['showing', 'lockbox_type'] },
  { key: 'showing_instructions', label: 'Showing Instructions', type: 'text', path: ['showing', 'showing_instructions'] },
  { key: 'private_remarks', label: 'Private Remarks', type: 'text', path: ['remarks', 'private_remarks'] },
  { key: 'public_remarks', label: 'Public Remarks', type: 'text', path: ['remarks', 'public_remarks'] },
  { key: 'poi', label: 'Points of Interest', type: 'poi', path: ['location', 'poi'] },
  { key: 'directions', label: 'Directions', type: 'text', path: ['remarks', 'directions'] },
  { key: 'ai_property_description', label: 'AI Property Description', type: 'text', path: ['remarks', 'ai_property_description'] },
];

export default function ReviewPage() {
  const { listingId } = useParams<{ listingId: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  
  const [canonical, setCanonical] = useState<Record<string, unknown> | null>(null);
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!listingId) return;
    
    const loadCanonical = async () => {
      try {
        setLoading(true);
        
        // Poll for canonical data until we get meaningful data
        const maxWaitTime = 600000; // 10 minutes max
        const startTime = Date.now();
        const pollInterval = 2000; // Check every 2 seconds
        let data = null;
        
        while (Date.now() - startTime < maxWaitTime) {
          try {
            data = await listingsApi.getCanonical(listingId);
            console.log('Loaded canonical data:', data);
            
            // Type guard to ensure data is an object
            if (!data || typeof data !== 'object') {
              await new Promise(resolve => setTimeout(resolve, pollInterval));
              continue;
            }
            
            const dataObj = data as Record<string, unknown>;
            const property = dataObj.property as Record<string, unknown> | undefined;
            const location = dataObj.location as Record<string, unknown> | undefined;
            const listingMeta = dataObj.listing_meta as Record<string, unknown> | undefined;
            const remarks = dataObj.remarks as Record<string, unknown> | undefined;
            const poi = location?.poi as unknown[] | undefined;
            
            // Check if we have meaningful data (extraction and enrichment completed)
            const hasExtractedData = !!(
              property?.living_area_sqft || 
              location?.street_address || 
              listingMeta?.list_price ||
              property?.year_built
            );
            
            const hasEnrichmentData = !!(
              remarks?.public_remarks ||
              remarks?.ai_property_description ||
              (poi && Array.isArray(poi) && poi.length > 0) ||
              remarks?.directions
            );
            
            // If we have both extracted and enriched data, we're done
            if (hasExtractedData && hasEnrichmentData) {
              console.log('Canonical data is complete');
              break;
            }
            
            // If we only have extracted data but not enrichment, wait a bit more
            if (hasExtractedData && !hasEnrichmentData) {
              console.log('Extraction complete, waiting for enrichment...');
            } else if (!hasExtractedData) {
              console.log('Waiting for extraction to complete...');
            }
          } catch (error) {
            console.warn('Failed to load canonical, retrying...', error);
          }
          
          // Wait before next poll
          await new Promise(resolve => setTimeout(resolve, pollInterval));
        }
        
        if (!data) {
          throw new Error('Failed to load canonical data after polling');
        }
        
        setCanonical(data);
        
        // Type guard to ensure data is an object
        if (!data || typeof data !== 'object') {
          throw new Error('Invalid canonical data format');
        }
        
        const dataObj = data as Record<string, unknown>;
        
        // Extract values for form
        const extracted: Record<string, unknown> = {};
        FIELD_CONFIGS.forEach(field => {
          let value: unknown = dataObj;
          for (const pathKey of field.path) {
            if (value && typeof value === 'object' && pathKey in value) {
              value = (value as Record<string, unknown>)[pathKey];
            } else {
              value = null;
              break;
            }
          }
          
          // Handle special cases
          if (field.key === 'bedrooms_total') {
            const property = dataObj.property as Record<string, unknown> | undefined;
            const main = (property?.main_level_bedrooms as number) || 0;
            const other = (property?.other_level_bedrooms as number) || 0;
            value = main + other;
          } else if (field.key === 'bathrooms_total') {
            const property = dataObj.property as Record<string, unknown> | undefined;
            const full = (property?.bathrooms_full as number) || 0;
            const half = (property?.bathrooms_half as number) || 0;
            // Format as decimal (e.g., 2.5 for 2 full, 1 half)
            value = half > 0 ? `${full}.${half}` : full;
          }
          
          extracted[field.key] = value;
        });
        
        // Extract latitude and longitude separately (not in FIELD_CONFIGS)
        const location = dataObj.location as Record<string, unknown> | undefined;
        if (location) {
          extracted.latitude = location.latitude as number | null || null;
          extracted.longitude = location.longitude as number | null || null;
        }
        
        setFormData(extracted);
      } catch (error) {
        console.error('Failed to load canonical:', error);
        dispatch(addToast({
          message: error instanceof Error ? error.message : 'Failed to load listing data',
          type: 'error',
        }));
      } finally {
        setLoading(false);
      }
    };
    
    loadCanonical();
  }, [listingId, dispatch]);


  const updateField = (key: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const updateArrayField = (key: string, index: number, value: string) => {
    setFormData(prev => {
      const currentValue = prev[key];
      const arr = Array.isArray(currentValue) ? [...(currentValue as string[])] : [];
      arr[index] = value;
      return { ...prev, [key]: arr };
    });
  };

  const addArrayItem = (key: string) => {
    setFormData(prev => {
      const currentValue = prev[key];
      const arr = Array.isArray(currentValue) ? [...(currentValue as string[])] : [];
      return { ...prev, [key]: [...arr, ''] };
    });
  };

  const removeArrayItem = (key: string, index: number) => {
    setFormData(prev => {
      const currentValue = prev[key];
      const arr = Array.isArray(currentValue) ? [...(currentValue as string[])] : [];
      arr.splice(index, 1);
      return { ...prev, [key]: arr };
    });
  };

  const handleNextStep = async () => {
    if (!listingId || !canonical) {
      console.log('Cannot proceed: missing listingId or canonical', { listingId, hasCanonical: !!canonical });
      return;
    }
    
    try {
      setSaving(true);
      console.log('Saving canonical updates for listing:', listingId);
      
      // Build updated canonical from form data
      const updated = JSON.parse(JSON.stringify(canonical));
      
      // Ensure updated has proper structure
      if (!updated.property) updated.property = {};
      if (!updated.location) updated.location = {};
      if (!updated.listing_meta) updated.listing_meta = {};
      if (!updated.remarks) updated.remarks = {};
      if (!updated.financial) updated.financial = {};
      if (!updated.showing) updated.showing = {};
      if (!updated.features) updated.features = {};
      if (!updated.utilities) updated.utilities = {};
      if (!updated.agents) updated.agents = {};
      
      // Handle latitude and longitude separately (not in FIELD_CONFIGS anymore)
      if (formData.latitude !== undefined && formData.latitude !== null) {
        updated.location.latitude = formData.latitude;
      }
      if (formData.longitude !== undefined && formData.longitude !== null) {
        updated.location.longitude = formData.longitude;
      }
      
      FIELD_CONFIGS.forEach(field => {
        const value = formData[field.key];
        if (value === undefined || value === null) return;
        
        // Handle special cases
        if (field.key === 'bedrooms_total') {
          // Split total bedrooms - assume all on main level for now
          const total = typeof value === 'number' ? value : parseInt(String(value)) || 0;
          updated.property.main_level_bedrooms = total;
          updated.property.other_level_bedrooms = 0;
          return;
        } else if (field.key === 'bathrooms_total') {
          // Parse "X.Y" or "X" format
          const strValue = String(value);
          if (strValue.includes('.')) {
            const parts = strValue.split('.');
            updated.property.bathrooms_full = parseInt(parts[0]) || 0;
            updated.property.bathrooms_half = parseInt(parts[1]) || 0;
          } else {
            updated.property.bathrooms_full = parseInt(strValue) || 0;
            updated.property.bathrooms_half = 0;
          }
          return;
        }
        
        // Navigate to the path and set value
        let target = updated as Record<string, unknown>;
        for (let i = 0; i < field.path.length - 1; i++) {
          const key = field.path[i];
          if (!target[key] || typeof target[key] !== 'object') {
            target[key] = {};
          }
          target = target[key] as Record<string, unknown>;
        }
        target[field.path[field.path.length - 1]] = value;
      });
      
      console.log('Updating canonical via API...');
      await listingsApi.updateCanonical(listingId, updated);
      console.log('Canonical updated successfully');
      
      dispatch(addToast({
        message: 'Listing updated successfully',
        type: 'success',
      }));
      
      console.log('Navigating to media page:', `/media/${listingId}`);
      navigate(`/media/${listingId}`, { replace: true });
    } catch (error) {
      console.error('Failed to update canonical:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to update listing';
      dispatch(addToast({
        message: errorMessage,
        type: 'error',
      }));
      // Still navigate even if update fails (user can retry)
      console.log('Navigating to media page despite error');
      navigate(`/media/${listingId}`, { replace: true });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center" style={{ backgroundColor: '#0F1115', color: 'white' }}>
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p>Loading listing data...</p>
        </div>
      </div>
    );
  }

  // Extract latitude, longitude, and property description for the map section
  const latitude = formData.latitude as number | null;
  const longitude = formData.longitude as number | null;
  const propertyDescription = formData.ai_property_description as string | null;
  const streetAddress = formData.street_address as string | null;

  return (
    <div className="h-screen w-full overflow-hidden" style={{ backgroundColor: '#0F1115', color: 'white', padding: '10px' }}>
      <div className="h-full flex flex-col max-w-full mx-auto">
        <h1 className="text-lg font-semibold mb-2 px-2">Review & Edit Listing Information</h1>
        
        <div className="flex-1 overflow-y-auto">
          {/* Map Section */}
          {(latitude || longitude || true) && (
            <div className="px-2 mb-3">
              <PropertyMap 
                latitude={latitude || null} 
                longitude={longitude || null}
                address={streetAddress || undefined}
                onLatitudeChange={(value) => updateField('latitude', value)}
                onLongitudeChange={(value) => updateField('longitude', value)}
              />
              
              {/* Property Description */}
              {propertyDescription && (
                <div className="mt-3">
                  <label className="block text-[10px] font-medium mb-1" style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                    Property Description
                  </label>
                  <div className="review-textarea" style={{ 
                    minHeight: '80px', 
                    padding: '0.5rem',
                    backgroundColor: 'rgba(33, 104, 218, 0.49)',
                    borderRadius: '4px',
                    whiteSpace: 'pre-wrap',
                    overflowY: 'auto',
                    maxHeight: '150px'
                  }}>
                    {propertyDescription}
                  </div>
                </div>
              )}
            </div>
          )}
          
          <div className="grid grid-cols-3 gap-1.5 px-2">
            {FIELD_CONFIGS.map(field => (
              <div key={field.key} className="border-b border-zinc-700/30 pb-1">
                <label className="block text-[10px] font-medium mb-0.5" style={{ color: 'rgba(255, 255, 255, 0.9)'}}>
                  {field.label}
                </label>
              
              {field.type === 'text' && (
                (field.key === 'private_remarks' || field.key === 'public_remarks' || field.key === 'ai_property_description' || field.key === 'directions' || field.key === 'showing_instructions' || field.key === 'tax_legal_description') ? (
                  <textarea
                    value={String(formData[field.key] || '')}
                    onChange={(e) => updateField(field.key, e.target.value)}
                    rows={2}
                    className="review-textarea"
                  />
                ) : (
                  <input
                    type="text"
                    value={String(formData[field.key] || '')}
                    onChange={(e) => updateField(field.key, e.target.value)}
                    className="review-input"
                  />
                )
              )}
              
              {field.type === 'number' && (
                <input
                  type="number"
                  value={((): number | '' => {
                    const val = formData[field.key];
                    if (typeof val === 'number') return val;
                    if (val) {
                      const num = Number(val);
                      return isNaN(num) ? '' : num;
                    }
                    return '';
                  })()}
                  onChange={(e) => updateField(field.key, e.target.value ? parseFloat(e.target.value) : null)}
                  className="review-input"
                />
              )}
              
              {field.type === 'date' && (
                <input
                  type="text"
                  value={String(formData[field.key] || '')}
                  onChange={(e) => updateField(field.key, e.target.value)}
                  placeholder="MM/DD/YYYY"
                  className="review-input"
                />
              )}
              
              {field.type === 'boolean' && (
                <select
                  value={formData[field.key] === true ? 'yes' : formData[field.key] === false ? 'no' : ''}
                  onChange={(e) => updateField(field.key, e.target.value === 'yes' ? true : e.target.value === 'no' ? false : null)}
                  className="review-select"
                >
                  <option value="">Not Set</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              )}
              
              {field.type === 'array' && (
                <div className="space-y-1">
                  {((formData[field.key] as string[]) || []).map((item: string, index: number) => (
                    <div key={index} className="flex gap-1">
                      <input
                        type="text"
                        value={item}
                        onChange={(e) => updateArrayField(field.key, index, e.target.value)}
                        className="flex-1 review-input"
                      />
                      <button
                        onClick={() => removeArrayItem(field.key, index)}
                        className="px-1.5 py-0.5 text-[8px] rounded bg-red-600 hover:bg-red-700 text-white"
                      >
                        X
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => addArrayItem(field.key)}
                    className="px-1.5 py-0.5 text-[8px] rounded bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    + Add
                  </button>
                </div>
              )}
              
              {field.type === 'poi' && (
                <div className="space-y-1">
                  {((formData[field.key] as Array<Record<string, unknown>>) || []).map((poi: Record<string, unknown>, index: number) => (
                    <div key={index} className="p-1 rounded bg-zinc-800/50 border border-zinc-700">
                      <p className="text-[9px]"><strong>Name:</strong> {String(poi.name || '')}</p>
                      <p className="text-[9px]"><strong>Category:</strong> {String(poi.category || '')}</p>
                    </div>
                  ))}
                </div>
              )}
              
              {field.type === 'coordinates' && (
                <input
                  type="number"
                  step="any"
                  value={((): number | '' => {
                    const val = formData[field.key];
                    if (typeof val === 'number') return val;
                    if (val) {
                      const num = Number(val);
                      return isNaN(num) ? '' : num;
                    }
                    return '';
                  })()}
                  onChange={(e) => updateField(field.key, e.target.value ? parseFloat(e.target.value) : null)}
                  className="review-input"
                />
              )}
            </div>
          ))}
          </div>
        </div>
        
        <div className="mt-2 px-2 flex justify-end border-t border-zinc-700/30 pt-2">
          <button
            onClick={handleNextStep}
            disabled={saving}
            className="px-4 py-1.5 text-sm rounded bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Next Step'}
          </button>
        </div>
      </div>
    </div>
  );
}

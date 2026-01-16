import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../store/hooks';
import { setCurrentListing } from '../store/slices/listingsSlice';
import { apiClient } from '../lib/api-client';

// Helper function to check if extraction is complete
const isExtractionComplete = (canonical: unknown): boolean => {
  if (!canonical || typeof canonical !== 'object') return false;
  
  const c = canonical as Record<string, unknown>;
  
  // Check for key extracted fields that indicate extraction has run
  const listingMeta = c.listing_meta as Record<string, unknown> | undefined;
  const property = c.property as Record<string, unknown> | undefined;
  const location = c.location as Record<string, unknown> | undefined;
  const financial = c.financial as Record<string, unknown> | undefined;
  
  const hasExtractedData = 
    listingMeta?.list_price ||
    property?.living_area_sqft ||
    property?.year_built ||
    location?.street_address ||
    property?.property_sub_type ||
    financial?.tax_year;
  
  return !!hasExtractedData;
};

// Helper function to check if enrichment is complete
const isEnrichmentComplete = (canonical: unknown): boolean => {
  if (!canonical || typeof canonical !== 'object') return false;
  
  const c = canonical as Record<string, unknown>;
  
  // Check for enrichment-specific fields
  const remarks = c.remarks as Record<string, unknown> | undefined;
  const location = c.location as Record<string, unknown> | undefined;
  const media = c.media as Record<string, unknown> | undefined;
  
  const poi = location?.poi as unknown[] | undefined;
  const mediaImages = media?.media_images as unknown[] | undefined;
  
  const hasEnrichmentData = 
    remarks?.public_remarks ||
    remarks?.ai_property_description ||
    (poi && poi.length > 0) ||
    remarks?.directions ||
    (mediaImages && mediaImages.length > 0);
  
  return !!hasEnrichmentData;
};

// Poll canonical until extraction is complete
const waitForExtraction = async (listingId: string, maxWaitTime: number = 600000): Promise<boolean> => {
  const startTime = Date.now();
  const pollInterval = 3000; // Check every 3 seconds
  
  while (Date.now() - startTime < maxWaitTime) {
    try {
      const canonical = await apiClient.get(`/listings/${listingId}/canonical`);
      if (isExtractionComplete(canonical)) {
        console.log('Extraction completed');
        return true;
      }
      console.log('Waiting for extraction to complete...');
    } catch (error) {
      console.warn('Error checking extraction status:', error);
    }
    
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }
  
  console.warn('Extraction timeout - proceeding anyway');
  return false;
};

// Poll canonical until enrichment is complete
const waitForEnrichment = async (listingId: string, maxWaitTime: number = 600000): Promise<boolean> => {
  const startTime = Date.now();
  const pollInterval = 3000; // Check every 3 seconds
  
  while (Date.now() - startTime < maxWaitTime) {
    try {
      const canonical = await apiClient.get(`/listings/${listingId}/canonical`);
      if (isEnrichmentComplete(canonical)) {
        console.log('Enrichment completed');
        return true;
      }
      console.log('Waiting for enrichment to complete...');
    } catch (error) {
      console.warn('Error checking enrichment status:', error);
    }
    
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }
  
  console.warn('Enrichment timeout - proceeding anyway');
  return false;
};

export default function ProcessingPage() {
  const { listingId } = useParams<{ listingId: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [status, setStatus] = useState('Waiting for extraction...');

  useEffect(() => {
    if (!listingId) {
      navigate('/', { replace: true });
      return;
    }

    dispatch(setCurrentListing(listingId));

    // Process: Wait for extraction, then run enrichment, then wait for enrichment
    const processListing = async () => {
      try {
        // Step 1: Wait for extraction to complete (it may have been started from UploadPage)
        setStatus('Extracting data from documents...');
        const extractionComplete = await waitForExtraction(listingId);
        
        if (!extractionComplete) {
          console.warn('Extraction may not have completed, but proceeding');
        }

        // Step 2: Start enrichment (this will use the extracted data)
        setStatus('Enriching listing data...');
        console.log('Starting enrichment...');
        
        // Start enrichment (don't await - it may take a while)
        const enrichmentPromise = apiClient.post(
          `/enrichment/listings/${listingId}/enrich?analyze_images=true&generate_descriptions=true&enrich_geo=true`
        );
        
        // Start enrichment in background and poll for completion
        enrichmentPromise.catch(error => {
          console.error('Enrichment error:', error);
        });
        
        // Wait for enrichment to complete by polling canonical
        setStatus('Waiting for enrichment to complete...');
        await waitForEnrichment(listingId);
        
        console.log('Processing completed');
        setStatus('Processing complete!');
        
        // Small delay to show completion message
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Step 3: Navigate to review page after everything completes
        navigate(`/review/${listingId}`, { replace: true });
      } catch (error) {
        console.error('Processing failed:', error);
        // Still navigate to review page even if processing fails
        // User can see what data is available
        navigate(`/review/${listingId}`, { replace: true });
      }
    };

    processListing();
  }, [listingId, navigate, dispatch]);

  return (
    <div 
      style={{ 
        minHeight: '100vh', 
        width: '100%', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        backgroundColor: '#0F1115' 
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '24px' }}>
        {/* Loading Animation - Two Concentric Circles */}
        <div style={{ position: 'relative', width: '80px', height: '80px' }}>
          {/* Outer Circle with Border (static background) */}
          <div
            style={{
              position: 'absolute',
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              border: '3px solid rgba(33, 104, 218, 0.49)',
              backgroundColor: '#0F1115',
            }}
          />
          {/* Moving Segment (one-fourth of the circle - 90 degrees) */}
          <div
            style={{
              position: 'absolute',
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              border: '3px solid transparent',
              borderTopColor: 'rgba(59, 130, 246, 0.8)',
              borderRightColor: 'rgba(59, 130, 246, 0.8)',
              borderTopWidth: '3px',
              borderRightWidth: '3px',
              borderBottomWidth: '3px',
              borderLeftWidth: '3px',
              animation: 'spin 1.5s linear infinite',
            }}
          />
          {/* Inner Solid Circle */}
          <div
            style={{
              position: 'absolute',
              top: '52%',
              left: '52.5%',
              transform: 'translate(-50%, -50%)',
              width: '25px',
              height: '25px',
              borderRadius: '50%',
              backgroundColor: 'rgba(59, 130, 246, 0.8)',
            }}
          />
        </div>
        
        <p style={{ color: 'white', fontSize: '20px', textAlign: 'center', margin: 0 }}>
          Our AI is reading through your property details.......
        </p>
        <p style={{ color: 'white', fontSize: '20px', textAlign: 'center', margin: 0 }}>
          {status}
        </p>
      </div>
      
      <style>{`
        @keyframes spin {
          0% {
            transform: rotate(0deg);
          }
          100% {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../../store/hooks';
import { setCurrentListing } from '../../store/slices/listingsSlice';
import { apiClient } from '../../lib/api-client';
import styles from './ProcessingPage.module.css';

// Helper function to check if extraction is complete
const isExtractionComplete = (canonical: unknown): boolean => {
    if (!canonical || typeof canonical !== 'object') return false;
    
    const c = canonical as Record<string, unknown>;
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
    const pollInterval = 3000;
    
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
    const pollInterval = 3000;
    
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

const ProcessingPage = () => {
    const { listingId } = useParams<{ listingId: string }>();
    const navigate = useNavigate();
    const dispatch = useAppDispatch();
    const [status, setStatus] = useState('Extracting Data from documents...');

    useEffect(() => {
        if (!listingId) {
            navigate('/', { replace: true });
            return;
        }

        dispatch(setCurrentListing(listingId));

        const processListing = async () => {
            try {
                setStatus('Extracting Data from documents...');
                const extractionComplete = await waitForExtraction(listingId);
                
                if (!extractionComplete) {
                    console.warn('Extraction may not have completed, but proceeding');
                }

                setStatus('Enriching listing data...');
                console.log('Starting enrichment...');
                
                const enrichmentPromise = apiClient.post(
                    `/enrichment/listings/${listingId}/enrich?analyze_images=true&generate_descriptions=true&enrich_geo=true`
                );
                
                enrichmentPromise.catch(error => {
                    console.error('Enrichment error:', error);
                });
                
                setStatus('Waiting for enrichment to complete...');
                await waitForEnrichment(listingId);
                
                console.log('Processing completed');
                setStatus('Processing complete!');
                
                await new Promise(resolve => setTimeout(resolve, 500));
                
                navigate(`/listings/${listingId}/review`, { replace: true });
            } catch (error) {
                console.error('Processing failed:', error);
                navigate(`/listings/${listingId}/review`, { replace: true });
            }
        };

        processListing();
    }, [listingId, navigate, dispatch]);

    return (
        <div className={styles.container}>
            <div className={styles.loaderWrapper}>
                <div className={styles.circleContainer}>
                    <div className={styles.outerRing}></div>
                    <div className={styles.innerCircle}></div>
                </div>
                <p className={styles.text}>{status}</p>
                <p className={styles.subtext}>This may take a few moments</p>
            </div>
        </div>
    );
};

export default ProcessingPage;

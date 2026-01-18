import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ChevronRight } from 'lucide-react';
import { listingsApi } from '../../services/api';
import { useAppDispatch } from '../../store/hooks';
import { addToast } from '../../store/slices/uiSlice';
import TopicSection from './TopicSection';
import EditableField from './EditableField';
import PropertyMap from '../../components/PropertyMap/PropertyMap';
import {
    formatCurrency,
    formatDate,
    formatArray,
    formatBoolean,
    formatPercentage,
    formatDecimal,
    getCanonicalValue,
    setCanonicalValue,
    calculateTotalBedrooms,
    calculateTotalBathrooms,
} from '../../utils/canonicalFormatters';
import styles from './ReviewPage.module.css';

interface ReviewPageProps {
    onNext?: () => void;
}

const ReviewPage = ({ onNext }: ReviewPageProps) => {
    const { listingId } = useParams<{ listingId: string }>();
    const navigate = useNavigate();
    const dispatch = useAppDispatch();
    const [isEditMode, setIsEditMode] = useState(false);
    const [canonical, setCanonical] = useState<Record<string, unknown> | null>(null);
    const [loading, setLoading] = useState(true);
    const isMountedRef = useRef(true);
    const pollingTimeoutRef = useRef<number | null>(null);

    useEffect(() => {
        if (!listingId) return;

        // Reset state when listingId changes
        setCanonical(null);
        setLoading(true);
        isMountedRef.current = true;

        const loadCanonical = async () => {
            try {
                setLoading(true);
                
                // Poll for canonical data with retries
                const maxRetries = 20;
                const pollInterval = 2000; // 2 seconds
                let retries = 0;
                let data: unknown = null;
                
                while (retries < maxRetries && isMountedRef.current) {
                    try {
                        data = await listingsApi.getCanonical(listingId);
                        
                        // Check if component is still mounted
                        if (!isMountedRef.current) return;
                        
                        // Check if we have meaningful data
                        if (data && typeof data === 'object') {
                            const dataObj = data as Record<string, unknown>;
                            const property = dataObj.property as Record<string, unknown> | undefined;
                            const location = dataObj.location as Record<string, unknown> | undefined;
                            const listingMeta = dataObj.listing_meta as Record<string, unknown> | undefined;
                            
                            // Check if we have at least some extracted data
                            const hasData = !!(
                                property?.living_area_sqft ||
                                location?.street_address ||
                                listingMeta?.list_price ||
                                property?.year_built ||
                                location?.city
                            );
                            
                            if (hasData) {
                                if (isMountedRef.current) {
                                    setCanonical(dataObj);
                                    setLoading(false);
                                }
                                return;
                            }
                        }
                        
                        // If no meaningful data yet, wait and retry
                        if (retries < maxRetries - 1 && isMountedRef.current) {
                            await new Promise(resolve => {
                                pollingTimeoutRef.current = setTimeout(resolve, pollInterval);
                            });
                        }
                    } catch (error) {
                        // Check if component is still mounted
                        if (!isMountedRef.current) return;
                        
                        const errorMessage = error instanceof Error ? error.message : String(error);
                        console.warn(`Failed to load canonical (attempt ${retries + 1}/${maxRetries}):`, errorMessage);
                        
                        // If it's a network error and we haven't exhausted retries, continue retrying
                        if (retries < maxRetries - 1 && isMountedRef.current) {
                            // Continue retrying - don't throw yet
                            await new Promise(resolve => {
                                pollingTimeoutRef.current = setTimeout(resolve, pollInterval);
                            });
                        } else {
                            // Last retry failed - throw to show error
                            throw error;
                        }
                    }
                    
                    retries++;
                }
                
                // If we got data but it wasn't meaningful, still set it
                if (isMountedRef.current) {
                    if (data && typeof data === 'object') {
                        setCanonical(data as Record<string, unknown>);
                    } else {
                        throw new Error('No canonical data available after retries');
                    }
                }
            } catch (error) {
                if (isMountedRef.current) {
                    console.error('Failed to load canonical:', error);
                    dispatch(addToast({
                        message: error instanceof Error ? error.message : 'Failed to load listing data. Please check if the backend is running.',
                        type: 'error',
                    }));
                }
            } finally {
                if (isMountedRef.current) {
                    setLoading(false);
                }
            }
        };

        loadCanonical();

        // Cleanup function
        return () => {
            isMountedRef.current = false;
            if (pollingTimeoutRef.current) {
                clearTimeout(pollingTimeoutRef.current);
                pollingTimeoutRef.current = null;
            }
        };
    }, [listingId, dispatch]);

    const getFieldValue = (path: string[]): string => {
        if (!canonical) return '-';
        const value = getCanonicalValue(canonical, path);
        if (value === null || value === undefined) return '-';
        return String(value);
    };

    const getArrayValue = (path: string[]): string => {
        if (!canonical) return '-';
        const value = getCanonicalValue(canonical, path);
        return formatArray(value as string[] | null);
    };

    const getCurrencyValue = (path: string[]): string => {
        if (!canonical) return '-';
        const value = getCanonicalValue(canonical, path);
        return formatCurrency(value as number | null);
    };


    const getBooleanValue = (path: string[]): string => {
        if (!canonical) return '-';
        const value = getCanonicalValue(canonical, path);
        return formatBoolean(value as boolean | null);
    };

    const getPercentageValue = (path: string[]): string => {
        if (!canonical) return '-';
        const value = getCanonicalValue(canonical, path);
        return formatPercentage(value as number | null);
    };

    const handleFieldChange = async (field: string, path: string[], newValue: string) => {
        if (!canonical) return;

        const updated = JSON.parse(JSON.stringify(canonical));
        
        // Parse value based on field type
        let parsedValue: unknown = newValue;
        
        // Handle array fields - split by comma
        if (field.includes('construction') || field.includes('foundation') || field.includes('roof') ||
            field.includes('fireplaces') || field.includes('appliances') || field.includes('water') ||
            field.includes('sewer') || field.includes('heating') || field.includes('cooling') ||
            field.includes('flooring') || field.includes('financing')) {
            parsedValue = newValue ? newValue.split(',').map(s => s.trim()).filter(s => s) : [];
        }
        // Handle number fields
        else if (field.includes('price') || field.includes('fee') || field.includes('amount') ||
                 field.includes('tax') || field.includes('value') || field.includes('spaces') ||
                 field.includes('parking') || field.includes('acres') || field.includes('year') ||
                 field.includes('rate')) {
            parsedValue = newValue ? parseFloat(newValue.replace(/[^0-9.-]/g, '')) || null : null;
        }
        // Handle boolean fields
        else if (field === 'association') {
            parsedValue = newValue.toLowerCase() === 'yes' || newValue.toLowerCase() === 'true';
        }
        // Handle date fields
        else if (field.includes('date') || field.includes('Date')) {
            // Try to parse MM/DD/YYYY format
            const dateMatch = newValue.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
            if (dateMatch) {
                const [, month, day, year] = dateMatch;
                parsedValue = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T00:00:00`;
            } else {
                parsedValue = newValue;
            }
        }
        // Handle decimal fields (latitude, longitude)
        else if (field === 'latitude' || field === 'longitude') {
            parsedValue = newValue ? parseFloat(newValue) || null : null;
        }

        setCanonicalValue(updated, path, parsedValue);
        setCanonical(updated);

        // Auto-save
        try {
            await listingsApi.updateCanonical(listingId!, updated);
        } catch (error) {
            console.error('Failed to save:', error);
            dispatch(addToast({
                message: 'Failed to save changes',
                type: 'error',
            }));
        }
    };

    const toggleEditMode = () => {
        const newEditMode = !isEditMode;
        setIsEditMode(newEditMode);
        
        // Focus the first editable field when entering edit mode
        if (newEditMode) {
            setTimeout(() => {
                // Try to focus the first field in the first topic section
                const firstInput = document.querySelector('.scrollContainer input, .scrollContainer textarea') as HTMLInputElement | HTMLTextAreaElement;
                if (firstInput) {
                    firstInput.focus();
                }
            }, 100);
        }
    };

    const handleNext = () => {
        if (onNext) {
            onNext();
        } else if (listingId) {
            navigate(`/listings/${listingId}/media`);
        }
    };

    const handleBack = () => {
        if (listingId) {
            navigate(`/listings/${listingId}/upload`);
        }
    };

    if (loading) {
        return (
            <div className={styles.container}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '1rem' }}>
                    <p style={{ color: 'var(--text-primary)' }}>Loading listing data...</p>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>This may take a few moments</p>
                </div>
            </div>
        );
    }

    if (!canonical) {
        return (
            <div className={styles.container}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '1rem' }}>
                    <p style={{ color: 'var(--text-primary)' }}>No data available</p>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                        Please ensure the backend is running and try refreshing the page.
                    </p>
                    <button
                        onClick={() => window.location.reload()}
                        style={{
                            padding: '0.5rem 1rem',
                            background: 'var(--accent-blue)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                        }}
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    const location = canonical.location as Record<string, unknown> | undefined;
    const property = canonical.property as Record<string, unknown> | undefined;
    const listingMeta = canonical.listing_meta as Record<string, unknown> | undefined;

    // Header stats
    const listPrice = formatCurrency(listingMeta?.list_price as number | null);
    const agreementType = (listingMeta?.listing_agreement as string) || '-';
    const expirationDate = formatDate(listingMeta?.expiration_date as string | null);
    const yearBuilt = String(property?.year_built || '-');
    const ownership = (property?.ownership_type as string) || '-';

    // Header address and specs
    const streetAddress = (location?.street_address as string) || '-';
    const county = (location?.county as string) || '-';
    const city = (location?.city as string) || '-';
    const state = (location?.state as string) || '-';
    const bedrooms = calculateTotalBedrooms(canonical);
    const bathrooms = calculateTotalBathrooms(canonical);
    const sqft = property?.living_area_sqft ? String(property.living_area_sqft) : '-';
    const floors = property?.levels ? String(property.levels) : '-';

    const renderStatField = (label: string, value: string, key: string, path: string[]) => {
        if (isEditMode) {
            // For currency fields, show raw number instead of formatted string
            let inputValue = value;
            if (key === 'listPrice') {
                const rawValue = getCanonicalValue(canonical, path) as number | null;
                inputValue = rawValue !== null && rawValue !== undefined ? String(rawValue) : '';
            } else if (key === 'yearBuilt') {
                const rawValue = getCanonicalValue(canonical, path);
                inputValue = rawValue !== null && rawValue !== undefined ? String(rawValue) : '';
            }
            
            return (
                <div className={styles.statBoxEditable}>
                    <span className={styles.statLabel}>{label}</span>
                    <input
                        className={styles.statInput}
                        value={inputValue}
                        onChange={(e) => handleFieldChange(key, path, e.target.value)}
                    />
                </div>
            );
        }
        return (
            <div className={styles.statBox}>
                <span className={styles.statValue}>{value}</span>
                <span className={styles.statLabel}>{label}</span>
            </div>
        );
    };

    return (
        <div className={styles.container}>
            {/* Header / Top Bar */}
            <div className={styles.topBar}>
                <button className={styles.backButton} onClick={handleBack}>
                    <ArrowLeft size={18} />
                </button>
                <div className={styles.propertyHeader}>
                    {isEditMode ? (
                        <>
                            <input
                                className={styles.headerInput}
                                value={streetAddress}
                                onChange={(e) => handleFieldChange('streetAddress', ['location', 'street_address'], e.target.value)}
                                placeholder="Street Address"
                                style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.1rem' }}
                            />
                            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.1rem' }}>
                                <input
                                    className={styles.headerInput}
                                    value={county}
                                    onChange={(e) => handleFieldChange('county', ['location', 'county'], e.target.value)}
                                    placeholder="County"
                                    style={{ fontSize: '0.6rem', flex: 1 }}
                                />
                                <input
                                    className={styles.headerInput}
                                    value={city}
                                    onChange={(e) => handleFieldChange('city', ['location', 'city'], e.target.value)}
                                    placeholder="City"
                                    style={{ fontSize: '0.6rem', flex: 1 }}
                                />
                                <input
                                    className={styles.headerInput}
                                    value={state}
                                    onChange={(e) => handleFieldChange('state', ['location', 'state'], e.target.value)}
                                    placeholder="State"
                                    style={{ fontSize: '0.6rem', flex: 1 }}
                                />
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <input
                                    className={styles.headerInput}
                                    value={bedrooms !== null ? String(bedrooms) : ''}
                                    onChange={async (e) => {
                                        const val = e.target.value;
                                        const total = val === '' ? null : (parseInt(val) || 0);
                                        const updated = JSON.parse(JSON.stringify(canonical));
                                        if (total !== null && total > 0) {
                                            setCanonicalValue(updated, ['property', 'main_level_bedrooms'], total);
                                            setCanonicalValue(updated, ['property', 'other_level_bedrooms'], 0);
                                        } else {
                                            setCanonicalValue(updated, ['property', 'main_level_bedrooms'], null);
                                            setCanonicalValue(updated, ['property', 'other_level_bedrooms'], null);
                                        }
                                        setCanonical(updated);
                                        try {
                                            await listingsApi.updateCanonical(listingId!, updated);
                                        } catch (error) {
                                            console.error('Failed to save bedrooms:', error);
                                        }
                                    }}
                                    placeholder="Bedrooms"
                                    style={{ fontSize: '0.55rem', width: '80px' }}
                                />
                                <input
                                    className={styles.headerInput}
                                    value={bathrooms || ''}
                                    onChange={async (e) => {
                                        const val = e.target.value;
                                        if (val === '') {
                                            const updated = JSON.parse(JSON.stringify(canonical));
                                            setCanonicalValue(updated, ['property', 'bathrooms_full'], null);
                                            setCanonicalValue(updated, ['property', 'bathrooms_half'], null);
                                            setCanonical(updated);
                                            try {
                                                await listingsApi.updateCanonical(listingId!, updated);
                                            } catch (error) {
                                                console.error('Failed to save bathrooms:', error);
                                            }
                                            return;
                                        }
                                        const parts = val.split('.');
                                        const full = parseInt(parts[0]) || 0;
                                        const half = parts[1] ? parseInt(parts[1]) : 0;
                                        const updated = JSON.parse(JSON.stringify(canonical));
                                        if (full > 0 || half > 0) {
                                            setCanonicalValue(updated, ['property', 'bathrooms_full'], full);
                                            setCanonicalValue(updated, ['property', 'bathrooms_half'], half);
                                        } else {
                                            setCanonicalValue(updated, ['property', 'bathrooms_full'], null);
                                            setCanonicalValue(updated, ['property', 'bathrooms_half'], null);
                                        }
                                        setCanonical(updated);
                                        try {
                                            await listingsApi.updateCanonical(listingId!, updated);
                                        } catch (error) {
                                            console.error('Failed to save bathrooms:', error);
                                        }
                                    }}
                                    placeholder="Bathrooms"
                                    style={{ fontSize: '0.55rem', width: '80px' }}
                                />
                                <input
                                    className={styles.headerInput}
                                    value={sqft !== '-' ? sqft : ''}
                                    onChange={(e) => handleFieldChange('sqft', ['property', 'living_area_sqft'], e.target.value)}
                                    placeholder="SQFT"
                                    style={{ fontSize: '0.55rem', width: '100px' }}
                                />
                                <input
                                    className={styles.headerInput}
                                    value={floors !== '-' ? floors : ''}
                                    onChange={(e) => handleFieldChange('floors', ['property', 'levels'], e.target.value)}
                                    placeholder="Floors"
                                    style={{ fontSize: '0.55rem', width: '80px' }}
                                />
                            </div>
                        </>
                    ) : (
                        <>
                            <h1 className={styles.address}>{streetAddress}</h1>
                            <span className={styles.subAddress}>{county.toUpperCase()}, {city.toUpperCase()}, {state.toUpperCase()}</span>
                            <span className={styles.specs}>
                                {bedrooms ? `${bedrooms} BEDS` : ''}, {bathrooms ? `${bathrooms} BATHS` : ''} | {sqft !== '-' ? `${sqft} SQFT` : ''} | {floors !== '-' ? `${floors} FLOORS` : ''}
                            </span>
                        </>
                    )}
                </div>

                <div className={styles.headerRight}>
                    <div className={styles.statGroup}>
                        {renderStatField('LIST PRICE', listPrice, 'listPrice', ['listing_meta', 'list_price'])}
                        {renderStatField('AGREEMENT TYPE', agreementType, 'agreementType', ['listing_meta', 'listing_agreement'])}
                        {renderStatField('EXPIRATION DATE', expirationDate, 'expirationDate', ['listing_meta', 'expiration_date'])}
                        {renderStatField('YEAR BUILT', yearBuilt, 'yearBuilt', ['property', 'year_built'])}
                        {renderStatField('OWNERSHIP', ownership, 'ownership', ['property', 'ownership_type'])}
                    </div>

                    <div className={styles.headerButtons}>
                        <button
                            className={`${styles.modifyButton} ${isEditMode ? styles.modifyActive : ''}`}
                            onClick={toggleEditMode}
                        >
                            {isEditMode ? 'DONE EDITING' : 'MODIFY FIELDS'}
                        </button>
                        <button className={styles.nextButton} onClick={handleNext}>
                            NEXT STEP <ChevronRight size={14} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Scrollable Content */}
            <div className={styles.scrollContainer}>
                <div className={styles.mainGrid}>
                    {/* Left Column: Topics 1-5 */}
                    <div className={styles.leftColumn}>
                        <TopicSection title="1. Agreement & Listing Services" defaultOpen={true}>
                            <EditableField
                                label="Listing Services"
                                value={getFieldValue(['listing_meta', 'listing_service'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('listingServices', ['listing_meta', 'listing_service'], v)}
                            />
                            <EditableField
                                label="Special Conditions"
                                value={getFieldValue(['listing_meta', 'special_conditions']) || 'None'}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('specialConditions', ['listing_meta', 'special_conditions'], v)}
                            />
                            <EditableField
                                label="Property Sub-Type"
                                value={getFieldValue(['property', 'property_sub_type'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('propertySubType', ['property', 'property_sub_type'], v)}
                            />
                            <EditableField
                                label="Listing Agent"
                                value={getFieldValue(['agents', 'listing_agent'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('listingAgent', ['agents', 'listing_agent'], v)}
                            />
                        </TopicSection>

                        <TopicSection title="2. Property Identity & Location" defaultOpen={true}>
                            <EditableField
                                label="Zip Code"
                                value={getFieldValue(['location', 'zip_code'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('zipCode', ['location', 'zip_code'], v)}
                            />
                            <EditableField
                                label="Parcel Number"
                                value={getFieldValue(['location', 'parcel_number'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('parcelNumber', ['location', 'parcel_number'], v)}
                            />
                            <EditableField
                                label="Subdivision"
                                value={getFieldValue(['location', 'subdivision'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('subdivision', ['location', 'subdivision'], v)}
                            />
                            <EditableField
                                label="Legal Description"
                                value={getFieldValue(['location', 'tax_legal_description'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('legalDescription', ['location', 'tax_legal_description'], v)}
                            />
                        </TopicSection>

                        <TopicSection title="3. Physical & Architectural Specs" defaultOpen={true}>
                            <EditableField
                                label="Construction Type"
                                value={getArrayValue(['property', 'construction_material'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('constructionType', ['property', 'construction_material'], v)}
                            />
                            <EditableField
                                label="Foundation"
                                value={getArrayValue(['property', 'foundation_details'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('foundation', ['property', 'foundation_details'], v)}
                            />
                            <EditableField
                                label="Roof Type"
                                value={getArrayValue(['property', 'roof'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('roofType', ['property', 'roof'], v)}
                            />
                            <EditableField
                                label="Property Condition"
                                value={getFieldValue(['property', 'property_condition'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('propertyCondition', ['property', 'property_condition'], v)}
                            />
                            <EditableField
                                label="Lot Size Acres"
                                value={formatDecimal(property?.lot_size_acres as number | null)}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('lotSizeAcres', ['property', 'lot_size_acres'], v)}
                            />
                            <EditableField
                                label="Direction Faces"
                                value={getFieldValue(['property', 'direction_faces'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('directionFaces', ['property', 'direction_faces'], v)}
                            />
                            <EditableField
                                label="Garage Spaces"
                                value={getFieldValue(['property', 'garage_spaces'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('garageSpaces', ['property', 'garage_spaces'], v)}
                            />
                            <EditableField
                                label="Total Parking"
                                value={getFieldValue(['property', 'parking_total'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('totalParking', ['property', 'parking_total'], v)}
                            />
                        </TopicSection>

                        <TopicSection title="4. Interior & Rooms" defaultOpen={true}>
                            <EditableField
                                label="Living Room"
                                value={getFieldValue(['property', 'living_room'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('livingRoom', ['property', 'living_room'], v)}
                            />
                            <EditableField
                                label="Dining Room"
                                value={getFieldValue(['property', 'dining_room'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('diningRoom', ['property', 'dining_room'], v)}
                            />
                            <EditableField
                                label="Fireplaces"
                                value={getArrayValue(['features', 'fireplaces'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('fireplaces', ['features', 'fireplaces'], v)}
                            />
                            <EditableField
                                label="Appliances"
                                value={getArrayValue(['features', 'appliances'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('appliances', ['features', 'appliances'], v)}
                            />
                            <EditableField
                                label="Water Source"
                                value={getArrayValue(['utilities', 'water_source'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('waterSource', ['utilities', 'water_source'], v)}
                            />
                            <EditableField
                                label="Sewer"
                                value={getArrayValue(['utilities', 'sewer'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('sewer', ['utilities', 'sewer'], v)}
                            />
                            <EditableField
                                label="Heating"
                                value={getArrayValue(['utilities', 'heating'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('heating', ['utilities', 'heating'], v)}
                            />
                            <EditableField
                                label="Cooling"
                                value={getArrayValue(['utilities', 'cooling'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('cooling', ['utilities', 'cooling'], v)}
                            />
                            <EditableField
                                label="Flooring"
                                value={getArrayValue(['features', 'flooring'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('flooring', ['features', 'flooring'], v)}
                            />
                        </TopicSection>

                        <TopicSection title="5. Financials" defaultOpen={true}>
                            <EditableField
                                label="Association"
                                value={getBooleanValue(['financial', 'association'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('association', ['financial', 'association'], v)}
                            />
                            <EditableField
                                label="Association Name"
                                value={getFieldValue(['financial', 'association_name'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('associationName', ['financial', 'association_name'], v)}
                            />
                            <EditableField
                                label="Association Fee"
                                value={getCurrencyValue(['financial', 'association_fee'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('associationFee', ['financial', 'association_fee'], v)}
                            />
                            <EditableField
                                label="Association Amount"
                                value={getCurrencyValue(['financial', 'association_amount'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('associationAmount', ['financial', 'association_amount'], v)}
                            />
                            <EditableField
                                label="Acceptable Financing"
                                value={getArrayValue(['financial', 'acceptable_financing'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('acceptableFinancing', ['financial', 'acceptable_financing'], v)}
                            />
                            <EditableField
                                label="Estimated Tax"
                                value={getCurrencyValue(['financial', 'estimated_tax'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('estimatedTax', ['financial', 'estimated_tax'], v)}
                            />
                            <EditableField
                                label="Tax Year"
                                value={getFieldValue(['financial', 'tax_year'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('taxYear', ['financial', 'tax_year'], v)}
                            />
                            <EditableField
                                label="Tax Annual Amount"
                                value={getCurrencyValue(['financial', 'tax_annual_amount'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('taxAnnualAmount', ['financial', 'tax_annual_amount'], v)}
                            />
                            <EditableField
                                label="Tax Assessed Value"
                                value={getCurrencyValue(['financial', 'tax_assessed_value'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('taxAssessedValue', ['financial', 'tax_assessed_value'], v)}
                            />
                            <EditableField
                                label="Tax Rate"
                                value={getPercentageValue(['financial', 'tax_rate'])}
                                forceEdit={isEditMode}
                                onSave={(v) => handleFieldChange('taxRate', ['financial', 'tax_rate'], v)}
                            />
                            <EditableField
                                label="Occupant Type"
                                value={getFieldValue(['showing', 'occupant_type'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('occupantType', ['showing', 'occupant_type'], v)}
                            />
                            <EditableField
                                label="Owner Name"
                                value={getFieldValue(['showing', 'owner_name'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('ownerName', ['showing', 'owner_name'], v)}
                            />
                            <EditableField
                                label="Lockbox Type"
                                value={getFieldValue(['showing', 'lockbox_type'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('lockboxType', ['showing', 'lockbox_type'], v)}
                            />
                            <EditableField
                                label="Showing Instructions"
                                value={getFieldValue(['showing', 'showing_instructions'])}
                                forceEdit={isEditMode}
                                multiline={true}
                                onSave={(v) => handleFieldChange('showingInstructions', ['showing', 'showing_instructions'], v)}
                            />
                        </TopicSection>
                    </div>

                    {/* Right Column: Topics 6-7 */}
                    <div className={styles.rightColumn}>
                        <TopicSection title="6. Location & Environmental" defaultOpen={true}>
                            <div style={{ gridColumn: '1 / -1', marginBottom: '0.1rem' }}>
                                <PropertyMap
                                    latitude={location?.latitude as number | null}
                                    longitude={location?.longitude as number | null}
                                    onLatitudeChange={(v) => handleFieldChange('latitude', ['location', 'latitude'], String(v || ''))}
                                    onLongitudeChange={(v) => handleFieldChange('longitude', ['location', 'longitude'], String(v || ''))}
                                />
                            </div>
                            <div style={{ gridColumn: '1 / -1' }}>
                                <EditableField
                                    label="Property Description"
                                    value={getFieldValue(['remarks', 'ai_property_description'])}
                                    forceEdit={isEditMode}
                                    multiline={true}
                                    onSave={(v) => handleFieldChange('propertyDescription', ['remarks', 'ai_property_description'], v)}
                                />
                            </div>
                        </TopicSection>

                        <TopicSection title="7. Marketing Remarks" defaultOpen={true}>
                            <div style={{ gridColumn: '1 / -1' }}>
                                <EditableField
                                    label="Public Remarks"
                                    value={getFieldValue(['remarks', 'public_remarks'])}
                                    forceEdit={isEditMode}
                                    multiline={true}
                                    onSave={(v) => handleFieldChange('publicRemarks', ['remarks', 'public_remarks'], v)}
                                />
                            </div>
                            <div style={{ gridColumn: '1 / -1' }}>
                                <EditableField
                                    label="Private Remarks"
                                    value={getFieldValue(['remarks', 'private_remarks'])}
                                    forceEdit={isEditMode}
                                    multiline={true}
                                    onSave={(v) => handleFieldChange('privateRemarks', ['remarks', 'private_remarks'], v)}
                                />
                            </div>
                        </TopicSection>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ReviewPage;

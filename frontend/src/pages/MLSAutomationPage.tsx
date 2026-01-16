import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../lib/api-client';
import styles from './MLSAutomationPage.module.css';

interface CanonicalListing {
    [key: string]: unknown;
}

interface MLSFieldMapping {
    canonical_path: string;
    confidence: number;
    type: string;
}

interface MLSMappingResult {
    field_mappings: {
        [section: string]: {
            [fieldName: string]: MLSFieldMapping;
        };
    };
    transformed_fields: {
        [fieldName: string]: unknown;
    };
    unmapped_required_fields: string[];
    mapping_notes: Array<{
        mls_field: string;
        canonical_source: string;
        action: string;
        confidence: number;
    }>;
    validation: {
        ready_for_autofill: boolean;
        blocking_issues?: string[];
        errors?: string[];
        warnings: string[];
    };
    ready_for_autofill: boolean;
    saved: boolean;
}

export default function MLSAutomationPage() {
    const { listingId } = useParams<{ listingId: string }>();
    const navigate = useNavigate();
    const [canonical, setCanonical] = useState<CanonicalListing | null>(null);
    const [mappingResult, setMappingResult] = useState<MLSMappingResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [mapping, setMapping] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showCanonical, setShowCanonical] = useState(true);
    const [showMappedFields, setShowMappedFields] = useState(false);

    useEffect(() => {
        if (!listingId) {
            navigate('/', { replace: true });
            return;
        }

        loadCanonical();
    }, [listingId, navigate]);

    const loadCanonical = async () => {
        if (!listingId) return;

        try {
            setLoading(true);
            setError(null);
            const data = await apiClient.get(`/listings/${listingId}/canonical`);
            setCanonical(data);
        } catch (err) {
            console.error('Failed to load canonical:', err);
            setError(err instanceof Error ? err.message : 'Failed to load canonical listing');
        } finally {
            setLoading(false);
        }
    };

    const handleMapMLSFields = async () => {
        if (!listingId) return;

        try {
            setMapping(true);
            setError(null);
            const result = await apiClient.get(`/listings/${listingId}/mls-fields?mls_system=unlock_mls`);
            console.log('Mapping result:', result);
            
            // Ensure validation object exists with proper structure
            if (!result.validation) {
                result.validation = {
                    ready_for_autofill: result.ready_for_autofill || false,
                    blocking_issues: [],
                    warnings: []
                };
            }
            
            // Normalize blocking_issues to errors for display
            if (result.validation.blocking_issues && !result.validation.errors) {
                result.validation.errors = result.validation.blocking_issues;
            }
            
            // Ensure arrays exist
            if (!Array.isArray(result.validation.errors)) {
                result.validation.errors = [];
            }
            if (!Array.isArray(result.validation.warnings)) {
                result.validation.warnings = [];
            }
            if (!Array.isArray(result.unmapped_required_fields)) {
                result.unmapped_required_fields = [];
            }
            if (!result.transformed_fields) {
                result.transformed_fields = {};
            }
            if (!result.field_mappings) {
                result.field_mappings = {};
            }
            
            setMappingResult(result);
            setShowMappedFields(true);
        } catch (err) {
            console.error('Failed to map MLS fields:', err);
            const errorMessage = err instanceof Error ? err.message : 'Failed to map MLS fields';
            setError(errorMessage);
            setMappingResult(null);
            setShowMappedFields(false);
        } finally {
            setMapping(false);
        }
    };

    if (loading) {
        return (
            <div className={styles.container}>
                <div className={styles.loading}>Loading canonical listing...</div>
            </div>
        );
    }

    if (error && !canonical) {
        return (
            <div className={styles.container}>
                <div className={styles.error}>{error}</div>
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h1 className={styles.title}>MLS Automation</h1>
                <button
                    className={styles.backButton}
                    onClick={() => navigate(`/media/${listingId}`)}
                >
                    ← Back to Media
                </button>
            </div>

            {error && (
                <div className={styles.errorBanner}>{error}</div>
            )}

            <div className={styles.content}>
                {/* Canonical JSON Section */}
                <div className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <h2 className={styles.sectionTitle}>Locked Canonical JSON</h2>
                        <button
                            className={styles.toggleButton}
                            onClick={() => setShowCanonical(!showCanonical)}
                        >
                            {showCanonical ? 'Hide' : 'Show'}
                        </button>
                    </div>
                    {showCanonical && canonical && (
                        <div className={styles.jsonContainer}>
                            <pre className={styles.jsonContent}>
                                {JSON.stringify(canonical, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>

                {/* Mapping Section */}
                <div className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <h2 className={styles.sectionTitle}>MLS Field Mapping</h2>
                        <button
                            className={styles.mapButton}
                            onClick={handleMapMLSFields}
                            disabled={mapping || !canonical}
                        >
                            {mapping ? 'Mapping...' : 'Map Fields to Unlock MLS'}
                        </button>
                    </div>

                    {mapping && (
                        <div className={styles.loading}>Mapping fields to Unlock MLS...</div>
                    )}

                    {mappingResult && showMappedFields && !mapping && (
                        <div className={styles.mappingResults}>
                            {/* Validation Status */}
                            <div className={styles.validationSection}>
                                <h3 className={styles.subsectionTitle}>Validation Status</h3>
                                <div className={styles.statusRow}>
                                    <span className={styles.statusLabel}>Ready for Autofill:</span>
                                    <span className={`${styles.statusValue} ${mappingResult.ready_for_autofill ? styles.success : styles.warning}`}>
                                        {mappingResult.ready_for_autofill ? 'Yes' : 'No'}
                                    </span>
                                </div>
                                {mappingResult.validation && mappingResult.validation.errors && mappingResult.validation.errors.length > 0 && (
                                    <div className={styles.errors}>
                                        <h4>Errors:</h4>
                                        <ul>
                                            {mappingResult.validation.errors.map((err: string, idx: number) => (
                                                <li key={idx}>{err}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                {mappingResult.validation && mappingResult.validation.warnings && mappingResult.validation.warnings.length > 0 && (
                                    <div className={styles.warnings}>
                                        <h4>Warnings:</h4>
                                        <ul>
                                            {mappingResult.validation.warnings.map((warn: string, idx: number) => (
                                                <li key={idx}>{warn}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>

                            {/* Unmapped Required Fields */}
                            {mappingResult.unmapped_required_fields && mappingResult.unmapped_required_fields.length > 0 && (
                                <div className={styles.unmappedSection}>
                                    <h3 className={styles.subsectionTitle}>Unmapped Required Fields</h3>
                                    <ul className={styles.unmappedList}>
                                        {mappingResult.unmapped_required_fields.map((field: string, idx: number) => (
                                            <li key={idx}>{field}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Mapped Fields */}
                            {mappingResult.transformed_fields && Object.keys(mappingResult.transformed_fields).length > 0 && (
                                <div className={styles.mappedFieldsSection}>
                                    <h3 className={styles.subsectionTitle}>Mapped Fields</h3>
                                    <div className={styles.fieldsGrid}>
                                        {Object.entries(mappingResult.transformed_fields).map(([fieldName, value]) => {
                                            const fieldMapping = mappingResult.field_mappings 
                                                ? Object.values(mappingResult.field_mappings)
                                                    .flatMap((section: any) => Object.entries(section))
                                                    .find(([name]: [string, any]) => name === fieldName)?.[1]
                                                : undefined;

                                            return (
                                                <div key={fieldName} className={styles.fieldCard}>
                                                    <div className={styles.fieldHeader}>
                                                        <span className={styles.fieldName}>{fieldName}</span>
                                                        {fieldMapping && (
                                                            <span className={styles.confidence}>
                                                                Confidence: {(fieldMapping.confidence * 100).toFixed(0)}%
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className={styles.fieldValue}>
                                                        {typeof value === 'object' && value !== null
                                                            ? JSON.stringify(value, null, 2)
                                                            : String(value ?? 'null')}
                                                    </div>
                                                    {fieldMapping && (
                                                        <div className={styles.fieldSource}>
                                                            Source: {fieldMapping.canonical_path || 'default'}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Field Mappings Details */}
                            {mappingResult.field_mappings && Object.keys(mappingResult.field_mappings).length > 0 && (
                                <div className={styles.mappingsSection}>
                                    <h3 className={styles.subsectionTitle}>Field Mappings Configuration</h3>
                                    <div className={styles.mappingsContainer}>
                                        {Object.entries(mappingResult.field_mappings).map(([section, fields]) => (
                                            <div key={section} className={styles.mappingSection}>
                                                <h4 className={styles.mappingSectionTitle}>{section}</h4>
                                                <div className={styles.mappingFields}>
                                                    {Object.entries(fields as Record<string, MLSFieldMapping>).map(([fieldName, mapping]) => (
                                                        <div key={fieldName} className={styles.mappingField}>
                                                            <span className={styles.mappingFieldName}>{fieldName}</span>
                                                            <span className={styles.mappingPath}>
                                                                → {mapping.canonical_path || 'default'}
                                                            </span>
                                                            <span className={styles.mappingType}>({mapping.type})</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

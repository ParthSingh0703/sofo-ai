import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../lib/api-client';
import { listingsApi, type AutomationResult } from '../services/api';
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
    const [automationRunning, setAutomationRunning] = useState(false);
    const [automationResult, setAutomationResult] = useState<AutomationResult | null>(null);
    const [mlsSystem, setMlsSystem] = useState('unlock_mls');
    const [mlsUrl, setMlsUrl] = useState('');
    const [screenshotTimestamp, setScreenshotTimestamp] = useState(Date.now());
    const [browserSessionActive, setBrowserSessionActive] = useState(false);
    const [openingSite, setOpeningSite] = useState(false);

    useEffect(() => {
        if (!listingId) {
            navigate('/', { replace: true });
            return;
        }

        loadCanonical();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [listingId, navigate]);

    // Poll for session status when mapping is ready
    useEffect(() => {
        if (!mappingResult || !listingId) return;

        const checkSession = async () => {
            try {
                const status = await listingsApi.getSessionStatus(listingId);
                setBrowserSessionActive(status.is_active);
            } catch (err) {
                console.error('Failed to check session status:', err);
            }
        };

        // Check immediately
        checkSession();

        // Poll every 2 seconds
        const interval = setInterval(checkSession, 2000);
        return () => clearInterval(interval);
    }, [mappingResult, listingId]);

    // Poll for live screenshot updates when browser session is active
    useEffect(() => {
        if (!browserSessionActive || !listingId) return;

        const interval = setInterval(() => {
            setScreenshotTimestamp(Date.now());
        }, 1000); // Update every second

        return () => clearInterval(interval);
    }, [browserSessionActive, listingId]);

    const loadCanonical = async () => {
        if (!listingId) return;

        try {
            setLoading(true);
            setError(null);
            const data = await apiClient.get(`/listings/${listingId}/canonical`) as CanonicalListing;
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
            const result = await apiClient.get(`/listings/${listingId}/mls-fields?mls_system=${mlsSystem}`) as MLSMappingResult;
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

    const handleOpenSite = async () => {
        if (!listingId) return;

        try {
            setOpeningSite(true);
            setError(null);
            
            const result = await listingsApi.openListingSite(
                listingId,
                mlsSystem,
                mlsUrl || undefined
            );
            
            if (result.status === 'opened' || result.status === 'already_open') {
                setBrowserSessionActive(true);
            } else {
                setError(result.message || 'Failed to open site');
            }
        } catch (err) {
            console.error('Failed to open site:', err);
            setError(err instanceof Error ? err.message : 'Failed to open site');
        } finally {
            setOpeningSite(false);
        }
    };

    const handleStartAutomation = async () => {
        if (!listingId) return;

        try {
            setAutomationRunning(true);
            setError(null);
            setAutomationResult(null);
            
            const result = await listingsApi.startAutomation(
                listingId,
                mlsSystem,
                mlsUrl || undefined
            );
            
            console.log('Automation result:', result);
            setAutomationResult(result);
        } catch (err) {
            console.error('Failed to start automation:', err);
            const errorMessage = err instanceof Error ? err.message : 'Failed to start automation';
            setError(errorMessage);
            setAutomationResult({
                status: 'failed',
                login_skipped: false,
                new_mls: false,
                fields_filled: 0,
                fields_skipped: 0,
                enums_learned: 0,
                images_updated: 0,
                errors: [errorMessage],
                warnings: [],
                screenshot_paths: []
            });
        } finally {
            setAutomationRunning(false);
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
                        <div className={styles.buttonGroup}>
                            <select
                                className={styles.mlsSelect}
                                value={mlsSystem}
                                onChange={(e) => setMlsSystem(e.target.value)}
                                disabled={mapping || automationRunning}
                            >
                                <option value="unlock_mls">Unlock MLS</option>
                            </select>
                            <button
                                className={styles.mapButton}
                                onClick={handleMapMLSFields}
                                disabled={mapping || !canonical || automationRunning}
                            >
                                {mapping ? 'Mapping...' : 'Map Fields'}
                            </button>
                        </div>
                    </div>
                    
                    {/* MLS URL input for new MLS systems */}
                    <div className={styles.mlsUrlInput}>
                        <label htmlFor="mls-url">MLS URL (for new MLS systems):</label>
                        <input
                            id="mls-url"
                            type="text"
                            value={mlsUrl}
                            onChange={(e) => setMlsUrl(e.target.value)}
                            placeholder="https://example-mls.com"
                            disabled={mapping || automationRunning}
                            className={styles.urlInput}
                        />
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
                                            const fieldMapping: MLSFieldMapping | undefined = mappingResult.field_mappings 
                                                ? Object.values(mappingResult.field_mappings)
                                                    .flatMap((section: Record<string, MLSFieldMapping>) => Object.entries(section))
                                                    .find(([name]: [string, MLSFieldMapping]) => name === fieldName)?.[1]
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
                                                    {Object.entries(fields as Record<string, MLSFieldMapping>).map(([fieldName, mapping]: [string, MLSFieldMapping]) => (
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

                {/* Browser Automation Section */}
                <div className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <h2 className={styles.sectionTitle}>Browser Automation</h2>
                        {!browserSessionActive ? (
                            <button
                                className={styles.automationButton}
                                onClick={handleOpenSite}
                                disabled={openingSite || !mappingResult || !mappingResult.ready_for_autofill}
                            >
                                {openingSite ? 'Opening Site...' : 'Open Listing Site'}
                            </button>
                        ) : (
                            <button
                                className={styles.automationButton}
                                onClick={handleStartAutomation}
                                disabled={automationRunning}
                            >
                                {automationRunning ? 'Running Automation...' : 'Start Automation'}
                            </button>
                        )}
                    </div>

                    {!mappingResult && (
                        <div className={styles.infoMessage}>
                            Please map MLS fields first before opening the listing site.
                        </div>
                    )}

                    {mappingResult && !mappingResult.ready_for_autofill && (
                        <div className={styles.warningMessage}>
                            ⚠️ Mapping validation failed. Please fix errors before opening the site.
                        </div>
                    )}

                    {browserSessionActive && !automationRunning && (
                        <div className={styles.automationStatus}>
                            <div className={styles.statusIndicator}>
                                <span>Browser is open. Navigate and login, then click 'Start Automation' when ready.</span>
                            </div>
                            <div className={styles.browserViewContainer}>
                                <h3 className={styles.subsectionTitle}>Live Browser View</h3>
                                <div className={styles.browserViewBox}>
                                    {listingId && (
                                        <img
                                            key={screenshotTimestamp}
                                            src={`/api/automation/listings/${listingId}/live-screenshot?t=${screenshotTimestamp}`}
                                            alt="Live browser view"
                                            className={styles.browserViewImage}
                                            onError={(e) => {
                                                // Screenshot might not be available yet - will retry on next poll
                                                const img = e.target as HTMLImageElement;
                                                img.style.display = 'none';
                                            }}
                                        />
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {automationRunning && (
                        <div className={styles.automationStatus}>
                            <div className={styles.statusIndicator}>
                                <div className={styles.spinner}></div>
                                <span>Automation in progress...</span>
                            </div>
                            <div className={styles.browserViewContainer}>
                                <h3 className={styles.subsectionTitle}>Live Browser View</h3>
                                <div className={styles.browserViewBox}>
                                    {listingId && (
                                        <img
                                            key={screenshotTimestamp}
                                            src={`/api/automation/listings/${listingId}/live-screenshot?t=${screenshotTimestamp}`}
                                            alt="Live browser view"
                                            className={styles.browserViewImage}
                                            onError={(e) => {
                                                // Screenshot might not be available yet - will retry on next poll
                                                const img = e.target as HTMLImageElement;
                                                img.style.display = 'none';
                                            }}
                                        />
                                    )}
                                </div>
                                <p className={styles.statusNote}>
                                    You may need to log in manually in the browser window. The live view updates automatically.
                                </p>
                            </div>
                        </div>
                    )}

                    {automationResult && !automationRunning && (
                        <div className={styles.automationResults}>
                            <div className={styles.resultHeader}>
                                <h3 className={styles.subsectionTitle}>Automation Results</h3>
                                <span className={`${styles.statusBadge} ${automationResult.status === 'saved' ? styles.success : styles.failed}`}>
                                    {automationResult.status.toUpperCase()}
                                </span>
                            </div>

                            <div className={styles.resultStats}>
                                <div className={styles.statItem}>
                                    <span className={styles.statLabel}>Fields Filled:</span>
                                    <span className={styles.statValue}>{automationResult.fields_filled}</span>
                                </div>
                                <div className={styles.statItem}>
                                    <span className={styles.statLabel}>Fields Skipped:</span>
                                    <span className={styles.statValue}>{automationResult.fields_skipped}</span>
                                </div>
                                <div className={styles.statItem}>
                                    <span className={styles.statLabel}>Images Uploaded:</span>
                                    <span className={styles.statValue}>{automationResult.images_updated}</span>
                                </div>
                                <div className={styles.statItem}>
                                    <span className={styles.statLabel}>Login Skipped:</span>
                                    <span className={styles.statValue}>{automationResult.login_skipped ? 'Yes' : 'No'}</span>
                                </div>
                            </div>

                            {automationResult.errors && automationResult.errors.length > 0 && (
                                <div className={styles.errors}>
                                    <h4>Errors:</h4>
                                    <ul>
                                        {automationResult.errors.map((err, idx) => (
                                            <li key={idx}>{err}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {automationResult.warnings && automationResult.warnings.length > 0 && (
                                <div className={styles.warnings}>
                                    <h4>Warnings:</h4>
                                    <ul>
                                        {automationResult.warnings.map((warn, idx) => (
                                            <li key={idx}>{warn}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {automationResult.screenshot_paths && automationResult.screenshot_paths.length > 0 && (
                                <div className={styles.screenshotsSection}>
                                    <h4>Screenshots:</h4>
                                    <div className={styles.screenshotsGrid}>
                                        {automationResult.screenshot_paths.map((path, idx) => {
                                            // Construct full URL to screenshot using automation endpoint
                                            const screenshotUrl = `/api/automation/screenshots/${path}`;
                                            return (
                                                <div key={idx} className={styles.screenshotItem}>
                                                    <img
                                                        src={screenshotUrl}
                                                        alt={`Automation screenshot ${idx + 1}`}
                                                        className={styles.screenshot}
                                                        onError={(e) => {
                                                            (e.target as HTMLImageElement).style.display = 'none';
                                                        }}
                                                    />
                                                    <span className={styles.screenshotLabel}>
                                                        {path.split('/').pop()?.replace('.png', '').replace(/_/g, ' ') || `Screenshot ${idx + 1}`}
                                                    </span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {automationResult.completed_at && (
                                <div className={styles.completedTime}>
                                    Completed at: {new Date(automationResult.completed_at).toLocaleString()}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

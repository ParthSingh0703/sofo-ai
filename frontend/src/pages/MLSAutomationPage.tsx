import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient } from "../lib/api-client";
import { listingsApi, type AutomationResult } from "../services/api";
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
  const [mappingResult, setMappingResult] = useState<MLSMappingResult | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [mapping, setMapping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCanonical, setShowCanonical] = useState(true);
  const [showMappedFields, setShowMappedFields] = useState(false);
  const [automationRunning, setAutomationRunning] = useState(false);
  const [automationResult, setAutomationResult] =
    useState<AutomationResult | null>(null);
  const [mlsSystem, setMlsSystem] = useState("unlock_mls");
  const [mlsUrl, setMlsUrl] = useState("");
  const [screenshotTimestamp, setScreenshotTimestamp] = useState(Date.now());
  const [browserSessionActive, setBrowserSessionActive] = useState(false);
  const [openingSite, setOpeningSite] = useState(false);

  useEffect(() => {
    if (!listingId) {
      navigate("/", { replace: true });
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
        console.error("Failed to check session status:", err);
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
      const data = (await apiClient.get(
        `/listings/${listingId}/canonical`,
      )) as CanonicalListing;
      setCanonical(data);
    } catch (err) {
      console.error("Failed to load canonical:", err);
      setError(
        err instanceof Error ? err.message : "Failed to load canonical listing",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleMapMLSFields = async () => {
    if (!listingId) return;

    try {
      setMapping(true);
      setError(null);
      const result = (await apiClient.get(
        `/listings/${listingId}/mls-fields?mls_system=${mlsSystem}`,
      )) as MLSMappingResult;
      console.log("Mapping result:", result);

      // Ensure validation object exists with proper structure
      if (!result.validation) {
        result.validation = {
          ready_for_autofill: result.ready_for_autofill || false,
          blocking_issues: [],
          warnings: [],
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
      console.error("Failed to map MLS fields:", err);
      const errorMessage =
        err instanceof Error ? err.message : "Failed to map MLS fields";
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
        mlsUrl || undefined,
      );

      if (result.status === "opened" || result.status === "already_open") {
        setBrowserSessionActive(true);
      } else {
        setError(result.message || "Failed to open site");
      }
    } catch (err) {
      console.error("Failed to open site:", err);
      setError(err instanceof Error ? err.message : "Failed to open site");
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
        mlsUrl || undefined,
      );

      console.log("Automation result:", result);
      setAutomationResult(result);
    } catch (err) {
      console.error("Failed to start automation:", err);
      const errorMessage =
        err instanceof Error ? err.message : "Failed to start automation";
      setError(errorMessage);
      setAutomationResult({
        status: "failed",
        login_skipped: false,
        new_mls: false,
        fields_filled: 0,
        fields_skipped: 0,
        enums_learned: 0,
        images_updated: 0,
        errors: [errorMessage],
        warnings: [],
        screenshot_paths: [],
      });
    } finally {
      setAutomationRunning(false);
    }
  };

  if (loading) {
    return (
      <div
        className="
        min-h-screen
        bg-[#0F1115]
        text-white
        p-8
        flex items-center justify-center
      "
      >
        <div className="text-gray-400 italic text-[1.1rem]">
          Loading canonical listing...
        </div>
      </div>
    );
  }

  if (error && !canonical) {
    return (
      <div
        className="
        min-h-screen
        bg-[#0F1115]
        text-white
        p-8
        flex items-center justify-center
      "
      >
        <div className="text-red-400 text-[1.1rem]">{error}</div>
      </div>
    );
  }

  return (
    <div
      className="
            min-h-screen
            bg-[#0F1115]
            text-white
            p-8
        "
    >
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-[2rem] font-semibold text-white">MLS Automation</h1>

        <button
          onClick={() => navigate(`/media/${listingId}`)}
          className="
            px-4 py-2
            bg-[#1a1d24]
            text-white
            border border-[#2d3139]
            rounded-lg
            text-[0.9rem]
            cursor-pointer
            transition-all duration-200
            hover:bg-[#2d3139]
            hover:border-blue-500
            "
        >
          ← Back to Media
        </button>
      </div>

      {error && (
        <div
          className="
            bg-red-900
            text-white
            p-4
            rounded-lg
            mb-6
            border border-red-700
            "
        >
          {error}
        </div>
      )}

      <div className="flex flex-col gap-8">
        {/* Canonical JSON Section */}
        <div
          className="
                bg-[#1a1d24]
                border border-[#2d3139]
                rounded-xl
                p-6
            "
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[1.5rem] font-semibold text-white">
              Locked Canonical JSON
            </h2>

            <button
              onClick={() => setShowCanonical(!showCanonical)}
              className="
                    px-4 py-2
                    bg-[#2d3139]
                    text-white
                    border border-[#3d4149]
                    rounded-lg
                    text-[0.9rem]
                    cursor-pointer
                    transition-all duration-200
                    hover:bg-[#3d4149]
                    hover:border-blue-500
                "
            >
              {showCanonical ? "Hide" : "Show"}
            </button>
          </div>

          {showCanonical && canonical && (
            <div
              className="
                    bg-[#0F1115]
                    border border-[#2d3139]
                    rounded-lg
                    p-4
                    max-h-[600px]
                    overflow-auto
                "
            >
              <pre
                className="
                    m-0
                    font-mono
                    text-[0.85rem]
                    leading-[1.5]
                    text-gray-200
                    whitespace-pre-wrap
                    break-words
                    "
              >
                {JSON.stringify(canonical, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Mapping Section */}
        <div
          className="
                bg-[#1a1d24]
                border border-[#2d3139]
                rounded-xl
                p-6
            "
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[1.5rem] font-semibold text-white">
              MLS Field Mapping
            </h2>

            <div className="flex gap-2 items-center">
              <select
                value={mlsSystem}
                onChange={(e) => setMlsSystem(e.target.value)}
                disabled={mapping || automationRunning}
                className="
                    px-4 py-2
                    bg-[#1a1d24]
                    text-white
                    border border-[#2d3139]
                    rounded-lg
                    text-[0.9rem]
                    cursor-pointer
                    transition-all duration-200
                    hover:border-blue-500
                    disabled:opacity-50
                    disabled:cursor-not-allowed
                    "
              >
                <option value="unlock_mls">Unlock MLS</option>
              </select>

              <button
                onClick={handleMapMLSFields}
                disabled={mapping || !canonical || automationRunning}
                className="
                    px-6 py-3
                    bg-blue-500
                    text-white
                    rounded-lg
                    text-[1rem]
                    font-medium
                    transition-all duration-200
                    hover:bg-blue-600
                    disabled:opacity-50
                    disabled:cursor-not-allowed
                    "
              >
                {mapping ? "Mapping..." : "Map Fields"}
              </button>
            </div>
          </div>

          {/* MLS URL input for new MLS systems */}
          <div className="mt-4 flex flex-col gap-2">
            <label
              htmlFor="mls-url"
              className="text-[0.9rem] text-gray-400 font-medium"
            >
              MLS URL (for new MLS systems):
            </label>
            <input
              id="mls-url"
              type="text"
              value={mlsUrl}
              onChange={(e) => setMlsUrl(e.target.value)}
              placeholder="https://example-mls.com"
              disabled={mapping || automationRunning}
              className="
                    px-4 py-2
                    bg-[#0F1115]
                    text-white
                    border border-[#2d3139]
                    rounded-lg
                    text-[0.9rem]
                    transition-all duration-200
                    focus:outline-none
                    focus:border-blue-500
                    disabled:opacity-50
                    disabled:cursor-not-allowed
                "
            />
          </div>

          {mapping && (
            <div className="text-center p-8 text-gray-400 italic text-[1.1rem]">
              Mapping fields to Unlock MLS...
            </div>
          )}

          {mappingResult && showMappedFields && !mapping && (
            <div className="flex flex-col gap-8">
              {/* Validation Status */}
              <div className="bg-[#0F1115] border border-[#2d3139] rounded-lg p-4">
                <h3 className="text-[1.25rem] font-semibold text-white mb-4">
                  Validation Status
                </h3>

                <div className="flex items-center gap-4 mb-4">
                  <span className="font-medium text-gray-400">
                    Ready for Autofill:
                  </span>
                  <span
                    className={`
              font-semibold
              px-3 py-1
              rounded
              ${
                mappingResult.ready_for_autofill
                  ? "bg-emerald-900 text-emerald-300"
                  : "bg-yellow-900 text-yellow-300"
              }
            `}
                  >
                    {mappingResult.ready_for_autofill ? "Yes" : "No"}
                  </span>
                </div>

                {mappingResult.validation &&
                  mappingResult.validation.errors &&
                  mappingResult.validation.errors.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-red-400 mb-2">Errors:</h4>
                      <ul className="pl-6 text-gray-200 list-disc">
                        {mappingResult.validation.errors.map((err, idx) => (
                          <li key={idx}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                {mappingResult.validation?.warnings?.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-yellow-400 mb-2">Warnings:</h4>
                    <ul className="pl-6 text-gray-200 list-disc">
                      {mappingResult.validation.warnings.map((warn, idx) => (
                        <li key={idx}>{warn}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Unmapped Required Fields */}
              {mappingResult.unmapped_required_fields?.length > 0 && (
                <div className="bg-[#0F1115] border border-[#2d3139] rounded-lg p-4">
                  <h3 className="text-[1.25rem] font-semibold text-white mb-4">
                    Unmapped Required Fields
                  </h3>
                  <ul className="pl-6 text-red-400 list-disc">
                    {mappingResult.unmapped_required_fields.map(
                      (field, idx) => (
                        <li key={idx}>{field}</li>
                      ),
                    )}
                  </ul>
                </div>
              )}

              {/* Mapped Fields */}
              {mappingResult.transformed_fields &&
                Object.keys(mappingResult.transformed_fields).length > 0 && (
                  <div className="bg-[#0F1115] border border-[#2d3139] rounded-lg p-4">
                    <h3 className="text-[1.25rem] font-semibold text-white mb-4">
                      Mapped Fields
                    </h3>

                    <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4">
                      {Object.entries(mappingResult.transformed_fields).map(
                        ([fieldName, value]) => {
                          const fieldMapping = mappingResult.field_mappings
                            ? Object.values(mappingResult.field_mappings)
                                .flatMap((section) => Object.entries(section))
                                .find(([name]) => name === fieldName)?.[1]
                            : undefined;

                          return (
                            <div
                              key={fieldName}
                              className="
                                    bg-[#1a1d24]
                                    border border-[#2d3139]
                                    rounded-lg
                                    p-4
                                    flex flex-col
                                    gap-2
                                "
                            >
                              <div className="flex justify-between items-center">
                                <span className="font-semibold text-blue-500 text-[0.95rem]">
                                  {fieldName}
                                </span>
                                {fieldMapping && (
                                  <span className="text-[0.75rem] text-gray-400 bg-[#0F1115] px-2 py-1 rounded">
                                    Confidence:{" "}
                                    {(fieldMapping.confidence * 100).toFixed(0)}
                                    %
                                  </span>
                                )}
                              </div>

                              <div className="text-gray-200 text-[0.9rem] break-words max-h-[150px] overflow-y-auto p-2 bg-[#0F1115] rounded font-mono">
                                {typeof value === "object" && value !== null
                                  ? JSON.stringify(value, null, 2)
                                  : String(value ?? "null")}
                              </div>

                              {fieldMapping && (
                                <div className="text-[0.75rem] text-gray-400 italic">
                                  Source:{" "}
                                  {fieldMapping.canonical_path || "default"}
                                </div>
                              )}
                            </div>
                          );
                        },
                      )}
                    </div>
                  </div>
                )}

              {/* Field Mappings Details */}
              {mappingResult.field_mappings &&
                Object.keys(mappingResult.field_mappings).length > 0 && (
                  <div className="bg-[#0F1115] border border-[#2d3139] rounded-lg p-4">
                    <h3 className="text-[1.25rem] font-semibold text-white mb-4">
                      Field Mappings Configuration
                    </h3>

                    <div className="flex flex-col gap-6">
                      {Object.entries(mappingResult.field_mappings).map(
                        ([section, fields]) => (
                          <div
                            key={section}
                            className="bg-[#1a1d24] border border-[#2d3139] rounded-lg p-4"
                          >
                            <h4 className="text-[1.1rem] font-semibold text-white mb-3">
                              {section}
                            </h4>

                            <div className="flex flex-col gap-2">
                              {Object.entries(fields).map(
                                ([fieldName, mapping]) => (
                                  <div
                                    key={fieldName}
                                    className="
                              flex items-center gap-3
                              p-2
                              bg-[#0F1115]
                              rounded
                              text-[0.9rem]
                            "
                                  >
                                    <span className="font-medium text-blue-500 min-w-[150px]">
                                      {fieldName}
                                    </span>
                                    <span className="text-gray-400 flex-1">
                                      → {mapping.canonical_path || "default"}
                                    </span>
                                    <span className="text-gray-500 text-[0.8rem]">
                                      ({mapping.type})
                                    </span>
                                  </div>
                                ),
                              )}
                            </div>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                )}
            </div>
          )}
        </div>

        {/* Browser Automation Section */}
        <div
          className="
                bg-[#1a1d24]
                border border-[#2d3139]
                rounded-xl
                p-6
            "
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[1.5rem] font-semibold text-white">
              Browser Automation
            </h2>

            {!browserSessionActive ? (
              <button
                onClick={handleOpenSite}
                disabled={
                  openingSite ||
                  !mappingResult ||
                  !mappingResult.ready_for_autofill
                }
                className="
                        px-6 py-3
                        bg-emerald-500
                        text-white
                        rounded-lg
                        text-[1rem]
                        font-medium
                        transition-all duration-200
                        hover:bg-emerald-600
                        disabled:opacity-50
                        disabled:cursor-not-allowed
                        "
              >
                {openingSite ? "Opening Site..." : "Open Listing Site"}
              </button>
            ) : (
              <button
                onClick={handleStartAutomation}
                disabled={automationRunning}
                className="
                        px-6 py-3
                        bg-emerald-500
                        text-white
                        rounded-lg
                        text-[1rem]
                        font-medium
                        transition-all duration-200
                        hover:bg-emerald-600
                        disabled:opacity-50
                        disabled:cursor-not-allowed
                        "
              >
                {automationRunning
                  ? "Running Automation..."
                  : "Start Automation"}
              </button>
            )}
          </div>

          {!mappingResult && (
            <div
              className="
                    mt-4
                    p-4
                    rounded-lg
                    text-[0.9rem]
                    bg-blue-900
                    text-blue-300
                    border border-blue-500
                "
            >
              Please map MLS fields first before opening the listing site.
            </div>
          )}

          {mappingResult && !mappingResult.ready_for_autofill && (
            <div
              className="
                    mt-4
                    p-4
                    rounded-lg
                    text-[0.9rem]
                    bg-[#78350f]
                    text-yellow-300
                    border border-yellow-500
                "
            >
              ⚠️ Mapping validation failed. Please fix errors before opening the
              site.
            </div>
          )}

          {browserSessionActive && !automationRunning && (
            <div
              className="
                    mt-4
                    p-6
                    bg-[#0F1115]
                    border border-[#2d3139]
                    rounded-lg
                "
            >
              <div className="flex items-center gap-4 mb-4 text-blue-500 text-[1rem]">
                <span>
                  Browser is open. Navigate and login, then click &apos;Start
                  Automation&apos; when ready.
                </span>
              </div>

              <div
                className="
                    mt-6
                    p-6
                    bg-[#0F1115]
                    border border-[#2d3139]
                    rounded-lg
                    "
              >
                <h3 className="text-[1.25rem] font-semibold text-white mb-4">
                  Live Browser View
                </h3>

                <div
                  className="
                        w-full
                        max-w-[1200px]
                        mx-auto
                        bg-[#1a1d24]
                        border-2 border-[#2d3139]
                        rounded-lg
                        overflow-hidden
                        min-h-[600px]
                        flex items-center justify-center
                    "
                >
                  {listingId && (
                    <img
                      key={screenshotTimestamp}
                      src={`/api/automation/listings/${listingId}/live-screenshot?t=${screenshotTimestamp}`}
                      alt="Live browser view"
                      className="
                            w-full
                            h-auto
                            max-h-[800px]
                            object-contain
                            block
                            bg-[#0F1115]
                        "
                      onError={(e) => {
                        const img = e.target as HTMLImageElement;
                        img.style.display = "none";
                      }}
                    />
                  )}
                </div>
              </div>
            </div>
          )}

          {automationRunning && (
            <div
              className="
                    mt-4
                    p-6
                    bg-[#0F1115]
                    border border-[#2d3139]
                    rounded-lg
                "
            >
              <div className="flex items-center gap-4 mb-4 text-blue-500 text-[1rem]">
                <div
                  className="
                            w-5 h-5
                            border-[3px] border-[#2d3139]
                            border-t-blue-500
                            rounded-full
                            animate-spin
                        "
                ></div>
                <span>Automation in progress...</span>
              </div>

              <div
                className="
                    mt-6
                    p-6
                    bg-[#0F1115]
                    border border-[#2d3139]
                    rounded-lg
                    "
              >
                <h3 className="text-[1.25rem] font-semibold text-white mb-4">
                  Live Browser View
                </h3>

                <div
                  className="
                        w-full
                        max-w-[1200px]
                        mx-auto
                        bg-[#1a1d24]
                        border-2 border-[#2d3139]
                        rounded-lg
                        overflow-hidden
                        min-h-[600px]
                        flex items-center justify-center
                    "
                >
                  {listingId && (
                    <img
                      key={screenshotTimestamp}
                      src={`/api/automation/listings/${listingId}/live-screenshot?t=${screenshotTimestamp}`}
                      alt="Live browser view"
                      className="
                                w-full
                                h-auto
                                max-h-[800px]
                                object-contain
                                block
                                bg-[#0F1115]
                            "
                      onError={(e) => {
                        const img = e.target as HTMLImageElement;
                        img.style.display = "none";
                      }}
                    />
                  )}
                </div>

                <p className="text-gray-400 text-[0.9rem] italic mt-4">
                  You may need to log in manually in the browser window. The
                  live view updates automatically.
                </p>
              </div>
            </div>
          )}

          {automationResult && !automationRunning && (
            <div
              className="
                    mt-4
                    p-6
                    bg-[#0F1115]
                    border border-[#2d3139]
                    rounded-lg
                "
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-[1.25rem] font-semibold text-white">
                  Automation Results
                </h3>

                <span
                  className={`
                        px-4 py-2
                        rounded-lg
                        font-semibold
                        text-[0.9rem]
                        ${
                          automationResult.status === "saved"
                            ? "bg-emerald-900 text-emerald-300"
                            : "bg-red-900 text-red-400"
                        }
                    `}
                >
                  {automationResult.status.toUpperCase()}
                </span>
              </div>

              <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4 mb-6">
                <div className="flex justify-between items-center p-3 bg-[#1a1d24] border border-[#2d3139] rounded-lg">
                  <span className="text-gray-400 text-[0.9rem]">
                    Fields Filled:
                  </span>
                  <span className="text-white font-semibold text-[1rem]">
                    {automationResult.fields_filled}
                  </span>
                </div>

                <div className="flex justify-between items-center p-3 bg-[#1a1d24] border border-[#2d3139] rounded-lg">
                  <span className="text-gray-400 text-[0.9rem]">
                    Fields Skipped:
                  </span>
                  <span className="text-white font-semibold text-[1rem]">
                    {automationResult.fields_skipped}
                  </span>
                </div>

                <div className="flex justify-between items-center p-3 bg-[#1a1d24] border border-[#2d3139] rounded-lg">
                  <span className="text-gray-400 text-[0.9rem]">
                    Images Uploaded:
                  </span>
                  <span className="text-white font-semibold text-[1rem]">
                    {automationResult.images_updated}
                  </span>
                </div>

                <div className="flex justify-between items-center p-3 bg-[#1a1d24] border border-[#2d3139] rounded-lg">
                  <span className="text-gray-400 text-[0.9rem]">
                    Login Skipped:
                  </span>
                  <span className="text-white font-semibold text-[1rem]">
                    {automationResult.login_skipped ? "Yes" : "No"}
                  </span>
                </div>
              </div>

              {automationResult.errors &&
                automationResult.errors.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-red-400 mb-2">Errors:</h4>
                    <ul className="pl-6 text-gray-200 list-disc">
                      {automationResult.errors.map((err, idx) => (
                        <li key={idx}>{err}</li>
                      ))}
                    </ul>
                  </div>
                )}

              {automationResult.warnings &&
                automationResult.warnings.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-yellow-400 mb-2">Warnings:</h4>
                    <ul className="pl-6 text-gray-200 list-disc">
                      {automationResult.warnings.map((warn, idx) => (
                        <li key={idx}>{warn}</li>
                      ))}
                    </ul>
                  </div>
                )}

              {automationResult.screenshot_paths &&
                automationResult.screenshot_paths.length > 0 && (
                  <div className="mt-6">
                    <h4 className="text-white text-[1.1rem] mb-4">
                      Screenshots:
                    </h4>

                    <div className="grid grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-4">
                      {automationResult.screenshot_paths.map((path, idx) => {
                        const screenshotUrl = `/api/automation/screenshots/${path}`;
                        return (
                          <div
                            key={idx}
                            className="
                      flex flex-col gap-2
                      bg-[#1a1d24]
                      border border-[#2d3139]
                      rounded-lg
                      p-2
                      overflow-hidden
                    "
                          >
                            <img
                              src={screenshotUrl}
                              alt={`Automation screenshot ${idx + 1}`}
                              className="
                        w-full
                        h-auto
                        max-h-[300px]
                        object-contain
                        rounded
                        bg-[#0F1115]
                      "
                              onError={(e) => {
                                (e.target as HTMLImageElement).style.display =
                                  "none";
                              }}
                            />
                            <span className="text-[0.75rem] text-gray-400 text-center capitalize">
                              {path
                                .split("/")
                                .pop()
                                ?.replace(".png", "")
                                .replace(/_/g, " ") || `Screenshot ${idx + 1}`}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

              {automationResult.completed_at && (
                <div className="mt-4 pt-4 border-t border-[#2d3139] text-gray-400 text-[0.85rem] italic">
                  Completed at:{" "}
                  {new Date(automationResult.completed_at).toLocaleString()}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

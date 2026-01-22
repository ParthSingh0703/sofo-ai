import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAppDispatch } from "../../store/hooks";
import { setCurrentListing } from "../../store/slices/listingsSlice";
import { apiClient } from "../../lib/api-client";

// ---------- Helper functions (UNCHANGED) ----------

const isExtractionComplete = (canonical: unknown): boolean => {
  if (!canonical || typeof canonical !== "object") return false;

  const c = canonical as Record<string, unknown>;
  const listingMeta = c.listing_meta as Record<string, unknown> | undefined;
  const property = c.property as Record<string, unknown> | undefined;
  const location = c.location as Record<string, unknown> | undefined;
  const financial = c.financial as Record<string, unknown> | undefined;

  return !!(
    listingMeta?.list_price ||
    property?.living_area_sqft ||
    property?.year_built ||
    location?.street_address ||
    property?.property_sub_type ||
    financial?.tax_year
  );
};

const isEnrichmentComplete = (canonical: unknown): boolean => {
  if (!canonical || typeof canonical !== "object") return false;

  const c = canonical as Record<string, unknown>;
  const remarks = c.remarks as Record<string, unknown> | undefined;
  const location = c.location as Record<string, unknown> | undefined;
  const media = c.media as Record<string, unknown> | undefined;

  const poi = location?.poi as unknown[] | undefined;
  const mediaImages = media?.media_images as unknown[] | undefined;

  return !!(
    remarks?.public_remarks ||
    remarks?.ai_property_description ||
    (poi && poi.length > 0) ||
    remarks?.directions ||
    (mediaImages && mediaImages.length > 0)
  );
};

// ---------- Component ----------

const ProcessingPage = () => {
  const { listingId } = useParams<{ listingId: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const [status, setStatus] = useState("Extracting data from documents...");
  const enrichmentStartedRef = useRef(false);

  // Store listing ID globally (same as before)
  useEffect(() => {
    if (!listingId) {
      navigate("/", { replace: true });
      return;
    }
    dispatch(setCurrentListing(listingId));
  }, [listingId, navigate, dispatch]);

  // 🔁 React Query: Poll canonical
  const { data: canonical } = useQuery({
    queryKey: ["canonical", listingId],
    queryFn: () => apiClient.get(`/listings/${listingId}/canonical`),
    enabled: !!listingId,
    refetchInterval: 3000,
    retry: true,
  });

  // 🧠 React to canonical changes
  useEffect(() => {
    if (!canonical || !listingId) return;

    // Step 1: Wait for extraction
    if (!isExtractionComplete(canonical)) {
      setStatus("Extracting data from documents...");
      return;
    }

    // Step 2: Trigger enrichment ONCE
    if (!enrichmentStartedRef.current) {
      enrichmentStartedRef.current = true;
      setStatus("Enriching listing data...");

      apiClient
        .post(
          `/enrichment/listings/${listingId}/enrich?analyze_images=true&generate_descriptions=true&enrich_geo=true`,
        )
        .catch((error) => {
          console.error("Enrichment error:", error);
        });

      return;
    }

    // Step 3: Wait for enrichment
    if (!isEnrichmentComplete(canonical)) {
      setStatus("Waiting for enrichment to complete...");
      return;
    }

    // Step 4: Done → navigate
    setStatus("Processing complete!");
    setTimeout(() => {
      navigate(`/listings/${listingId}/review`, { replace: true });
    }, 500);
  }, [canonical, listingId, navigate]);

  return (
  <div
    className="
      flex flex-col items-center justify-center
      w-full h-screen
      bg-(--bg-color)
      animate-[fadeIn_0.5s_ease-out]
    "
  >
    <div className="flex flex-col items-center gap-8">
      <div className="relative w-[80px] h-[80px]">
        {/* Outer ring */}
        <div
          className="
            absolute inset-0
            rounded-full
            border-[3px] border-[rgba(37,99,235,0.2)]
            box-border
            after:content-['']
            after:absolute
            after:top-[-2px]
            after:left-[-2px]
            after:w-[80px]
            after:h-[80px]
            after:rounded-full
            after:border-[2px]
            after:border-transparent
            after:border-t-(--accent-blue)
            after:box-border
            after:animate-[spin_1s_linear_infinite]
          "
        />

        {/* Inner circle */}
        <div
          className="
            absolute top-1/2 left-1/2
            -translate-x-1/2 -translate-y-1/2
            w-[25px] h-[25px]
            bg-(--accent-blue)
            rounded-full
          "
        />
      </div>

      <p className="text-[1.1rem] font-medium text-(--text-primary)">
        {status}
      </p>

      <p className="text-[0.85rem] text-(--text-secondary) mt-[-1rem]">
        This may take a few moments
      </p>
    </div>
  </div>
);

};

export default ProcessingPage;

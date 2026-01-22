import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { listingsApi } from '../services/api';
import { useAppDispatch } from '../store/hooks';
import { setCurrentListing, setLoading, setError } from '../store/slices/listingsSlice';
import { addToast } from '../store/slices/uiSlice';

export default function CreateListingPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const [userId] = useState('00000000-0000-0000-0000-000000000001');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateListing = useCallback(async () => {
    if (isCreating) {
      console.log('Already creating, skipping...');
      return;
    }

    console.log('=== Starting create listing process ===');
    setIsCreating(true);
    dispatch(setLoading(true));
    dispatch(setError(null));

    try {
      console.log('Step 1: Creating listing for user:', userId);
      console.log('API Base URL:', import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api');
      console.log('Full API URL will be:', `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/listings?user_id=${userId}`);
      
      let result;
      try {
        result = await listingsApi.create(userId);
      } catch (apiError) {
        console.error('API call failed:', apiError);
        console.error('API error details:', {
          message: apiError instanceof Error ? apiError.message : String(apiError),
          stack: apiError instanceof Error ? apiError.stack : undefined,
        });
        throw apiError;
      }
      console.log('Step 2: API call completed. Result:', result);
      console.log('Step 2: Result type:', typeof result);
      console.log('Step 2: Result keys:', result ? Object.keys(result) : 'null');

      // Handle different possible response formats
      const listingId = result?.listing_id || 
        (result && typeof result === 'object' && 'data' in result && (result.data as { listing_id?: string })?.listing_id) ||
        (result && typeof result === 'object' && 'id' in result && (result as { id?: string })?.id);

      console.log('Step 3: Extracted listing ID:', listingId);

      if (!listingId) {
        console.error('Step 3 ERROR: No listing ID found in response');
        console.error('Full response:', JSON.stringify(result, null, 2));
        throw new Error('No listing ID returned from server');
      }

      console.log('Step 4: Updating Redux store with listing ID:', listingId);
      // Update Redux store
      dispatch(setCurrentListing(listingId));
      dispatch(setLoading(false));

      console.log('Step 5: Showing success toast');
      // Show success toast
      dispatch(addToast({
        message: 'Listing created successfully',
        type: 'success',
      }));

      console.log('Step 6: Preparing to navigate to /upload/' + listingId);
      // Use setTimeout to ensure state updates are processed
      setTimeout(() => {
        console.log('Step 7: Executing navigation');
        try {
          navigate(`/upload/${listingId}`, { replace: true });
          console.log('Step 8: Navigation called successfully');
        } catch (navError) {
          console.error('Navigation error:', navError);
          // Fallback: try window.location
          window.location.href = `/upload/${listingId}`;
        }
      }, 100);
    } catch (error) {
      console.error('=== ERROR in create listing ===');
      console.error('Error object:', error);
      console.error('Error type:', typeof error);
      console.error('Error message:', error instanceof Error ? error.message : String(error));
      console.error('Error stack:', error instanceof Error ? error.stack : 'No stack trace');
      
      const errorMessage = error instanceof Error ? error.message : 'Failed to create listing. Please try again.';
      
      dispatch(setError(errorMessage));
      dispatch(setLoading(false));
      dispatch(addToast({
        message: errorMessage,
        type: 'error',
      }));
      
      setIsCreating(false);
    }
  }, [userId, navigate, dispatch, isCreating]);

  return (
  <div
    className="min-h-screen w-full flex items-center justify-center text-white"
    style={{ backgroundColor: '#0F1115' }}
  >
    <div className="flex flex-col items-center w-full max-w-xl px-6 text-center">

      {/* Heading */}
      <h1 className="text-5xl font-semibold tracking-tight mb-4">
        MLS Automation
      </h1>

      {/* Subheading */}
      <p className="text-base text-white/60 max-w-md leading-relaxed mb-6">
        Create a new listing to get started with AI-powered document
        extraction and MLS automation.
      </p>

      {/* CTA */}
      <button
        onClick={handleCreateListing}
        disabled={isCreating}
        className={`
          group
          relative
          inline-flex items-center justify-center gap-3
          px-5 py-2
          rounded-full
          font-medium text-base
          text-white
          bg-blue-600
          transition-all duration-200 ease-out
          hover:bg-blue-500
          hover:shadow-[0_0_40px_rgba(59,130,246,0.35)]
          active:scale-[0.96]
          focus-visible:outline-none
          focus-visible:ring-2
          focus-visible:ring-blue-500
          focus-visible:ring-offset-2
          focus-visible:ring-offset-[#0F1115]
          disabled:opacity-50
          disabled:cursor-not-allowed
          ${isCreating ? 'cursor-wait' : 'cursor-pointer'}
        `}
      >
        {isCreating ? (
          <>
            <div className="w-5 h-5 rounded-full border-2 border-white/40 border-t-white animate-spin" />
            <span className="tracking-tight">Creating…</span>
          </>
        ) : (
          <>
            <Plus className="w-5 h-5 text-white transition-transform duration-200 group-hover:rotate-90" />
            <span className="tracking-tight">Create New Listing</span>
          </>
        )}
      </button>
    </div>
  </div>
);



}

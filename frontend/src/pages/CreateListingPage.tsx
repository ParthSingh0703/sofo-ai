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
    <div className="min-h-screen w-full flex items-center justify-center text-white" style={{ backgroundColor: '#0F1115' }}>
      <div className="flex flex-col items-center gap-8 w-full max-w-lg px-4">
        <div className="flex flex-col items-center gap-4">
          <h1 className="text-3xl font-semibold text-white text-center">MLS Automation</h1>
          <p className="text-white text-center max-w-md">
            Create a new listing to get started with AI-powered document extraction and MLS automation.
          </p>
        </div>

        <button
          onClick={handleCreateListing}
          disabled={isCreating}
          className={`
            flex items-center justify-center gap-3 px-8 py-4 rounded-lg font-medium text-base transition-all
            text-black border-2
            bg-blue-600 hover:bg-blue-700 border-blue-500 hover:border-blue-600
            disabled:opacity-50 disabled:cursor-not-allowed
            shadow-lg hover:shadow-xl
            min-w-[200px]
            ${isCreating ? 'cursor-wait' : 'cursor-pointer'}
          `}
        >
          {isCreating ? (
            <>
              <div className="w-5 h-5 border-2 border-black border-t-transparent rounded-full animate-spin" />
              <span className="text-black">Creating...</span>
            </>
          ) : (
            <>
              <Plus className="w-5 h-5 text-black" />
              <span className="text-black">Create New Listing</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

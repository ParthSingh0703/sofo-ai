import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

interface ListingsState {
  currentListingId: string | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: ListingsState = {
  currentListingId: null,
  isLoading: false,
  error: null,
};

const listingsSlice = createSlice({
  name: 'listings',
  initialState,
  reducers: {
    setCurrentListing: (state, action: PayloadAction<string>) => {
      state.currentListingId = action.payload;
      state.error = null;
    },
    clearCurrentListing: (state) => {
      state.currentListingId = null;
      state.error = null;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const { setCurrentListing, clearCurrentListing, setLoading, setError } = listingsSlice.actions;
export default listingsSlice.reducer;

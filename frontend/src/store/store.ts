import { configureStore } from '@reduxjs/toolkit';
import listingsReducer from './slices/listingsSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    listings: listingsReducer,
    ui: uiReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

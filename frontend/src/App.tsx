import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { store } from './store/store';
import CreateListingPage from './pages/CreateListingPage';
import UploadPage from './pages/UploadPage/UploadPage';
import ProcessingPage from './components/ProcessingPage/ProcessingPage';
import ReviewPage from './components/ReviewPage/ReviewPage';
import MediaPage from './components/MediaPage/MediaPage';
import MLSAutomationPage from './pages/MLSAutomationPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<CreateListingPage />} />
            <Route path="/upload/:listingId" element={<UploadPage />} />
            <Route path="/processing/:listingId" element={<ProcessingPage />} />
            <Route path="/listings/:listingId/review" element={<ReviewPage />} />
            <Route path="/listings/:listingId/media" element={<MediaPage />} />
            <Route path="/mls/:listingId" element={<MLSAutomationPage />} />
            {/* Legacy routes for backward compatibility */}
            <Route path="/review/:listingId" element={<ReviewPage />} />
            <Route path="/media/:listingId" element={<MediaPage />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </Provider>
  );
}

export default App;

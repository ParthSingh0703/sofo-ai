import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { listingsApi, apiClient } from '../services/api';
import { useAppDispatch } from '../store/hooks';
import { addToast } from '../store/slices/uiSlice';
import { formatRoomType } from '../utils/roomTypeFormatter';
import { Trash2, Upload, Loader2 } from 'lucide-react';
import '../styles/reviewPage.css';

interface ImageData {
  image_id: string;
  ai_suggested_description?: string;
  description?: string;
  ai_suggested_room_type?: string;
  room_type?: string;
  label?: string;
  ai_suggested_label?: string;
  storage_path?: string;
  image_url?: string;
}

export default function MediaPage() {
  const { listingId } = useParams<{ listingId: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  
  const [canonical, setCanonical] = useState<any>(null);
  const [images, setImages] = useState<ImageData[]>([]);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [deletingImageId, setDeletingImageId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!listingId) return;
    
    const loadData = async () => {
      try {
        setLoading(true);
        
        // Load canonical
        const data = await listingsApi.getCanonical(listingId);
        setCanonical(data);
        
        // Get API base URL for image URLs
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
        
        // Try to load images from API endpoint first
        let imagesWithUrls: ImageData[] = [];
        
        try {
          const imagesResponse = await apiClient.get<{ images: any[] }>(`/images/listings/${listingId}`);
          
          if (imagesResponse && imagesResponse.images && Array.isArray(imagesResponse.images)) {
            imagesWithUrls = imagesResponse.images.map((img: any) => ({
              image_id: img.image_id,
              ai_suggested_description: img.ai_description,
              description: img.ai_description, // Use AI description as default
              ai_suggested_room_type: img.detected_features?.room_label,
              room_type: img.detected_features?.room_label ? formatRoomType(img.detected_features.room_label) : undefined, // Convert to Title Case
              label: img.final_label || img.ai_suggested_label,
              ai_suggested_label: img.ai_suggested_label,
              storage_path: img.storage_path,
              image_url: `${apiBaseUrl}/images/${listingId}/${img.image_id}`, // Full URL with API base
            }));
          }
        } catch (apiError) {
          console.warn('Failed to load images from API endpoint, trying canonical:', apiError);
          
          // Fallback: Load images from canonical data
          const media = (data as any)?.media;
          const mediaImages = media?.media_images;
          
          if (mediaImages && Array.isArray(mediaImages) && mediaImages.length > 0) {
            imagesWithUrls = mediaImages.map((img: any) => ({
              image_id: String(img.image_id || ''),
              ai_suggested_description: img.ai_suggested_description ? String(img.ai_suggested_description) : undefined,
              description: img.description ? String(img.description) : (img.ai_suggested_description ? String(img.ai_suggested_description) : undefined),
              ai_suggested_room_type: img.ai_suggested_room_type ? String(img.ai_suggested_room_type) : undefined,
              room_type: img.room_type ? String(img.room_type) : (img.ai_suggested_room_type ? formatRoomType(String(img.ai_suggested_room_type)) : undefined),
              label: img.label || img.ai_suggested_label,
              ai_suggested_label: img.ai_suggested_label,
              image_url: `${apiBaseUrl}/images/${listingId}/${img.image_id}`, // Full URL with API base
            }));
          }
        }
        
        console.log('Loaded images:', imagesWithUrls);
        setImages(imagesWithUrls);
        
        if (imagesWithUrls.length === 0) {
          console.warn('No images found for listing:', listingId);
        }
      } catch (error) {
        console.error('Failed to load data:', error);
        dispatch(addToast({
          message: error instanceof Error ? error.message : 'Failed to load listing data',
          type: 'error',
        }));
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [listingId, dispatch]);

  const updateImage = (imageId: string, field: 'description' | 'room_type', value: string) => {
    setImages(prev => prev.map(img => 
      img.image_id === imageId ? { ...img, [field]: value } : img
    ));
  };

  const nextImage = () => {
    if (images.length > 0) {
      setCurrentImageIndex((prev) => (prev + 1) % images.length);
    }
  };

  const prevImage = () => {
    if (images.length > 0) {
      setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length);
    }
  };

  const handleSave = async () => {
    if (!listingId || !canonical) return;
    
    try {
      setSaving(true);
      
      // Update canonical with edited image descriptions and room types
      const updated = JSON.parse(JSON.stringify(canonical));
      
      images.forEach(imageData => {
        const img = updated.media.media_images.find((img: any) => img.image_id === imageData.image_id);
        if (img) {
          if (imageData.description !== undefined) {
            img.description = imageData.description;
          }
          if (imageData.room_type !== undefined) {
            // Convert to Title Case before saving
            img.room_type = formatRoomType(imageData.room_type);
          }
        }
      });
      
      await listingsApi.updateCanonical(listingId, updated);
      
      dispatch(addToast({
        message: 'Image information updated successfully',
        type: 'success',
      }));
    } catch (error) {
      console.error('Failed to update canonical:', error);
      dispatch(addToast({
        message: error instanceof Error ? error.message : 'Failed to update listing',
        type: 'error',
      }));
    } finally {
      setSaving(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!listingId || !e.target.files || e.target.files.length === 0) return;
    
    const files = Array.from(e.target.files);
    const imageFiles = files.filter(file => {
      const ext = file.name.split('.').pop()?.toLowerCase();
      return ext && ['jpg', 'jpeg', 'png'].includes(ext);
    });
    
    if (imageFiles.length === 0) {
      dispatch(addToast({
        message: 'Please select image files (JPG, JPEG, PNG)',
        type: 'error',
      }));
      return;
    }
    
    try {
      setUploading(true);
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
      
      // Upload all images
      const uploadPromises = imageFiles.map(async (file) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${apiBaseUrl}/images/listings/${listingId}`, {
          method: 'POST',
          body: formData,
        });
        
        if (!response.ok) {
          throw new Error(`Failed to upload ${file.name}`);
        }
        
        const data = await response.json();
        return { imageId: data.image_id, fileName: file.name };
      });
      
      const uploadedImages = await Promise.all(uploadPromises);
      
      dispatch(addToast({
        message: `Successfully uploaded ${uploadedImages.length} image(s). Enriching in background...`,
        type: 'success',
      }));
      
      // Trigger background enrichment for new images
      // This enriches images in the background and updates the database with:
      // - Room type (room_label in detected_features)
      // - Image description (description in image_ai_analysis)
      // - Labels and sequencing
      setEnriching(true);
      try {
        await apiClient.post(`/enrichment/listings/${listingId}/enrich?analyze_images=true&generate_descriptions=false&enrich_geo=false`);
        
        // After enrichment completes, reload canonical and images to get the enriched data
        // The enrichment service updates:
        // 1. image_ai_analysis table with description and detected_features (including room_label)
        // 2. listing_images table with ai_suggested_label, final_label, display_order, is_primary
        // 3. Canonical JSON is synced when we call getCanonical (it pulls from database)
        const updatedCanonical = await listingsApi.getCanonical(listingId);
        setCanonical(updatedCanonical);
        
        // Reload images from API to get enriched data (room type, description, labels)
        await loadImages();
        
        dispatch(addToast({
          message: 'Images enriched successfully. Room types and descriptions are now available for editing.',
          type: 'success',
        }));
      } catch (enrichError) {
        console.error('Enrichment error:', enrichError);
        dispatch(addToast({
          message: 'Images uploaded but enrichment failed. You can manually trigger enrichment later.',
          type: 'warning',
        }));
        // Still reload images even if enrichment failed (they'll just be without enriched data)
        await loadImages();
      } finally {
        setEnriching(false);
      }
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('Upload error:', error);
      dispatch(addToast({
        message: error instanceof Error ? error.message : 'Failed to upload images',
        type: 'error',
      }));
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (!listingId || !window.confirm('Are you sure you want to delete this image? This will remove it from the database and storage.')) {
      return;
    }
    
    try {
      setDeletingImageId(imageId);
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
      
      const response = await fetch(`${apiBaseUrl}/images/listings/${listingId}/${imageId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete image');
      }
      
      // Remove from local state
      setImages(prev => {
        const filtered = prev.filter(img => img.image_id !== imageId);
        // Adjust current index if needed
        if (currentImageIndex >= filtered.length && filtered.length > 0) {
          setCurrentImageIndex(filtered.length - 1);
        } else if (filtered.length === 0) {
          setCurrentImageIndex(0);
        }
        return filtered;
      });
      
      // Update canonical to remove image
      if (canonical) {
        const updated = JSON.parse(JSON.stringify(canonical));
        if (updated.media?.media_images) {
          updated.media.media_images = updated.media.media_images.filter((img: any) => img.image_id !== imageId);
        }
        await listingsApi.updateCanonical(listingId, updated);
      }
      
      dispatch(addToast({
        message: 'Image deleted successfully',
        type: 'success',
      }));
    } catch (error) {
      console.error('Delete error:', error);
      dispatch(addToast({
        message: error instanceof Error ? error.message : 'Failed to delete image',
        type: 'error',
      }));
    } finally {
      setDeletingImageId(null);
    }
  };

  const loadImages = async () => {
    if (!listingId) return;
    
    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
      
      const imagesResponse = await apiClient.get<{ images: any[] }>(`/images/listings/${listingId}`);
      
      if (imagesResponse && imagesResponse.images && Array.isArray(imagesResponse.images)) {
        const imagesWithUrls = imagesResponse.images.map((img: any) => ({
          image_id: img.image_id,
          ai_suggested_description: img.ai_description,
          description: img.ai_description,
          ai_suggested_room_type: img.detected_features?.room_label,
          room_type: img.detected_features?.room_label ? formatRoomType(img.detected_features.room_label) : undefined,
          label: img.final_label || img.ai_suggested_label,
          ai_suggested_label: img.ai_suggested_label,
          storage_path: img.storage_path,
          image_url: `${apiBaseUrl}/images/${listingId}/${img.image_id}`,
        }));
        
        setImages(imagesWithUrls);
      }
    } catch (error) {
      console.error('Failed to reload images:', error);
    }
  };

  const handleFinalizeAssets = async () => {
    if (!listingId) {
      console.log('Cannot proceed: missing listingId');
      return;
    }
    
    try {
      setValidating(true);
      
      // First save any pending changes
      await handleSave();
      
      // Resequence images before finalizing
      try {
        await apiClient.post(`/images/listings/${listingId}/resequence`);
        dispatch(addToast({
          message: 'Images resequenced successfully',
          type: 'success',
        }));
      } catch (resequenceError) {
        console.error('Resequencing error:', resequenceError);
        dispatch(addToast({
          message: 'Warning: Failed to resequence images. Proceeding anyway.',
          type: 'warning',
        }));
      }
      
      // Reload images to get updated sequence
      await loadImages();
      
      // Validate and lock the canonical
      const userId = '00000000-0000-0000-0000-000000000001';
      const result = await listingsApi.validateCanonical(listingId, userId);
      
      dispatch(addToast({
        message: 'Assets finalized and listing locked. Ready for automation.',
        type: 'success',
      }));
      
      // Navigate to MLS automation page
      navigate(`/mls/${listingId}`, { replace: true });
    } catch (error) {
      console.error('Failed to finalize assets:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to finalize assets';
      dispatch(addToast({
        message: errorMessage,
        type: 'error',
      }));
    } finally {
      setValidating(false);
    }
  };

  const handleProceedToAutomation = async () => {
    if (!listingId) {
      console.log('Cannot proceed: missing listingId');
      return;
    }
    
    try {
      setValidating(true);
      console.log('Validating canonical for listing:', listingId);
      
      // First save any pending changes
      console.log('Saving pending image changes...');
      await handleSave();
      
      // Validate and lock the canonical
      const userId = '00000000-0000-0000-0000-000000000001'; // Default user ID
      console.log('Calling validate endpoint...');
      const result = await listingsApi.validateCanonical(listingId, userId);
      console.log('Validation successful:', result);
      
      dispatch(addToast({
        message: 'Listing locked. Ready for automation.',
        type: 'success',
      }));
      
      // Navigate to MLS automation page (or wherever you want)
      console.log('Navigating to MLS page:', `/mls/${listingId}`);
      navigate(`/mls/${listingId}`, { replace: true });
    } catch (error) {
      console.error('Failed to validate canonical:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to validate listing';
      dispatch(addToast({
        message: errorMessage,
        type: 'error',
      }));
    } finally {
      setValidating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center" style={{ backgroundColor: '#0F1115', color: 'white' }}>
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p>Loading images...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full" style={{ backgroundColor: '#0F1115', color: 'white', padding: '40px 20px' }}>
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-semibold">Review & Edit Property Images</h1>
          <div className="flex gap-4">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept="image/jpeg,image/jpg,image/png"
              multiple
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || enriching}
              className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {uploading || enriching ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {uploading ? 'Uploading...' : 'Enriching...'}
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Add Media
                </>
              )}
            </button>
          </div>
        </div>
        
        {images.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-zinc-400 mb-4">No images found for this listing.</p>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || enriching}
              className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 mx-auto"
            >
              {uploading || enriching ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {uploading ? 'Uploading...' : 'Enriching...'}
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Add Media
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="mb-8">
            {/* Image Carousel */}
            <div className="image-carousel-container" style={{ height: '500px', marginBottom: '24px', position: 'relative' }}>
              {images[currentImageIndex] && (
                <>
                  <button
                    onClick={() => handleDeleteImage(images[currentImageIndex].image_id)}
                    disabled={deletingImageId === images[currentImageIndex].image_id}
                    className="absolute top-4 right-4 z-10 p-2 rounded bg-red-600 hover:bg-red-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ zIndex: 10 }}
                    title="Delete image"
                  >
                    {deletingImageId === images[currentImageIndex].image_id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                  <img
                    src={images[currentImageIndex].image_url}
                    alt={images[currentImageIndex].room_type || images[currentImageIndex].ai_suggested_room_type || 'Property image'}
                    className="image-carousel-image"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      console.error('Failed to load image:', images[currentImageIndex].image_url);
                      target.style.display = 'none';
                      // Show error message
                      const container = target.parentElement;
                      if (container) {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'flex items-center justify-center h-full text-zinc-400';
                        errorDiv.textContent = `Failed to load image: ${images[currentImageIndex].label || images[currentImageIndex].image_id}`;
                        container.appendChild(errorDiv);
                      }
                    }}
                    onLoad={() => {
                      console.log('Image loaded successfully:', images[currentImageIndex].image_url);
                    }}
                  />
                  <div className="carousel-counter">
                    {currentImageIndex + 1} / {images.length}
                  </div>
                  {images.length > 1 && (
                    <>
                      <button
                        onClick={prevImage}
                        className="carousel-arrow carousel-arrow-left"
                        aria-label="Previous image"
                      >
                        ‹
                      </button>
                      <button
                        onClick={nextImage}
                        className="carousel-arrow carousel-arrow-right"
                        aria-label="Next image"
                      >
                        ›
                      </button>
                    </>
                  )}
                </>
              )}
            </div>

            {/* Editable Fields for Current Image */}
            {images[currentImageIndex] && (
              <div className="bg-zinc-800/30 border border-zinc-700 rounded-lg p-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                      Room Type
                    </label>
                    <input
                      type="text"
                      value={images[currentImageIndex].room_type || (images[currentImageIndex].ai_suggested_room_type ? formatRoomType(images[currentImageIndex].ai_suggested_room_type) : '')}
                      onChange={(e) => updateImage(images[currentImageIndex].image_id, 'room_type', e.target.value)}
                      placeholder={images[currentImageIndex].ai_suggested_room_type ? formatRoomType(images[currentImageIndex].ai_suggested_room_type) : 'Enter room type'}
                      className="w-full px-3 py-2 rounded bg-zinc-800/50 border border-zinc-700 text-white"
                      style={{ 
                        color: 'white',
                        backgroundColor: 'rgba(33, 104, 218, 0.49)',
                        border: 'none'
                      }}
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2" style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                      Image Description
                    </label>
                    <textarea
                      value={images[currentImageIndex].description || images[currentImageIndex].ai_suggested_description || ''}
                      onChange={(e) => updateImage(images[currentImageIndex].image_id, 'description', e.target.value)}
                      placeholder={images[currentImageIndex].ai_suggested_description || 'Enter image description'}
                      rows={4}
                      className="w-full px-3 py-2 rounded bg-zinc-800/50 border border-zinc-700 text-white resize-none"
                      style={{ 
                        color: 'white',
                        backgroundColor: 'rgba(33, 104, 218, 0.49)',
                        border: 'none'
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        
        <div className="mt-8 flex justify-between">
          <button
            onClick={handleSave}
            disabled={saving || uploading || enriching}
            className="px-6 py-3 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          
          <button
            onClick={handleFinalizeAssets}
            disabled={validating || saving || uploading || enriching}
            className="px-6 py-3 rounded bg-green-600 hover:bg-green-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {validating ? 'Finalizing...' : 'Finalize Assets'}
          </button>
        </div>
      </div>
    </div>
  );
}

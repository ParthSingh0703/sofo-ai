import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, ChevronRight } from 'lucide-react';
import { listingsApi, apiClient } from '../../services/api';
import { useAppDispatch } from '../../store/hooks';
import { addToast } from '../../store/slices/uiSlice';
import { formatRoomType } from '../../utils/roomTypeFormatter';
import { sortImagesByPrecedence } from '../../utils/imageSorting';
import MediaCard from './MediaCard';
import Lightbox from './Lightbox';
import styles from './MediaPage.module.css';

interface MediaPageProps {
    onBack?: () => void;
    onFinalize?: () => void;
}

const MediaPage = ({ onBack, onFinalize }: MediaPageProps) => {
    const { listingId } = useParams<{ listingId: string }>();
    const navigate = useNavigate();
    const dispatch = useAppDispatch();
    
    const [images, setImages] = useState<Array<{ id: string; src: string; room: string; description: string; isMain: boolean; isProcessing?: boolean; detected_features?: { room_label?: string } }>>([]);
    const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
    const [uploading, setUploading] = useState(false);
    const [enriching, setEnriching] = useState(false);
    const [finalizing, setFinalizing] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (!listingId) return;
        loadImages();
    }, [listingId]);

    const loadImages = async () => {
        if (!listingId) return;
        
        try {
            const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
            let formattedImages: Array<{ id: string; src: string; room: string; description: string; isMain: boolean; isProcessing?: boolean; detected_features?: { room_label?: string } }> = [];
            
            // Try to load images from API endpoint first
            try {
                const imagesResponse = await apiClient.get<{ images: any[] }>(`/images/listings/${listingId}`);
                
                if (imagesResponse && imagesResponse.images && Array.isArray(imagesResponse.images)) {
                    // Sort images by room label precedence (exterior first)
                    const sortedImages = sortImagesByPrecedence(imagesResponse.images);
                    
                    formattedImages = sortedImages.map((img: any) => ({
                        id: img.image_id,
                        src: `${apiBaseUrl}/images/${listingId}/${img.image_id}`,
                        room: img.detected_features?.room_label ? formatRoomType(img.detected_features.room_label) : 'Other',
                        description: img.ai_description || '',
                        isMain: img.is_primary || false,
                        isProcessing: false, // Images from API are already processed
                        // Keep original data for sorting
                        detected_features: img.detected_features,
                    }));
                }
            } catch (apiError) {
                console.warn('Failed to load images from API endpoint, trying canonical:', apiError);
                
                // Fallback: Load images from canonical data
                const canonical = await listingsApi.getCanonical(listingId);
                const media = (canonical as any)?.media;
                const mediaImages = media?.media_images;
                
                if (mediaImages && Array.isArray(mediaImages) && mediaImages.length > 0) {
                    const imagesFromCanonical = mediaImages.map((img: any) => ({
                        id: String(img.image_id || ''),
                        src: `${apiBaseUrl}/images/${listingId}/${img.image_id}`,
                        room: img.room_type ? String(img.room_type) : (img.ai_suggested_room_type ? formatRoomType(String(img.ai_suggested_room_type)) : 'Other'),
                        description: img.description ? String(img.description) : (img.ai_suggested_description ? String(img.ai_suggested_description) : ''),
                        isMain: img.is_primary || false,
                        isProcessing: false,
                        detected_features: img.ai_suggested_room_type ? { room_label: img.ai_suggested_room_type } : undefined,
                    }));
                    
                    // Sort images from canonical by precedence
                    formattedImages = sortImagesByPrecedence(imagesFromCanonical);
                }
            }
            
            if (formattedImages.length > 0) {
                setImages(formattedImages);
            } else {
                console.warn('No images found for listing:', listingId);
            }
        } catch (error) {
            console.error('Failed to load images:', error);
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
            
            // Upload all images and immediately add them to state with processing indicator
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
            
            // Immediately add newly uploaded images to state with processing indicator
            const newImages = uploadedImages.map(({ imageId }) => ({
                id: imageId,
                src: `${apiBaseUrl}/images/${listingId}/${imageId}`,
                room: '',
                description: '',
                isMain: false,
                isProcessing: true,
                detected_features: {}
            }));
            
            // Add new images to existing images and sort
            setImages(prevImages => {
                const combined = [...prevImages, ...newImages];
                return sortImagesByPrecedence(combined);
            });
            
            dispatch(addToast({
                message: `Successfully uploaded ${imageFiles.length} image(s). Enriching in background...`,
                type: 'success',
            }));
            
            // Trigger background enrichment
            setEnriching(true);
            try {
                await apiClient.post(`/enrichment/listings/${listingId}/enrich?analyze_images=true&generate_descriptions=false&enrich_geo=false`);
                
                // Reload images to get enriched data
                await loadImages();
                
                dispatch(addToast({
                    message: 'Images enriched successfully',
                    type: 'success',
                }));
            } catch (enrichError) {
                console.error('Enrichment error:', enrichError);
                dispatch(addToast({
                    message: 'Images uploaded but enrichment failed',
                    type: 'warning',
                }));
                // Still reload to show uploaded images even if enrichment failed
                await loadImages();
            } finally {
                setEnriching(false);
            }
            
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

    const handleEditImage = async (index: number, newData: { room: string; description: string }) => {
        if (!listingId) return;
        
        const image = images[index];
        if (!image) return;
        
        try {
            // Update canonical with new room type and description
            const canonical = await listingsApi.getCanonical(listingId);
            const updated = JSON.parse(JSON.stringify(canonical));
            
            if (updated.media?.media_images) {
                const img = updated.media.media_images.find((img: any) => img.image_id === image.id);
                if (img) {
                    img.room_type = newData.room;
                    img.description = newData.description;
                }
            }
            
            await listingsApi.updateCanonical(listingId, updated);
            
            // Update local state
            setImages(prev => {
                const newImages = [...prev];
                newImages[index] = { ...newImages[index], ...newData };
                return newImages;
            });
            
            dispatch(addToast({
                message: 'Image updated successfully',
                type: 'success',
            }));
        } catch (error) {
            console.error('Failed to update image:', error);
            dispatch(addToast({
                message: 'Failed to update image',
                type: 'error',
            }));
        }
    };

    const handleDeleteImage = async (index: number) => {
        if (!listingId) return;
        
        const image = images[index];
        if (!image || !window.confirm('Are you sure you want to delete this image?')) return;
        
        try {
            const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
            
            const response = await fetch(`${apiBaseUrl}/images/listings/${listingId}/${image.id}`, {
                method: 'DELETE',
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete image');
            }
            
            // Remove from local state
            setImages(prev => prev.filter((_, i) => i !== index));
            
            // Update canonical
            const canonical = await listingsApi.getCanonical(listingId);
            const updated = JSON.parse(JSON.stringify(canonical));
            if (updated.media?.media_images) {
                updated.media.media_images = updated.media.media_images.filter((img: any) => img.image_id !== image.id);
            }
            await listingsApi.updateCanonical(listingId, updated);
            
            dispatch(addToast({
                message: 'Image deleted successfully',
                type: 'success',
            }));
        } catch (error) {
            console.error('Delete error:', error);
            dispatch(addToast({
                message: 'Failed to delete image',
                type: 'error',
            }));
        }
    };

    const handleFinalize = async () => {
        if (!listingId) return;
        
        try {
            setFinalizing(true);
            
            // Resequence images
            try {
                await apiClient.post(`/images/listings/${listingId}/resequence`);
            } catch (resequenceError) {
                console.error('Resequencing error:', resequenceError);
            }
            
            // Reload images
            await loadImages();
            
            // Validate and lock canonical (only when Finalize Assets is called)
            const userId = '00000000-0000-0000-0000-000000000001';
            await listingsApi.validateCanonical(listingId, userId);
            
            dispatch(addToast({
                message: 'Assets finalized and listing locked',
                type: 'success',
            }));
            
            if (onFinalize) {
                onFinalize();
            } else {
                navigate(`/mls/${listingId}`);
            }
        } catch (error) {
            console.error('Failed to finalize assets:', error);
            dispatch(addToast({
                message: 'Failed to finalize assets',
                type: 'error',
            }));
        } finally {
            setFinalizing(false);
        }
    };

    const handleBack = () => {
        if (onBack) {
            onBack();
        } else if (listingId) {
            navigate(`/listings/${listingId}/review`);
        }
    };

    const openLightbox = (index: number) => setLightboxIndex(index);
    const closeLightbox = () => setLightboxIndex(null);
    
    const nextImage = () => {
        setLightboxIndex((prev) => prev !== null ? (prev + 1) % images.length : null);
    };
    
    const prevImage = () => {
        setLightboxIndex((prev) => prev !== null ? (prev - 1 + images.length) % images.length : null);
    };

    const isLightboxOpen = lightboxIndex !== null;

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.headerLeft}>
                    <button className={styles.backButton} onClick={handleBack}>
                        <ArrowLeft size={18} />
                    </button>
                    <div className={styles.titleGroup}>
                        <span className={styles.title}>Photos & media</span>
                        <span className={styles.subtitle}>TOTAL ASSETS: {images.length}</span>
                    </div>
                </div>
                <div className={styles.headerRight}>
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileSelect}
                        accept="image/jpeg,image/jpg,image/png"
                        multiple
                        className={styles.hiddenInput}
                    />
                    <button
                        className={styles.addButton}
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading || enriching}
                    >
                        <Plus size={16} /> ADD MEDIA
                    </button>
                    <button
                        className={styles.finalizeButton}
                        onClick={handleFinalize}
                        disabled={finalizing || uploading || enriching}
                    >
                        FINALIZE ASSETS <ChevronRight size={16} />
                    </button>
                </div>
            </div>

            <div className={styles.content}>
                <div className={styles.grid}>
                    {images.map((img, index) => (
                        <MediaCard
                            key={img.id}
                            image={img}
                            index={index}
                            onMagnify={openLightbox}
                            onEdit={handleEditImage}
                            onDelete={handleDeleteImage}
                        />
                    ))}
                </div>
            </div>

            {isLightboxOpen && lightboxIndex !== null && (
                <Lightbox
                    images={images}
                    currentIndex={lightboxIndex}
                    onClose={closeLightbox}
                    onNext={nextImage}
                    onPrev={prevImage}
                />
            )}
        </div>
    );
};

export default MediaPage;

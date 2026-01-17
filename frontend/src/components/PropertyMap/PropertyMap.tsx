import { useEffect, useRef } from 'react';
import styles from './PropertyMap.module.css';

interface PropertyMapProps {
  latitude: number | null;
  longitude: number | null;
  address?: string;
  onLatitudeChange?: (value: number | null) => void;
  onLongitudeChange?: (value: number | null) => void;
}

interface GoogleMaps {
  maps: {
    Map: new (element: HTMLElement, options: Record<string, unknown>) => {
      setCenter: (location: { lat: number; lng: number }) => void;
      setZoom: (zoom: number) => void;
    };
    Marker: new (options: Record<string, unknown>) => {
      setMap: (map: unknown) => void;
      setPosition: (location: { lat: number; lng: number }) => void;
    };
  };
}

declare global {
  interface Window {
    google?: GoogleMaps;
    initMap?: () => void;
  }
}

const PropertyMap = ({ latitude, longitude, onLatitudeChange, onLongitudeChange }: PropertyMapProps) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<{ setCenter: (location: { lat: number; lng: number }) => void; setZoom: (zoom: number) => void } | null>(null);
  const markerRef = useRef<{ setMap: (map: unknown) => void; setPosition: (location: { lat: number; lng: number }) => void } | null>(null);
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

  useEffect(() => {
    if (!latitude || !longitude || !mapRef.current) return;

    // Load Google Maps script if not already loaded
    if (!window.google) {
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey || ''}&callback=initMap`;
      script.async = true;
      script.defer = true;
      
      window.initMap = () => {
        if (mapRef.current && latitude && longitude && window.google) {
          const map = new window.google.maps.Map(mapRef.current, {
            center: { lat: latitude, lng: longitude },
            zoom: 15,
            disableDefaultUI: false,
            zoomControl: true,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
          });

          // Add marker
          if (markerRef.current) {
            markerRef.current.setMap(null);
          }
          markerRef.current = new window.google.maps.Marker({
            position: { lat: latitude, lng: longitude },
            map: map,
            draggable: false,
          });

          mapInstanceRef.current = map;
        }
      };

      document.head.appendChild(script);
    } else {
      // Google Maps already loaded, create map directly
      if (mapRef.current && window.google) {
        const map = new window.google.maps.Map(mapRef.current, {
          center: { lat: latitude, lng: longitude },
          zoom: 15,
          disableDefaultUI: false,
          zoomControl: true,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
        });

        if (markerRef.current) {
          markerRef.current.setMap(null);
        }
        markerRef.current = new window.google.maps.Marker({
          position: { lat: latitude, lng: longitude },
          map: map,
          draggable: false,
        });

        mapInstanceRef.current = map;
      }
    }

    return () => {
      if (markerRef.current) {
        markerRef.current.setMap(null);
      }
    };
  }, [latitude, longitude, apiKey]);

  return (
    <div className={styles.container}>
      {(latitude && longitude) ? (
        <div className={styles.mapWrapper}>
          <div ref={mapRef} className={styles.map} />
        </div>
      ) : (
        <div className={styles.mapPlaceholder}>
          <p className={styles.placeholderText}>Enter coordinates below to view map</p>
        </div>
      )}
      
      <div className={styles.coordinates}>
        <div className={styles.coordRow}>
          <label className={styles.coordLabel}>Latitude</label>
          <input
            type="number"
            step="any"
            value={latitude !== null && latitude !== undefined ? latitude : ''}
            onChange={(e) => {
              const value = e.target.value ? parseFloat(e.target.value) : null;
              if (onLatitudeChange) {
                onLatitudeChange(value);
              }
            }}
            onWheel={(e) => e.currentTarget.blur()}
            className={styles.coordInput}
            placeholder="Enter latitude"
          />
        </div>
        <div className={styles.coordRow}>
          <label className={styles.coordLabel}>Longitude</label>
          <input
            type="number"
            step="any"
            value={longitude !== null && longitude !== undefined ? longitude : ''}
            onChange={(e) => {
              const value = e.target.value ? parseFloat(e.target.value) : null;
              if (onLongitudeChange) {
                onLongitudeChange(value);
              }
            }}
            onWheel={(e) => e.currentTarget.blur()}
            className={styles.coordInput}
            placeholder="Enter longitude"
          />
        </div>
      </div>
    </div>
  );
};

export default PropertyMap;

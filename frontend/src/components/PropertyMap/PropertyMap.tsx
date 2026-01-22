import { useEffect, useRef } from 'react';

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
  <div className="w-full flex flex-col gap-2 mb-[0.2rem]">
    {(latitude && longitude) ? (
      <div className="w-full h-[200px] rounded-lg overflow-hidden border border-white/10 bg-white/5 relative">
        <div
          ref={mapRef}
          className="w-full h-full border-none pointer-events-auto"
        />
      </div>
    ) : (
      <div className="w-full h-[200px] flex items-center justify-center rounded-lg border border-white/10 bg-white/5">
        <p className="text-white/50 text-[0.75rem]">
          Enter coordinates below to view map
        </p>
      </div>
    )}

    <div className="grid grid-cols-2 gap-[0.8rem] text-[0.7rem]">
      <div className="flex flex-col gap-[0.15rem] w-full">
        <label className="text-[0.55rem] uppercase text-(--text-secondary) font-medium tracking-[0.02em] pl-[0.2rem]">
          Latitude
        </label>
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
          placeholder="Enter latitude"
          className="
            w-full px-[0.2rem] py-[0.3rem]
            rounded
            bg-transparent
            border border-transparent
            text-(--text-primary)
            text-[0.8rem]
            outline-none
            font-inherit
            transition-all duration-200 ease-in-out
            hover:bg-white/5 hover:border-(--card-border)
            focus:bg-[rgba(37,99,235,0.15)] focus:border-(--accent-blue)
          "
        />
      </div>

      <div className="flex flex-col gap-[0.15rem] w-full">
        <label className="text-[0.55rem] uppercase text-(--text-secondary) font-medium tracking-[0.02em] pl-[0.2rem]">
          Longitude
        </label>
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
          placeholder="Enter longitude"
          className="
            w-full px-[0.2rem] py-[0.3rem]
            rounded
            bg-transparent
            border border-transparent
            text-(--text-primary)
            text-[0.8rem]
            outline-none
            font-inherit
            transition-all duration-200 ease-in-out
            hover:bg-white/5 hover:border-(--card-border)
            focus:bg-[rgba(37,99,235,0.15)] focus:border-(--accent-blue)
          "
        />
      </div>
    </div>
  </div>
);

};

export default PropertyMap;

"""
Geo-intelligence enrichment service using Google Maps APIs.
Enriches canonical listings with location-based data.
Supports parallel API calls for improved performance.
"""
import os
import json
import hashlib
import re
from typing import Dict, Any, Optional, List
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.api.models.canonical import CanonicalListing
from services.api.services.canonical_service import get_canonical, update_canonical
from services.api.database import get_db


# Google Maps API client
try:
    import googlemaps
    GOOGLEMAPS_AVAILABLE = True
except ImportError:
    GOOGLEMAPS_AVAILABLE = False
    googlemaps = None


def enrich_geo_intelligence(listing_id: UUID) -> Dict[str, Any]:
    """
    Main function to enrich a listing with geo-intelligence data.
    
    Args:
        listing_id: The listing ID to enrich
        
    Returns:
        Dictionary with enrichment results and status
    """
    if not GOOGLEMAPS_AVAILABLE:
        return {
            "success": False,
            "error": "googlemaps library not installed. Install with: pip install googlemaps"
        }
    
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "GOOGLE_MAPS_API_KEY environment variable not set. Please add it to your .env file in the project root."
        }
    
    # Get canonical listing
    canonical = get_canonical(listing_id)
    if not canonical:
        return {
            "success": False,
            "error": "Canonical listing not found"
        }
    
    # Check if location data is available
    location = canonical.location
    if not location.street_address and not (location.city and location.state):
        return {
            "success": False,
            "error": "Insufficient location data. Need at least street_address or (city and state)"
        }
    
    # Build address string
    address_parts = []
    if location.street_address:
        address_parts.append(location.street_address)
    if location.city:
        address_parts.append(location.city)
    if location.state:
        address_parts.append(location.state)
    if location.zip_code:
        address_parts.append(location.zip_code)
    
    address = ", ".join(address_parts) + ", US"  # Always append US
    
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=api_key)
    
    # Task 1: Geocoding
    geo_result = _geocode_address(gmaps, address, listing_id)
    if not geo_result or not geo_result.get("latitude"):
        return {
            "success": False,
            "error": "Geocoding failed. Could not determine coordinates."
        }
    
    lat = geo_result["latitude"]
    lng = geo_result["longitude"]
    
    # Task 2-4: Run independent geo tasks in parallel
    print(f"Running geo-intelligence tasks in parallel for listing {listing_id}...")
    import time
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all independent tasks
        directions_future = executor.submit(
            _get_nearest_major_road_and_directions, 
            gmaps, lat, lng, address
        )
        pois_future = executor.submit(_get_nearby_pois, gmaps, lat, lng, 483)
        water_future = executor.submit(_check_water_body_proximity, gmaps, lat, lng)
        
        # Wait for all results
        directions_result = directions_future.result()
        pois = pois_future.result()
        water_body_info = water_future.result()
    
    elapsed_time = time.time() - start_time
    print(f"✓ Completed geo-intelligence tasks in {elapsed_time:.2f} seconds")
    
    # Update canonical with geo data (only if fields are empty or null)
    updated = False
    
    # Update location fields (only if not already set)
    if not location.latitude:
        location.latitude = lat
        updated = True
    if not location.longitude:
        location.longitude = lng
        updated = True
    if not location.county and geo_result.get("county"):
        location.county = geo_result["county"]
        updated = True
    if not location.country:
        location.country = "US"
        updated = True
    
    # Update remarks.directions (only if not already set)
    if not canonical.remarks.directions and directions_result.get("direction_summary"):
        canonical.remarks.directions = directions_result["direction_summary"]
        updated = True
    
    # Update property.distance_to_water (only if not already set)
    if not canonical.property.distance_to_water and water_body_info:
        distance_miles = water_body_info.get("distance_miles", 0)
        distance_meters = water_body_info.get("distance_meters", 0)
        if distance_miles > 0:
            # Store as number (miles)
            canonical.property.distance_to_water = distance_miles
        elif distance_meters > 0:
            # Convert meters to miles and store as number
            canonical.property.distance_to_water = distance_meters / 1609.34  # meters to miles
        updated = True
    
    # Update property.waterfront_features (only if water body is directly adjacent)
    if not canonical.property.waterfront_features and water_body_info and water_body_info.get("is_adjacent"):
        features = water_body_info.get("features")
        if features:
            canonical.property.waterfront_features = features
            updated = True
    
    # Store POIs separately in location.poi (leave view as is)
    if pois:
        # Deduplicate POIs by name (keep the closest one if duplicates exist)
        deduplicated_pois = _deduplicate_pois_by_name(pois)
        
        # Convert POIs to the format expected by the canonical model (without distance_meters)
        location.poi = [
            {
                "name": poi.get("name", ""),
                "category": poi.get("category", "")
            }
            for poi in deduplicated_pois
        ]
        updated = True
        
        # Also save POIs to database for future use (with distance_meters for internal use)
        _save_pois_to_database(listing_id, deduplicated_pois)
    
    # Update canonical if changes were made
    if updated:
        update_canonical(listing_id, canonical)
    
    return {
        "success": True,
        "geo": geo_result,
        "directions": directions_result,
        "nearby_pois": pois,
        "water_body": water_body_info,
        "canonical_updated": updated
    }


def _geocode_address(gmaps, address: str, listing_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Geocode an address using Google Maps Geocoding API.
    
    Returns:
        Dictionary with latitude, longitude, neighborhood, county, country
    """
    # Check cache first
    cache_key = _get_cache_key("geocode", address)
    cached = _get_cached_result(cache_key)
    if cached:
        return cached
    
    try:
        # Geocode the address
        geocode_result = gmaps.geocode(address)
        
        if not geocode_result:
            return None
        
        # Select highest confidence result (first result is usually best)
        result = geocode_result[0]
        geometry = result.get("geometry", {})
        location = geometry.get("location", {})
        
        lat = location.get("lat")
        lng = location.get("lng")
        
        if not lat or not lng:
            return None
        
        # Extract address components
        address_components = result.get("address_components", [])
        
        neighborhood = None
        county = None
        
        for component in address_components:
            types = component.get("types", [])
            long_name = component.get("long_name")
            
            if "sublocality" in types or "neighborhood" in types:
                neighborhood = long_name
            elif "administrative_area_level_2" in types:  # County
                county = long_name
        
        geo_data = {
            "latitude": lat,
            "longitude": lng,
            "neighborhood": neighborhood,
            "county": county,
            "country": "US"
        }
        
        # Cache the result
        _cache_result(cache_key, geo_data)
        
        return geo_data
    
    except (ConnectionError, OSError) as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"Geocoding error: Network connection failed - Cannot reach Google Maps API. Check your internet connection and DNS settings.")
        else:
            print(f"Geocoding error: Network error - {error_msg}")
        return None
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "11001" in error_msg:
            print(f"Geocoding error: Network connection failed - Cannot reach Google Maps API. Check your internet connection.")
        else:
            print(f"Geocoding error: {error_msg}")
        return None


def _get_nearest_major_road_and_directions(
    gmaps,
    lat: float,
    lng: float,
    destination_address: str
) -> Dict[str, Any]:
    """
    Find nearest major road and generate simple directions.
    
    Returns:
        Dictionary with nearest_major_road and direction_summary
    """
    cache_key = _get_cache_key("directions", f"{lat},{lng}")
    cached = _get_cached_result(cache_key)
    if cached:
        return cached
    
    try:
        # Use reverse geocoding to find nearby roads
        reverse_geocode = gmaps.reverse_geocode((lat, lng))
        
        major_road = None
        major_road_types = [
            "route",  # Highway, street, etc.
            "street_address"  # Sometimes major roads appear as addresses
        ]
        
        # Look for major roads in reverse geocoding results
        # Prioritize routes with specific road types
        road_priority = ["route", "street_address", "intersection"]
        
        for result in reverse_geocode:
            address_components = result.get("address_components", [])
            for component in address_components:
                types = component.get("types", [])
                # Check for route type first (highways, major roads)
                if "route" in types:
                    long_name = component.get("long_name")
                    short_name = component.get("short_name")
                    # Prefer long name, fallback to short name
                    road_name = long_name or short_name
                    if road_name:
                        # Filter out minor roads and restricted roads
                        road_lower = road_name.lower()
                        minor_indicators = ["alley", "lane", "court", "place", "circle", "restricted", "private", "unnamed", "service road"]
                        if not any(indicator in road_lower for indicator in minor_indicators):
                            # Clean the road name (remove any road type suffixes)
                            road_name_clean = re.sub(r'\s*(Restricted usage road|Unnamed road|Private road|Service road).*$', '', road_name, flags=re.IGNORECASE).strip()
                            major_road = road_name_clean or road_name
                            break
            if major_road:
                break
        
        # If no major road found, try nearby search for routes
        if not major_road:
            try:
                places_result = gmaps.places_nearby(
                    location=(lat, lng),
                    radius=1000,  # 1km radius
                    type="route"
                )
                
                if places_result.get("results"):
                    # Get the closest route, but filter out restricted/private roads
                    for place in places_result.get("results", []):
                        place_name = place.get("name", "")
                        if place_name:
                            place_lower = place_name.lower()
                            # Skip restricted/private/unnamed roads
                            if not any(indicator in place_lower for indicator in ["restricted", "private", "unnamed", "service road"]):
                                # Clean the road name (re is already imported at module level)
                                major_road = re.sub(r'\s*(Restricted usage road|Unnamed road|Private road|Service road).*$', '', place_name, flags=re.IGNORECASE).strip()
                                if major_road:
                                    break
            except:
                pass
        
        direction_summary = None
        
        if major_road:
            # Generate simple directions from major road to property
            try:
                directions = gmaps.directions(
                    origin=major_road,
                    destination=destination_address,
                    mode="driving"
                )
                
                if directions and directions[0].get("legs"):
                    leg = directions[0]["legs"][0]
                    steps = leg.get("steps", [])
                    
                    # Build simple direction summary (max 3 steps)
                    summary_parts = []
                    
                    # Road type suffixes to remove
                    road_type_patterns = [
                        r'\s*Restricted usage road\s*',
                        r'\s*Unnamed road\s*',
                        r'\s*Private road\s*',
                        r'\s*Service road\s*',
                        r'\s*Access road\s*',
                        r'\s*\(Restricted usage road\)',
                        r'\s*\(Unnamed road\)',
                        r'\s*\(Private road\)',
                    ]
                    
                    for i, step in enumerate(steps[:3]):
                        # Prefer text instructions if available (cleaner)
                        instruction = step.get("html_instructions", "")
                        
                        # Clean HTML tags
                        instruction = re.sub(r'<[^>]+>', '', instruction)
                        
                        # Decode HTML entities
                        instruction = instruction.replace("&nbsp;", " ")
                        instruction = instruction.replace("&amp;", "&")
                        instruction = instruction.replace("&lt;", "<")
                        instruction = instruction.replace("&gt;", ">")
                        instruction = instruction.replace("&quot;", '"')
                        instruction = instruction.replace("&#39;", "'")
                        
                        # Remove road type suffixes
                        for pattern in road_type_patterns:
                            instruction = re.sub(pattern, '', instruction, flags=re.IGNORECASE)
                        
                        # Clean up extra spaces
                        instruction = re.sub(r'\s+', ' ', instruction).strip()
                        
                        # Simplify common patterns
                        instruction = re.sub(r'\btoward\s+', 'onto ', instruction, flags=re.IGNORECASE)
                        instruction = re.sub(r'\bHead\s+', '', instruction, flags=re.IGNORECASE)
                        instruction = re.sub(r'\bContinue\s+', '', instruction, flags=re.IGNORECASE)
                        
                        # Capitalize first letter
                        if instruction:
                            instruction = instruction[0].upper() + instruction[1:] if len(instruction) > 1 else instruction.upper()
                            summary_parts.append(instruction)
                    
                    if summary_parts:
                        # Join with simple separators, limit length
                        direction_summary = ". ".join(summary_parts[:3])
                        # Final cleanup
                        direction_summary = re.sub(r'\s+', ' ', direction_summary).strip()
                        if len(direction_summary) > 200:
                            direction_summary = direction_summary[:197] + "..."
                    else:
                        direction_summary = f"From {major_road}, follow directions to property"
            except Exception as e:
                # If directions fail, create simple summary
                direction_summary = f"From {major_road}, follow directions to property"
        
        result = {
            "nearest_major_road": major_road,
            "direction_summary": direction_summary
        }
        
        # Cache result
        _cache_result(cache_key, result)
        
        return result
    
    except Exception as e:
        print(f"Error getting directions: {str(e)}")
        return {
            "nearest_major_road": None,
            "direction_summary": None
        }


def _search_poi_category(gmaps, lat: float, lng: float, radius: int, place_type: str, category: str) -> List[Dict[str, Any]]:
    """
    Search for a single POI category.
    Designed to be called in parallel.
    
    Args:
        gmaps: Google Maps client
        lat: Latitude
        lng: Longitude
        radius: Search radius in meters
        place_type: Google Maps place type (e.g., "park", "school")
        category: Category name (e.g., "Parks / trails", "Schools")
        
    Returns:
        List of POI dictionaries with name, category, distance_meters
    """
    try:
        places_result = gmaps.places_nearby(
            location=(lat, lng),
            radius=radius,
            type=place_type
        )
        
        results = places_result.get("results", [])
        category_pois = []
        
        for place in results:
            name = place.get("name")
            if not name:
                continue
            
            # Calculate distance
            place_location = place.get("geometry", {}).get("location", {})
            place_lat = place_location.get("lat")
            place_lng = place_location.get("lng")
            
            if place_lat and place_lng:
                distance = _calculate_distance(lat, lng, place_lat, place_lng)
                
                if distance <= radius:
                    category_pois.append({
                        "name": name,
                        "category": category,
                        "distance_meters": int(distance)
                    })
        
        return category_pois
    except Exception as e:
        print(f"Error searching POI category {category} ({place_type}): {str(e)}")
        return []


def _get_nearby_pois(gmaps, lat: float, lng: float, radius: int = 483) -> List[Dict[str, Any]]:
    """
    Find nearby points of interest within radius (default 0.3 miles = 483 meters).
    Uses parallel processing to search all POI categories concurrently.
    
    Returns:
        List of POI dictionaries with name, category, distance_meters (deduplicated)
    """
    cache_key = _get_cache_key("pois", f"{lat},{lng},{radius}")
    cached = _get_cached_result(cache_key)
    if cached:
        return cached
    
    poi_categories = {
        "park": "Parks / trails",
        "amusement_park": "Parks / trails",
        "campground": "Parks / trails",
        "natural_feature": "Lakes / water bodies",
        "school": "Schools",
        "supermarket": "Grocery / shopping",
        "shopping_mall": "Grocery / shopping",
        "store": "Grocery / shopping",
        "restaurant": "Dining",
        "cafe": "Dining",
        "transit_station": "Public transit",
        "subway_station": "Public transit",
        "bus_station": "Public transit",
    }
    
    all_pois = []
    category_counts = {}
    
    try:
        # Search all POI categories in parallel
        print(f"Searching {len(poi_categories)} POI categories in parallel...")
        import time
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(poi_categories)) as executor:
            # Submit all category searches
            future_to_category = {
                executor.submit(
                    _search_poi_category,
                    gmaps, lat, lng, radius, place_type, category
                ): category
                for place_type, category in poi_categories.items()
            }
            
            # Process results as they complete
            for future in as_completed(future_to_category):
                category = future_to_category[future]
                try:
                    category_pois = future.result()
                    
                    # Add POIs up to max 3 per category
                    for poi in category_pois:
                        if category_counts.get(category, 0) < 3:
                            all_pois.append(poi)
                            category_counts[category] = category_counts.get(category, 0) + 1
                except Exception as e:
                    print(f"Error processing POI category {category}: {str(e)}")
                    continue
        
        elapsed_time = time.time() - start_time
        print(f"✓ Completed POI searches in {elapsed_time:.2f} seconds")
        
        # Deduplicate POIs by name (keep closest)
        all_pois = _deduplicate_pois_by_name(all_pois)
        
        # Re-apply category limits after deduplication
        # (deduplication might have removed some, so we can add more if needed)
        final_pois = []
        final_category_counts = {}
        for poi in all_pois:
            category = poi.get("category")
            if final_category_counts.get(category, 0) < 3:
                final_pois.append(poi)
                final_category_counts[category] = final_category_counts.get(category, 0) + 1
        
        # Sort by distance
        final_pois.sort(key=lambda x: x.get("distance_meters", float('inf')))
        
        # Cache result
        _cache_result(cache_key, final_pois)
        
        return final_pois
    
    except Exception as e:
        print(f"Error getting POIs: {str(e)}")
        return []


def _check_water_body_proximity(gmaps, lat: float, lng: float, threshold: int = 500) -> Optional[Dict[str, Any]]:
    """
    Check if property is near a named lake, river, or major water body.
    
    Returns:
        Dictionary with:
        - "is_adjacent": bool (True if within 100m, False otherwise)
        - "distance_meters": float (distance to nearest water body)
        - "distance_miles": float (distance in miles)
        - "name": str (name of water body)
        - "type": str (type: lake, river, creek, etc.)
        - "features": str (features description if adjacent)
        None if no water body found or error
    """
    cache_key = _get_cache_key("water", f"{lat},{lng},{threshold}")
    cached = _get_cached_result(cache_key)
    if cached is not None:
        return cached
    
    # Threshold for "directly adjacent" (100 meters)
    adjacent_threshold = 100
    
    try:
        nearest_water = None
        nearest_distance = float('inf')
        
        # Search for natural features (lakes, rivers)
        places_result = gmaps.places_nearby(
            location=(lat, lng),
            radius=threshold,
            type="natural_feature"
        )
        
        results = places_result.get("results", [])
        
        for place in results:
            name = place.get("name", "")
            types = place.get("types", [])
            
            # Check if it's a water body
            water_keywords = ["lake", "river", "creek", "pond", "bay", "harbor", "marina", "ocean", "beach"]
            name_lower = name.lower()
            
            if any(keyword in name_lower for keyword in water_keywords):
                # Calculate distance
                place_location = place.get("geometry", {}).get("location", {})
                place_lat = place_location.get("lat")
                place_lng = place_location.get("lng")
                
                if place_lat and place_lng:
                    distance = _calculate_distance(lat, lng, place_lat, place_lng)
                    
                    if distance <= threshold and distance < nearest_distance:
                        # Determine water body type
                        water_type = "water body"
                        for keyword in ["lake", "river", "creek", "pond", "bay", "harbor", "marina", "ocean", "beach"]:
                            if keyword in name_lower:
                                water_type = keyword
                                break
                        
                        nearest_water = {
                            "name": name,
                            "type": water_type,
                            "distance_meters": distance,
                            "distance_miles": round(distance * 0.000621371, 2)
                        }
                        nearest_distance = distance
        
        # Also check for specific water body types
        water_types = ["lake", "river", "water"]
        for water_type in water_types:
            try:
                places_result = gmaps.places_nearby(
                    location=(lat, lng),
                    radius=threshold,
                    keyword=water_type
                )
                
                results = places_result.get("results", [])
                for place in results:
                    place_name = place.get("name", "")
                    place_location = place.get("geometry", {}).get("location", {})
                    place_lat = place_location.get("lat")
                    place_lng = place_location.get("lng")
                    
                    if place_lat and place_lng:
                        distance = _calculate_distance(lat, lng, place_lat, place_lng)
                        
                        if distance <= threshold and distance < nearest_distance:
                            nearest_water = {
                                "name": place_name or water_type.title(),
                                "type": water_type,
                                "distance_meters": distance,
                                "distance_miles": round(distance * 0.000621371, 2)
                            }
                            nearest_distance = distance
            except:
                continue
        
        if nearest_water:
            # Check if adjacent (within 100m)
            is_adjacent = nearest_distance <= adjacent_threshold
            
            # Build features description if adjacent
            features = None
            if is_adjacent:
                features_parts = []
                if nearest_water["name"]:
                    features_parts.append(nearest_water["name"])
                features_parts.append(nearest_water["type"].title())
                features = ", ".join(features_parts)
            
            result = {
                "is_adjacent": is_adjacent,
                "distance_meters": nearest_water["distance_meters"],
                "distance_miles": nearest_water["distance_miles"],
                "name": nearest_water["name"],
                "type": nearest_water["type"],
                "features": features
            }
            
            _cache_result(cache_key, result)
            return result
        
        _cache_result(cache_key, None)
        return None
    
    except Exception as e:
        print(f"Error checking water body proximity: {str(e)}")
        return None


def _deduplicate_pois_by_name(pois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate POIs by name, keeping only the closest one if duplicates exist.
    
    Sometimes Google Maps returns the same location at slightly different coordinates,
    so we keep only the closest instance of each POI name.
    
    Args:
        pois: List of POI dictionaries with name, category, distance_meters
        
    Returns:
        Deduplicated list of POIs (closest instance kept for each name)
    """
    # Dictionary to track closest POI for each name
    poi_by_name: Dict[str, Dict[str, Any]] = {}
    
    for poi in pois:
        name = poi.get("name", "").strip().lower()
        if not name:
            continue
        
        distance = poi.get("distance_meters", float('inf'))
        
        # If we haven't seen this name, or this instance is closer, keep it
        if name not in poi_by_name:
            poi_by_name[name] = poi
        else:
            existing_distance = poi_by_name[name].get("distance_meters", float('inf'))
            if distance < existing_distance:
                poi_by_name[name] = poi
    
    # Return deduplicated list, sorted by distance
    deduplicated = list(poi_by_name.values())
    deduplicated.sort(key=lambda x: x.get("distance_meters", float('inf')))
    
    return deduplicated


def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points in meters using Haversine formula.
    """
    from math import radians, cos, sin, asin, sqrt
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Earth radius in meters
    r = 6371000
    
    return c * r


def _get_cache_key(cache_type: str, key: str) -> str:
    """Generate cache key."""
    return f"geo_{cache_type}_{hashlib.md5(key.encode()).hexdigest()}"


def _get_cached_result(cache_key: str) -> Optional[Any]:
    """Get cached result from database."""
    try:
        with get_db() as (conn, cur):
            cur.execute(
                """
                SELECT cached_data
                FROM geo_enrichment_cache
                WHERE cache_key = %s
                AND expires_at > now()
                """,
                (cache_key,)
            )
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
    except Exception as e:
        # If table doesn't exist, return None
        pass
    return None


def _cache_result(cache_key: str, data: Any) -> None:
    """Cache result in database."""
    try:
        with get_db() as (conn, cur):
            # Create table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS geo_enrichment_cache (
                    cache_key TEXT PRIMARY KEY,
                    cached_data JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '30 days'
                )
            """)
            
            cur.execute(
                """
                INSERT INTO geo_enrichment_cache (cache_key, cached_data, expires_at)
                VALUES (%s, %s, now() + INTERVAL '30 days')
                ON CONFLICT (cache_key)
                DO UPDATE SET cached_data = EXCLUDED.cached_data, expires_at = EXCLUDED.expires_at
                """,
                (cache_key, json.dumps(data))
            )
    except Exception as e:
        # If caching fails, continue without caching
        print(f"Cache error: {str(e)}")


def _save_pois_to_database(listing_id: UUID, pois: List[Dict[str, Any]]) -> None:
    """Save POIs to database for future use."""
    try:
        with get_db() as (conn, cur):
            # Create table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS listing_pois (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    listing_id UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    distance_meters INTEGER NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    UNIQUE (listing_id, name, category)
                )
            """)
            
            # Delete existing POIs for this listing
            cur.execute(
                "DELETE FROM listing_pois WHERE listing_id = %s",
                (str(listing_id),)
            )
            
            # Insert new POIs
            for poi in pois:
                cur.execute(
                    """
                    INSERT INTO listing_pois (listing_id, name, category, distance_meters)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (listing_id, name, category) DO NOTHING
                    """,
                    (str(listing_id), poi["name"], poi["category"], poi["distance_meters"])
                )
    except Exception as e:
        print(f"Error saving POIs: {str(e)}")

# Performance Optimization Strategies

## Overview
This document outlines optimization strategies to reduce processing time for extraction, enrichment, and geo-intelligence services. The current implementation processes tasks sequentially, which creates significant bottlenecks when handling multiple documents, images, or API calls.

## Current Performance Bottlenecks

### 1. Extraction Pipeline
- **Issue**: Documents are processed sequentially (one at a time)
- **Location**: `services/api/services/extraction_pipeline.py` (lines 53-89)
- **Impact**: High - Each document waits for the previous one to complete

### 2. Image Analysis
- **Issue**: Images are analyzed one by one
- **Location**: `services/api/services/enrichment_service.py` (lines 113-132)
- **Impact**: High - Multiple images processed sequentially

### 3. Geo-Intelligence API Calls
- **Issue**: Geocoding → Directions → POIs → Water body (sequential)
- **Location**: `services/api/services/enrichment_geo_intelligence.py` (lines 81-98)
- **Impact**: Medium-High - Multiple independent API calls waiting on each other

### 4. POI Category Searches
- **Issue**: Each POI category searched sequentially
- **Location**: `services/api/services/enrichment_geo_intelligence.py` (line 449)
- **Impact**: Medium - 12+ sequential API calls for POI categories

### 5. Enrichment Task Orchestration
- **Issue**: Image analysis → Sequencing → Descriptions → Geo → AI description (sequential)
- **Location**: `services/api/services/enrichment_service.py` (lines 50-96)
- **Impact**: Medium - Independent tasks run sequentially

---

## Optimization Strategies

### Strategy 1: Parallelize Document Extraction

**Current Implementation:**
```python
# Sequential processing
for document in documents:
    extraction_result = extract_with_ai(...)
    # Process result
```

**Optimized Implementation:**
```python
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

def _extract_single_document(document, listing_id):
    """Extract from a single document."""
    document_id = document['id']
    storage_path = document['storage_path']
    filename = document['filename']
    
    storage_root = os.getenv("STORAGE_ROOT", "storage")
    file_path = os.path.join(storage_root, storage_path)
    file_extension = os.path.splitext(filename)[1]
    
    try:
        extraction_result = extract_with_ai(
            file_path=file_path,
            file_id=str(document_id),
            file_extension=file_extension
        )
        return extraction_result
    except Exception as e:
        print(f"Error extracting from document {document_id}: {str(e)}")
        return None

# In extract_listing_from_documents():
all_extracted_fields: Dict[str, ExtractedField] = {}

with ThreadPoolExecutor(max_workers=5) as executor:
    future_to_doc = {
        executor.submit(_extract_single_document, document, listing_id): document
        for document in documents
    }
    
    for future in as_completed(future_to_doc):
        try:
            extraction_result = future.result()
            if extraction_result:
                # Merge results
                for field_path, field in extraction_result.extracted_fields.items():
                    if field_path not in all_extracted_fields:
                        all_extracted_fields[field_path] = field
                    else:
                        # Apply existing merging logic
                        existing_field = all_extracted_fields[field_path]
                        if isinstance(field.value, list) and isinstance(existing_field.value, list):
                            combined = list(set(existing_field.value + field.value))
                            all_extracted_fields[field_path] = ExtractedField(
                                value=combined,
                                provenance=field.provenance
                            )
        except Exception as e:
            print(f"Error processing extraction result: {str(e)}")
            continue
```

**Expected Speedup:** 3-5x for multiple documents

**Implementation Notes:**
- Use `max_workers=5` to balance parallelism and API rate limits
- Maintain thread safety when merging results
- Handle exceptions per document to avoid stopping entire extraction

---

### Strategy 2: Parallelize Image Analysis

**Current Implementation:**
```python
# Sequential processing
for image in images:
    analysis = analyze_image_with_vision(file_path, filename)
    _save_image_analysis(image_id, analysis)
```

**Optimized Implementation:**
```python
def _analyze_single_image(image, listing_id):
    """Analyze a single image."""
    image_id = image['id']
    storage_path = image['storage_path']
    filename = image['filename']
    
    file_path = os.path.join(STORAGE_ROOT, storage_path)
    
    if not os.path.exists(file_path):
        return None, None
    
    try:
        analysis = analyze_image_with_vision(file_path, filename)
        _save_image_analysis(image_id, analysis)
        return str(image_id), analysis
    except Exception as e:
        print(f"Error analyzing image {image_id}: {str(e)}")
        return None, None

def _analyze_all_images(listing_id: UUID) -> Dict[str, Dict[str, Any]]:
    """Analyze all images for a listing in parallel."""
    images = _get_listing_images(listing_id)
    results = {}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_image = {
            executor.submit(_analyze_single_image, image, listing_id): image
            for image in images
        }
        
        for future in as_completed(future_to_image):
            try:
                image_id, analysis = future.result()
                if image_id and analysis:
                    results[image_id] = analysis
            except Exception as e:
                print(f"Error processing image analysis: {str(e)}")
    
    return results
```

**Expected Speedup:** 4-5x for multiple images

**Implementation Notes:**
- Process 5 images concurrently to avoid overwhelming the AI API
- Each image analysis is independent, making this ideal for parallelization
- Database writes are already handled per image in `_save_image_analysis`

---

### Strategy 3: Parallelize Geo-Intelligence API Calls

**Current Implementation:**
```python
# Sequential API calls
geo_result = _geocode_address(gmaps, address, listing_id)
directions_result = _get_nearest_major_road_and_directions(gmaps, lat, lng, address)
pois = _get_nearby_pois(gmaps, lat, lng, radius=483)
water_body_info = _check_water_body_proximity(gmaps, lat, lng)
```

**Optimized Implementation:**
```python
def enrich_geo_intelligence(listing_id: UUID) -> Dict[str, Any]:
    """Main function to enrich a listing with geo-intelligence data."""
    # ... existing setup code (lines 35-75) ...
    
    gmaps = googlemaps.Client(key=api_key)
    
    # Step 1: Geocode first (needed for lat/lng)
    geo_result = _geocode_address(gmaps, address, listing_id)
    if not geo_result or not geo_result.get("latitude"):
        return {
            "success": False,
            "error": "Geocoding failed. Could not determine coordinates."
        }
    
    lat = geo_result["latitude"]
    lng = geo_result["longitude"]
    
    # Step 2: Run independent tasks in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
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
    
    # ... rest of existing code (lines 100-169) ...
```

**Expected Speedup:** 2-3x for geo-intelligence

**Implementation Notes:**
- Geocoding must complete first to get lat/lng
- Directions, POIs, and water body checks are independent and can run in parallel
- Use `max_workers=3` to avoid hitting Google Maps API rate limits

---

### Strategy 4: Parallelize POI Category Searches

**Current Implementation:**
```python
# Sequential POI category searches
for place_type, category in poi_categories.items():
    places_result = gmaps.places_nearby(...)
    # Process results
```

**Optimized Implementation:**
```python
def _search_poi_category(gmaps, lat, lng, radius, place_type, category):
    """Search for a single POI category."""
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
        print(f"Error searching POI category {category}: {str(e)}")
        return []

def _get_nearby_pois(gmaps, lat: float, lng: float, radius: int = 483) -> List[Dict[str, Any]]:
    """Find nearby points of interest within radius (parallelized)."""
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
    
    # Search all categories in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(poi_categories)) as executor:
        future_to_category = {
            executor.submit(
                _search_poi_category, 
                gmaps, lat, lng, radius, place_type, category
            ): category
            for place_type, category in poi_categories.items()
        }
        
        for future in concurrent.futures.as_completed(future_to_category):
            try:
                category_pois = future.result()
                for poi in category_pois:
                    category = poi["category"]
                    if category_counts.get(category, 0) < 3:
                        all_pois.append(poi)
                        category_counts[category] = category_counts.get(category, 0) + 1
            except Exception as e:
                print(f"Error processing POI category: {str(e)}")
    
    # Sort by distance
    all_pois.sort(key=lambda x: x["distance_meters"])
    
    # Cache result
    _cache_result(cache_key, all_pois)
    
    return all_pois
```

**Expected Speedup:** 3-4x for POI searches

**Implementation Notes:**
- All POI category searches are independent and can run in parallel
- Limit to 3 POIs per category (enforced after parallel execution)
- Use `max_workers=len(poi_categories)` to search all categories simultaneously

---

### Strategy 5: Parallelize Enrichment Task Orchestration

**Current Implementation:**
```python
# Sequential task execution
if analyze_images:
    image_results = _analyze_all_images(listing_id)
    sequence = generate_photo_sequence(...)
    # ...

if generate_descriptions:
    descriptions = generate_listing_descriptions(canonical)
    # ...

if enrich_geo:
    geo_result = enrich_geo_intelligence(listing_id)
    # ...
```

**Optimized Implementation:**
```python
def enrich_listing(
    listing_id: UUID,
    analyze_images: bool = True,
    generate_descriptions: bool = True,
    enrich_geo: bool = True
) -> Dict[str, Any]:
    """Main enrichment function with parallel task execution."""
    results = {
        "image_analysis": {},
        "photo_sequence": [],
        "primary_image": None,
        "descriptions": {},
        "geo_intelligence": {},
        "ai_property_description": {}
    }
    
    # Run independent tasks in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit independent tasks
        image_future = None
        if analyze_images:
            image_future = executor.submit(_analyze_all_images, listing_id)
        
        geo_future = None
        if enrich_geo:
            geo_future = executor.submit(enrich_geo_intelligence, listing_id)
        
        # Wait for image analysis (needed for sequencing)
        if image_future:
            image_results = image_future.result()
            results["image_analysis"] = image_results
            
            # Task 3: Photo sequencing (depends on image analysis)
            sequence = generate_photo_sequence(str(listing_id))
            results["photo_sequence"] = sequence
            
            # Identify primary image
            primary_id = identify_primary_image(str(listing_id))
            results["primary_image"] = primary_id
            
            # Update database with sequencing and primary flag
            _update_image_sequencing(listing_id, sequence, primary_id)
            
            # Sequence and rename image files
            from services.api.services.image_rename_helper import sequence_and_rename_images
            sequence_and_rename_images(str(listing_id))
        
        # Get geo results (already running in parallel)
        if geo_future:
            geo_result = geo_future.result()
            results["geo_intelligence"] = geo_result
        
        # Generate descriptions (can run after image analysis completes)
        if generate_descriptions:
            canonical = get_canonical(listing_id)
            if canonical:
                descriptions = generate_listing_descriptions(canonical)
                results["descriptions"] = descriptions
                
                # Update canonical with descriptions
                canonical.remarks.public_remarks = descriptions.get("public_remarks")
                canonical.remarks.syndication_remarks = descriptions.get("syndication_remarks")
                update_canonical(listing_id, canonical)
        
        # AI property description (depends on geo for POIs)
        try:
            if geo_future:
                geo_future.result()  # Ensure geo is done
            ai_desc_result = generate_ai_property_description(listing_id)
            results["ai_property_description"] = ai_desc_result
        except Exception as e:
            results["ai_property_description"] = {
                "success": False,
                "error": str(e)
            }
    
    return results
```

**Expected Speedup:** 1.5-2x for overall enrichment

**Implementation Notes:**
- Image analysis and geo-intelligence can run in parallel (independent)
- Photo sequencing depends on image analysis
- AI property description depends on geo-intelligence for POI data
- Use `max_workers=3` to balance parallelism and resource usage

---

### Strategy 6: Use Async/Await for I/O-Bound Operations

**Concept:**
Convert blocking API calls to async operations for better concurrency.

**Implementation Approach:**
```python
import asyncio
import aiohttp
from functools import partial

async def async_geocode(gmaps, address):
    """Async wrapper for geocoding."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, gmaps.geocode, address)

async def async_places_nearby(gmaps, location, radius, place_type):
    """Async wrapper for places_nearby."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        gmaps.places_nearby,
        location, radius, place_type
    )

async def enrich_geo_intelligence_async(listing_id: UUID):
    """Async version of geo-intelligence enrichment."""
    # ... setup code ...
    
    # Geocode first
    geo_result = await async_geocode(gmaps, address)
    
    # Run independent tasks concurrently
    directions_task = async_get_directions(gmaps, lat, lng, address)
    pois_task = async_get_pois(gmaps, lat, lng)
    water_task = async_check_water(gmaps, lat, lng)
    
    directions_result, pois, water_body_info = await asyncio.gather(
        directions_task, pois_task, water_task
    )
    
    # ... rest of processing ...
```

**Expected Speedup:** Additional 10-20% on top of thread-based parallelism

**Implementation Notes:**
- Requires converting endpoints to async (`async def`)
- Use `asyncio.gather()` for concurrent async operations
- Wrap sync Google Maps calls in `run_in_executor()`

---

### Strategy 7: Batch Image Material Extraction

**Current Implementation:**
Images processed sequentially in `extraction_image_materials.py`

**Optimized Implementation:**
```python
def extract_materials_from_images(listing_id: UUID, batch_size: int = 5):
    """Extract materials from images in parallel batches."""
    images = _get_listing_images(listing_id)
    
    all_fields = {}
    
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [
            executor.submit(_extract_materials_from_single_image, image)
            for image in images
        ]
        
        for future in as_completed(futures):
            try:
                fields = future.result()
                if fields:
                    # Merge fields with existing
                    for field_path, field in fields.items():
                        if field_path not in all_fields:
                            all_fields[field_path] = field
                        else:
                            # Apply merging logic (confidence-based)
                            existing_field = all_fields[field_path]
                            image_confidence = field.provenance.confidence or 0.5
                            text_confidence = existing_field.provenance.confidence or 0.5
                            
                            if image_confidence > text_confidence:
                                all_fields[field_path] = field
            except Exception as e:
                print(f"Error extracting materials from image: {str(e)}")
    
    return all_fields
```

**Expected Speedup:** 4-5x for image material extraction

---

### Strategy 8: Optimize Caching

**Current State:**
- Geocoding results are cached
- POI results are cached
- Cache expires after 30 days

**Optimization Opportunities:**

1. **Coordinate Grid Caching:**
```python
def _get_grid_cache_key(lat: float, lng: float, grid_size: float = 0.001):
    """Create cache key based on coordinate grid."""
    # Round to grid (e.g., 100m grid)
    grid_lat = round(lat / grid_size) * grid_size
    grid_lng = round(lng / grid_size) * grid_size
    return f"geo_grid_{grid_lat}_{grid_lng}"

def _get_cached_pois_for_grid(lat: float, lng: float):
    """Get cached POIs for coordinate grid."""
    cache_key = _get_grid_cache_key(lat, lng)
    return _get_cached_result(cache_key)
```

2. **Pre-cache Common Addresses:**
- Cache geocoding for common street addresses
- Cache POIs for common neighborhoods

3. **Extend Cache Duration:**
- POI data rarely changes: extend to 90 days
- Geocoding: extend to 60 days

**Expected Speedup:** 50-80% for repeated locations

---

### Strategy 9: Reduce API Call Overhead

**Optimization Opportunities:**

1. **Batch Google Maps API Requests:**
   - Use Google Maps Places API batch requests where available
   - Combine multiple POI searches into single requests

2. **Request Queuing:**
```python
from queue import Queue
import threading

class APIRequestQueue:
    def __init__(self, max_concurrent=10):
        self.queue = Queue()
        self.max_concurrent = max_concurrent
        self.semaphore = threading.Semaphore(max_concurrent)
    
    def submit_request(self, func, *args, **kwargs):
        """Submit API request to queue."""
        future = concurrent.futures.Future()
        
        def worker():
            with self.semaphore:
                try:
                    result = func(*args, **kwargs)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
        
        threading.Thread(target=worker).start()
        return future
```

3. **Reduce Redundant API Calls:**
   - Check cache before making API calls
   - Skip API calls if data already exists in canonical

**Expected Speedup:** 10-20% reduction in API overhead

---

### Strategy 10: Database Query Optimization

**Current State:**
- Individual database writes per image/document
- Multiple queries for canonical updates

**Optimization Opportunities:**

1. **Batch Database Writes:**
```python
def _save_image_analyses_batch(analyses: List[Tuple[str, Dict[str, Any]]]):
    """Save multiple image analyses in a single transaction."""
    with get_db() as (conn, cur):
        for image_id, analysis in analyses:
            # Use executemany for bulk inserts
            cur.execute(
                """
                UPDATE listing_images
                SET ai_suggested_label = %s, is_primary = %s
                WHERE id = %s
                """,
                (analysis.get("room_label"), 
                 analysis.get("is_primary_candidate", False),
                 image_id)
            )
        conn.commit()
```

2. **Add Database Indexes:**
```sql
-- Add indexes for frequently queried fields
CREATE INDEX IF NOT EXISTS idx_listing_images_listing_id 
    ON listing_images(listing_id);
CREATE INDEX IF NOT EXISTS idx_documents_listing_id 
    ON documents(listing_id);
CREATE INDEX IF NOT EXISTS idx_geo_cache_key 
    ON geo_enrichment_cache(cache_key);
```

3. **Reduce Database Round-trips:**
   - Combine multiple SELECT queries into one
   - Use JOINs instead of multiple queries

**Expected Speedup:** 20-30% for database operations

---

## Expected Overall Performance Improvement

### Current Processing Times (Estimated)
- **Extraction**: 30-60 seconds per document
- **Image Analysis**: 5-10 seconds per image
- **Geo-Intelligence**: 10-20 seconds
- **Overall Enrichment**: 2-5 minutes

### Optimized Processing Times (Estimated)
- **Extraction**: 10-15 seconds (3-5 documents in parallel)
- **Image Analysis**: 1-2 seconds per image (5 images in parallel)
- **Geo-Intelligence**: 5-8 seconds (parallel API calls)
- **Overall Enrichment**: 1-2 minutes (parallel tasks)

### Total Expected Improvement
**2-4x reduction in processing time**

---

## Implementation Priority

### Phase 1: High Impact, Easy Implementation
1. ✅ **Parallelize Document Extraction** (#1)
   - Impact: High
   - Difficulty: Easy
   - Estimated Time: 2-3 hours

2. ✅ **Parallelize Image Analysis** (#2)
   - Impact: High
   - Difficulty: Easy
   - Estimated Time: 2-3 hours

### Phase 2: High Impact, Medium Difficulty
3. ✅ **Parallelize Geo-Intelligence API Calls** (#3)
   - Impact: High
   - Difficulty: Medium
   - Estimated Time: 3-4 hours

4. ✅ **Parallelize POI Category Searches** (#4)
   - Impact: Medium-High
   - Difficulty: Medium
   - Estimated Time: 2-3 hours

### Phase 3: Medium Impact, Medium Difficulty
5. ✅ **Parallelize Enrichment Task Orchestration** (#5)
   - Impact: Medium
   - Difficulty: Medium
   - Estimated Time: 3-4 hours

6. ✅ **Batch Image Material Extraction** (#7)
   - Impact: Medium
   - Difficulty: Easy
   - Estimated Time: 1-2 hours

### Phase 4: Additional Optimizations
7. ⚠️ **Use Async/Await** (#6)
   - Impact: Low-Medium
   - Difficulty: High (requires async refactoring)
   - Estimated Time: 8-12 hours

8. ✅ **Optimize Caching** (#8)
   - Impact: Low-Medium
   - Difficulty: Easy
   - Estimated Time: 2-3 hours

9. ✅ **Reduce API Call Overhead** (#9)
   - Impact: Low
   - Difficulty: Medium
   - Estimated Time: 4-6 hours

10. ✅ **Database Query Optimization** (#10)
    - Impact: Low-Medium
    - Difficulty: Easy
    - Estimated Time: 2-3 hours

---

## Implementation Guidelines

### Thread Safety Considerations
- Use thread-safe data structures when merging results
- Ensure database connections are properly managed in thread pools
- Use locks for shared state if needed

### Error Handling
- Handle exceptions per task to avoid stopping entire pipeline
- Log errors for debugging
- Return partial results if some tasks fail

### Resource Management
- Limit `max_workers` to avoid overwhelming APIs or database
- Monitor API rate limits (Google Maps, Gemini)
- Use connection pooling (already implemented)

### Testing Strategy
1. Test with single document/image first
2. Test with multiple documents/images
3. Test error handling (API failures, timeouts)
4. Verify thread safety
5. Performance benchmarking before/after

### Monitoring
- Add timing logs for each optimization
- Monitor API usage and rate limits
- Track database connection pool usage
- Measure actual speedup achieved

---

## Dependencies

### Required Libraries
- `concurrent.futures` (built-in Python library)
- `threading` (built-in Python library)
- `asyncio` (built-in Python library, for Strategy 6)

### No Additional Dependencies Required
All optimizations use Python standard library modules.

---

## Notes

- All optimizations maintain backward compatibility
- Existing caching mechanisms are preserved
- Error handling is enhanced for parallel execution
- Database transaction safety is maintained
- API rate limits should be monitored after implementation

---

## Revision History

- **2024-01-XX**: Initial documentation created
- Documented all 10 optimization strategies
- Prioritized implementation phases
- Estimated performance improvements

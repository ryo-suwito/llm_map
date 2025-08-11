"""
FastAPI Backend for Google Maps Integration
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from typing import Optional, Dict, Any
from urllib.parse import quote
import time

app = FastAPI(title="Google Maps API Backend", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
DEFAULT_RADIUS = 5000
MAX_RESULTS = 5

# Cache for user location
location_cache = {}

@app.get("/")
async def root():
    return {"message": "Google Maps API Backend", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/location")
async def get_user_location(client_ip: Optional[str] = None):
    """Get user's current location using IP geolocation."""
    
    cache_key = client_ip or "default"
    current_time = time.time()
    cache_duration = 600  # 10 minutes
    
    # Check cache
    if (cache_key in location_cache and 
        current_time - location_cache[cache_key]["timestamp"] < cache_duration):
        cached_data = location_cache[cache_key]["data"]
        return {
            "location": f"{cached_data['city']}, {cached_data['region']}, {cached_data['country']}",
            "coordinates": {"lat": cached_data["lat"], "lng": cached_data["lng"]},
            "cached": True
        }
    
    try:
        response = requests.get(
            "http://ip-api.com/json/?fields=lat,lon,city,regionName,country", 
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("lat") and data.get("lon"):
                location_data = {
                    "lat": data["lat"],
                    "lng": data["lon"],
                    "city": data.get("city", "Unknown"),
                    "region": data.get("regionName", "Unknown"),
                    "country": data.get("country", "Unknown")
                }
                
                # Cache the result
                location_cache[cache_key] = {
                    "data": location_data,
                    "timestamp": current_time
                }
                
                return {
                    "location": f"{location_data['city']}, {location_data['region']}, {location_data['country']}",
                    "coordinates": {"lat": location_data["lat"], "lng": location_data["lng"]},
                    "cached": False
                }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not detect location: {str(e)}")
    
    raise HTTPException(status_code=500, detail="Unable to detect location")

@app.get("/places/nearby")
async def find_nearby_places(
    query: str = Query(..., description="What to search for (e.g., 'cafe', 'restaurant')"),
    location: Optional[str] = Query(None, description="Location to search near (optional)")
):
    """Find places nearby a location."""
    
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    # Auto-detect location if not provided
    if not location:
        try:
            location_response = await get_user_location()
            location = location_response["location"]
        except:
            raise HTTPException(status_code=400, detail="Could not determine location")
    
    try:
        # Google Places Text Search API
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": f"{query} near {location}",
            "key": GOOGLE_MAPS_API_KEY,
            "radius": DEFAULT_RADIUS
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            raise HTTPException(status_code=400, detail=f"Google Maps API Error: {data.get('error_message', 'Unknown error')}")
        
        places = data.get("results", [])[:MAX_RESULTS]
        
        if not places:
            return {
                "query": query,
                "location": location,
                "places": [],
                "count": 0,
                "message": f"No {query} found near {location}"
            }
        
        # Format places
        formatted_places = []
        for place in places:
            name = place.get("name", "Unknown")
            address = place.get("formatted_address", "Address not available")
            rating = place.get("rating")
            place_id = place.get("place_id")
            
            maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            directions_url = f"https://www.google.com/maps/dir/{quote(location)}/{quote(address)}"
            
            formatted_place = {
                "name": name,
                "address": address,
                "rating": rating,
                "place_id": place_id,
                "maps_url": maps_url,
                "directions_url": directions_url
            }
            formatted_places.append(formatted_place)
        
        # Generate embedded map URL
        search_query = quote(f"{query} near {location}")
        embed_url = f"https://www.google.com/maps/embed/v1/search?key={GOOGLE_MAPS_API_KEY}&q={search_query}&zoom=14"
        
        return {
            "query": query,
            "location": location,
            "places": formatted_places,
            "count": len(formatted_places),
            "embed_map_url": embed_url
        }
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/places/directions")
async def get_directions(
    origin: str = Query(..., description="Starting location"),
    destination: str = Query(..., description="Destination location"),
    mode: str = Query("driving", description="Travel mode (driving, walking, bicycling, transit)")
):
    """Get directions between two locations."""
    
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    try:
        # Google Directions API
        api_url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            raise HTTPException(status_code=400, detail=f"Directions API Error: {data.get('error_message', 'Could not find route')}")
        
        routes = data.get("routes", [])
        if not routes:
            raise HTTPException(status_code=404, detail="No route found between the locations")
        
        route = routes[0]
        leg = route["legs"][0]
        
        # Create Google Maps directions URL
        directions_url = f"https://www.google.com/maps/dir/{quote(origin)}/{quote(destination)}"
        if mode != "driving":
            mode_params = {
                "walking": "w",
                "bicycling": "b", 
                "transit": "r"
            }
            if mode in mode_params:
                directions_url += f"?dirflg={mode_params[mode]}"
        
        # Get first few steps
        steps = leg.get("steps", [])[:5]
        formatted_steps = []
        
        for step in steps:
            instruction = step.get("html_instructions", "")
            # Remove HTML tags
            import re
            instruction = re.sub(r'<[^>]+>', '', instruction)
            distance = step.get("distance", {}).get("text", "")
            formatted_steps.append({
                "instruction": instruction,
                "distance": distance
            })
        
        return {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "distance": leg['distance']['text'],
            "duration": leg['duration']['text'],
            "directions_url": directions_url,
            "steps": formatted_steps,
            "total_steps": len(leg.get("steps", []))
        }
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
Simple OpenWebUI Tool that calls Maps Backend API
"""

import requests
from typing import Optional

class Tools:
    def __init__(self):
        self.citation = True

    class Valves:
        BACKEND_API_URL: str = "http://maps-backend:8000"

    def __init__(self):
        self.valves = self.Valves()

    def get_user_location(self) -> str:
        """Get user's current location."""
        try:
            response = requests.get(f"{self.valves.BACKEND_API_URL}/location", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data["location"]
        except Exception as e:
            return f"❌ Error getting location: {str(e)}"

    async def find_nearby(self, query: str, location: str = "", __event_emitter__=None) -> str:
        """
        Find places nearby using the backend API.
        
        :param query: What to search for (e.g., "cafe", "restaurant", "gas station")
        :param location: Location to search near (optional, auto-detected if empty)
        :return: Formatted list of nearby places with embedded map
        """
        try:
            params = {"query": query}
            if location:
                params["location"] = location
            
            response = requests.get(
                f"{self.valves.BACKEND_API_URL}/places/nearby",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data["count"] == 0:
                return data["message"]
            
            # Format the response
            result = f"📍 **Found {data['count']} {data['query']} near {data['location']}**\n\n"
            
            for i, place in enumerate(data["places"], 1):
                result += f"**{i}. {place['name']}**\n"
                result += f"📍 {place['address']}\n"
                
                if place["rating"]:
                    stars = "⭐" * int(place["rating"])
                    result += f"⭐ Rating: {place['rating']}/5 {stars}\n"
                
                result += f"🗺️ [View on Maps]({place['maps_url']})\n"
                result += f"🧭 [Get Directions]({place['directions_url']})\n\n"
            
            # Embed map with proper sandbox permissions for Google Maps
            if __event_emitter__:
                await __event_emitter__({
                    "type": "message", 
                    "data": {"content": f'''```html
<iframe src="{data["embed_map_url"]}" width="100%" height="720" frameborder="0" allowfullscreen></iframe>
```\n'''}
                })
            return result
            
        except requests.RequestException as e:
            return f"❌ Network error: {str(e)}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
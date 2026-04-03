import requests
import json
from math import radians, sin, cos, sqrt, atan2, degrees
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPEN_API_KEY = os.getenv("OPEN_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_LAT = 48.2931
DEFAULT_LON = 25.9296
DEFAULT_RADIUS = 1000  # meters
DEFAULT_AMENITY = "restaurant"

def get_recommendation_from_ai(user_lat: float = DEFAULT_LAT, user_lon: float = DEFAULT_LON, purpose: str = DEFAULT_AMENITY, radius: int = DEFAULT_RADIUS) -> str:
    raw_data = get_locations(user_lat, user_lon, radius, purpose)
    locations = parse_lcoations(raw_data) 
    
    if not locations:
        return f"I couldn't find any {purpose}s within {radius} meters of your location."

    enriched_list = []
    for loc in locations:
        dist = haversine_distance(user_lat, user_lon, loc['latitude'], loc['longitude'])
        bearing = calculate_bearing(user_lat, user_lon, loc['latitude'], loc['longitude'])
        direction = bearing_to_direction(bearing)
        
        enriched_list.append({
            "name": loc['name'],
            "distance_meters": round(dist),
            "direction": direction,
            "cuisine": loc['tags'].get("cuisine", "N/A"),
            "website": loc['website']
        })

    prompt = f"""
    You are a helpful City Assistant. A user is looking for a '{purpose}'.
    User's current coordinates: {user_lat}, {user_lon}.
    
    Here is a list of real places found nearby:
    {json.dumps(enriched_list, indent=2)}
    
    Please analyze these options and give a friendly recommendation. 
    Mention the distance (in meters) and the direction for the top 2-3 options. 
    If a place has a website, mention it. Be concise.
    """

    response = client.chat.completions.create(
        model="gpt-4o", # or "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are a helpful city guide."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content

def get_locations(lat: float, lon: float, radius: int, amenity: str) -> dict:
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="{amenity}"](around:{radius},{lat},{lon});
      way["amenity"="{amenity}"](around:{radius},{lat},{lon});
    );
    out center;
    """

    url = "https://overpass-api.de/api/interpreter"

    response = requests.post(
        url,
        data=overpass_query,
        headers={"Content-Type": "text/plain"}
    )

    response.raise_for_status()
    return response.json()

def parse_lcoations(data: dict) -> list:
    locations = []
    for element in data.get("elements", []):
        if "tags" in element:
            tags = element.get("tags", {})
            name = element["tags"].get("name", "Unnamed")
            website = tags.get("website") or tags.get("contact:website")

            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")
            locations.append({
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "website": website,
                "tags": tags
            })
    return locations

def reverse_geocode(location: dict) -> dict:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": location["latitude"],
        "lon": location["longitude"],
        "format": "jsonv2",
        "addressdetails": 1
    }

    headers = {
        "User-Agent": "geo-demo-app (va.melnyk@chnu.edu.ua)"
    }

    r = requests.get(url, params=params, headers=headers, timeout=10)
    r.raise_for_status()

    data = r.json()
    address = data.get("address", {})

    location["street"] = address.get("road")
    location["house_number"] = address.get("house_number")
    location["city"] = address.get("city") or address.get("town")
    location["address"] = data.get("display_name")
    return location

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    dlon = radians(lon2 - lon1)

    x = sin(dlon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)

    bearing = (degrees(atan2(x, y)) + 360) % 360
    return bearing

def bearing_to_direction(bearing):
    directions = [
        "north",
        "north-east",
        "east",
        "south-east",
        "south",
        "south-west",
        "west",
        "north-west"
    ]

    index = round(bearing / 45) % 8
    return directions[index]
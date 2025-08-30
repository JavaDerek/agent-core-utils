import re
from typing import Any, Optional

from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from ..services import initialize_llm_client
from .google_places import get_bounding_box

_LOCATION_PROMPT = (
    "Extract the city, state or province, and country from the user's request. "
    "Respond with the location only, or 'None' if no location is mentioned."
)

def _create_geolocator() -> Nominatim:
    """Return a ``Nominatim`` geocoder with the required user-agent."""
    return Nominatim(user_agent="roswell-agent", timeout=10)

def _safe_geocode(geolocator: Any, location: str | None) -> tuple[float, float] | None:
    """Return ``(lat, lon)`` for ``location`` or ``None`` on failure."""
    if not location:
        return None
    try:
        geo = geolocator.geocode(location)
        if geo:
            return geo.latitude, geo.longitude
    except Exception:
        return None
    return None

def _bounding_box(
    lat: float, lon: float, radius_miles: float = 25
) -> tuple[float, float, float, float]:
    """Return (south, north, west, east) bounds around ``lat, lon``."""
    north = geodesic(miles=radius_miles).destination((lat, lon), 0).latitude
    south = geodesic(miles=radius_miles).destination((lat, lon), 180).latitude
    east = geodesic(miles=radius_miles).destination((lat, lon), 90).longitude
    west = geodesic(miles=radius_miles).destination((lat, lon), 270).longitude
    return south, north, west, east

def extract_location_with_llm(
    text: str, *, llm_client: ChatOpenAI | None = None
) -> Optional[str]:
    """Return the location mentioned in ``text`` using the LLM."""
    client = llm_client or initialize_llm_client()
    prompt = f"{_LOCATION_PROMPT}\nRequest: {text}\nLocation:"
    try:
        reply = client.invoke([HumanMessage(content=prompt)])
    except Exception:
        return None
    location = reply.content.strip()
    if location.lower() == "none":
        return None
    # Remove extraneous punctuation or whitespace
    location = re.sub(r"[\n\r]", " ", location).strip()
    return location or None

def address_in_region(
    address: str, region: str, *, geolocator: Any | None = None
) -> bool:
    """Return ``True`` if ``address`` lies within ``region`` using bounding boxes."""
    geolocator = geolocator or _create_geolocator()
    addr_geo = _safe_geocode(geolocator, address)
    if not addr_geo:
        return False
    lat, lon = addr_geo
    try:
        bbox = get_bounding_box(region)
    except Exception:
        bbox = None
    if not bbox:
        region_geo = _safe_geocode(geolocator, region)
        if not region_geo:
            return False
        south, north, west, east = _bounding_box(*region_geo)
    else:
        south, north, west, east = bbox
    return south <= lat <= north and west <= lon <= east

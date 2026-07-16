"""Place geocoding helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim


@lru_cache(maxsize=256)
def geocode_place(place: str) -> dict[str, Any]:
    """Resolve place name to lat/lon. Raises ValueError if not found."""
    geolocator = Nominatim(user_agent="vedicastro-app/1.0")
    try:
        location = geolocator.geocode(place, exactly_one=True, timeout=10)
    except (GeocoderTimedOut, GeocoderServiceError) as exc:
        raise ValueError(f"Geocoding failed: {exc}") from exc
    if location is None:
        raise ValueError(f"Could not find location: {place}")
    return {
        "place": location.address,
        "latitude": float(location.latitude),
        "longitude": float(location.longitude),
    }


def estimate_timezone_offset(longitude: float, place: str = "") -> float:
    """Estimate TZ offset in hours.

    Longitude/15 rounded to half-hours is often wrong for India (gives +5.0
    instead of IST +5.5). A 30-minute birth-time error moves the Moon enough
    to shift Vimshottari dates by several months. Prefer an explicit offset.
    """
    text = (place or "").lower()
    if "india" in text or "bharat" in text:
        return 5.5
    if "bangladesh" in text:
        return 6.0
    if "nepal" in text:
        return 5.75
    if "pakistan" in text:
        return 5.0
    if "sri lanka" in text:
        return 5.5

    # Nearest 15 minutes (better than half-hour for generic longitudes)
    return round((longitude / 15.0) * 4) / 4

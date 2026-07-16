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


def estimate_timezone_offset(longitude: float) -> float:
    """Rough timezone offset from longitude (15° ≈ 1 hour). Prefer user override later."""
    return round(longitude / 15.0 * 2) / 2  # nearest half-hour

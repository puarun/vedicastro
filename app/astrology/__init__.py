"""Shared Vedic astrology constants and helpers."""

from __future__ import annotations

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGNS_SA = [
    "Mesha",
    "Vrishabha",
    "Mithuna",
    "Karka",
    "Simha",
    "Kanya",
    "Tula",
    "Vrishchika",
    "Dhanu",
    "Makara",
    "Kumbha",
    "Meena",
]

PLANETS = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
]

# Swiss Ephemeris planet IDs.
# Mean Node for Rahu (SE_MEAN_NODE=10): traditional Jyotish / DrikPanchang default.
# True Node (11) oscillates up to ~1.5–1.9° around the mean and can place Rahu/Ketu
# in the previous sign (and whole-sign house) near boundaries.
SWE_IDS = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
    "Rahu": 10,  # mean node
}

RAHU_NODE_TYPE = "mean"

NAKSHATRAS = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

NAKSHATRA_LORDS = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
] * 3

VIMSHOTTARI_ORDER = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
]

VIMSHOTTARI_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

NAKSHATRA_SPAN = 360.0 / 27.0  # 13°20'


def lon_to_sign(lon: float) -> tuple[int, str, str, float]:
    """Return (sign_index, english, sanskrit, deg_in_sign)."""
    lon = lon % 360.0
    idx = int(lon // 30)
    return idx, SIGNS[idx], SIGNS_SA[idx], lon % 30.0


def lon_to_nakshatra(lon: float) -> tuple[int, str, str, float]:
    """Return (index, name, lord, fraction through nakshatra 0-1)."""
    lon = lon % 360.0
    idx = int(lon // NAKSHATRA_SPAN) % 27
    frac = (lon % NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    return idx, NAKSHATRAS[idx], NAKSHATRA_LORDS[idx], frac


def house_from_asc(planet_lon: float, asc_lon: float) -> int:
    """Whole-sign house number 1-12 from Ascendant."""
    p_sign = int((planet_lon % 360) // 30)
    a_sign = int((asc_lon % 360) // 30)
    return ((p_sign - a_sign) % 12) + 1

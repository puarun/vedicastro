"""Birth chart and varga (D1, D9, D10) calculations using Swiss Ephemeris."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import swisseph as swe

from app.astrology import (
    PLANETS,
    RAHU_NODE_TYPE,
    SWE_IDS,
    house_from_asc,
    lon_to_nakshatra,
    lon_to_sign,
)

# Bundled Swiss Ephemeris files (sepl/semo/seas). Without these, pyswisseph
# silently falls back to the lower-precision Moshier ephemeris.
_EPHE_DIR = Path(__file__).resolve().parents[1] / "ephe"
if _EPHE_DIR.is_dir():
    swe.set_ephe_path(str(_EPHE_DIR))

# Lahiri ayanamsa
swe.set_sid_mode(swe.SIDM_LAHIRI)


def _jd_ut(dt_utc: datetime) -> float:
    """Julian Day UT from a naive or aware UTC datetime."""
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    # utc_to_jd accounts for leap seconds when converting civil UTC → UT.
    try:
        _jd_et, jd_ut = swe.utc_to_jd(
            dt_utc.year,
            dt_utc.month,
            dt_utc.day,
            dt_utc.hour,
            dt_utc.minute,
            float(dt_utc.second) + dt_utc.microsecond / 1e6,
            swe.GREG_CAL,
        )
        return jd_ut
    except Exception:
        return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)


def local_to_utc(date_str: str, time_str: str, tz_offset_hours: float) -> datetime:
    hour, minute = map(int, time_str.split(":")[:2])
    year, month, day = map(int, date_str.split("-"))
    local = datetime(year, month, day, hour, minute, tzinfo=timezone(timedelta(hours=tz_offset_hours)))
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def _planet_sidereal_lon(jd: float, planet: str) -> float:
    if planet == "Ketu":
        rahu_lon = _planet_sidereal_lon(jd, "Rahu")
        return (rahu_lon + 180.0) % 360.0
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    result, _ = swe.calc_ut(jd, SWE_IDS[planet], flags)
    return result[0] % 360.0


def _ascendant_sidereal(jd: float, lat: float, lon: float) -> float:
    """Sidereal ascendant (Lahiri) for whole-sign houses."""
    flags = swe.FLG_SIDEREAL
    try:
        _cusps, ascmc = swe.houses_ex(jd, lat, lon, b"P", flags)
        return ascmc[0] % 360.0
    except Exception:
        # Fallback: tropical Asc minus ayanamsa (equivalent for the Asc degree).
        _cusps, ascmc = swe.houses(jd, lat, lon, b"P")
        return (ascmc[0] - swe.get_ayanamsa_ut(jd)) % 360.0


def navamsa_sign(lon: float) -> int:
    """D9 sign index 0-11 from sidereal longitude."""
    lon = lon % 360.0
    sign = int(lon // 30)
    pos_in_sign = lon % 30.0
    pada = int(pos_in_sign // (30.0 / 9.0))  # 0-8
    # Movable signs start from themselves; fixed from 9th; dual from 5th
    if sign % 3 == 0:  # movable
        start = sign
    elif sign % 3 == 1:  # fixed
        start = (sign + 8) % 12
    else:  # dual
        start = (sign + 4) % 12
    return (start + pada) % 12


def dasamsa_sign(lon: float) -> int:
    """D10 sign index 0-11 from sidereal longitude."""
    lon = lon % 360.0
    sign = int(lon // 30)
    pos_in_sign = lon % 30.0
    part = int(pos_in_sign // 3.0)  # 0-9
    # Odd signs: count from same sign; even: from 9th
    if sign % 2 == 0:  # odd signs in 1-indexed (Aries=0 even? Aries is odd in Jyotish 1-index)
        # Jyotish: odd signs = Aries(1), Gemini(3)... → index 0,2,4...
        # Standard: for odd rasis start from same; even from 9th
        pass
    # Using 0-indexed: odd rasi numbers are even indices (0,2,4...)
    if sign % 2 == 0:  # odd signs (Mesha, Mithuna, ...)
        start = sign
    else:
        start = (sign + 8) % 12
    return (start + part) % 12


def _format_body(name: str, lon: float, asc_lon: float) -> dict[str, Any]:
    s_idx, s_en, s_sa, deg = lon_to_sign(lon)
    n_idx, n_name, n_lord, n_frac = lon_to_nakshatra(lon)
    return {
        "planet": name,
        "longitude": round(lon, 4),
        "sign": s_en,
        "sign_sa": s_sa,
        "sign_index": s_idx,
        "degree": round(deg, 2),
        "house": house_from_asc(lon, asc_lon),
        "nakshatra": n_name,
        "nakshatra_lord": n_lord,
        "nakshatra_pada": int(n_frac * 4) + 1,
    }


def _varga_body(name: str, d1_lon: float, varga_sign: int, varga_asc_sign: int) -> dict[str, Any]:
    from app.astrology import SIGNS, SIGNS_SA

    house = ((varga_sign - varga_asc_sign) % 12) + 1
    return {
        "planet": name,
        "sign": SIGNS[varga_sign],
        "sign_sa": SIGNS_SA[varga_sign],
        "sign_index": varga_sign,
        "house": house,
    }


def compute_charts(
    date_str: str,
    time_str: str,
    latitude: float,
    longitude: float,
    tz_offset_hours: float,
) -> dict[str, Any]:
    """Compute D1, D9, D10 charts for a birth moment."""
    dt_utc = local_to_utc(date_str, time_str, tz_offset_hours)
    jd = _jd_ut(dt_utc)

    asc_lon = _ascendant_sidereal(jd, latitude, longitude)
    ayanamsa = swe.get_ayanamsa_ut(jd)

    positions: dict[str, float] = {}
    for p in PLANETS:
        positions[p] = _planet_sidereal_lon(jd, p)

    d1_planets = [_format_body(p, positions[p], asc_lon) for p in PLANETS]
    d1_asc = _format_body("Ascendant", asc_lon, asc_lon)
    d1_asc.pop("planet")
    d1_asc["label"] = "Ascendant"

    # D9
    d9_asc_sign = navamsa_sign(asc_lon)
    d9_planets = [
        _varga_body(p, positions[p], navamsa_sign(positions[p]), d9_asc_sign) for p in PLANETS
    ]

    # D10
    d10_asc_sign = dasamsa_sign(asc_lon)
    d10_planets = [
        _varga_body(p, positions[p], dasamsa_sign(positions[p]), d10_asc_sign) for p in PLANETS
    ]

    from app.astrology import SIGNS, SIGNS_SA

    moon = next(x for x in d1_planets if x["planet"] == "Moon")

    return {
        "datetime_utc": dt_utc.isoformat(timespec="minutes"),
        "julian_day": jd,
        "ayanamsa": round(ayanamsa, 4),
        "ayanamsa_name": "Lahiri",
        "house_system": "Whole sign",
        "rahu_node_type": RAHU_NODE_TYPE,
        "d1": {
            "ascendant": d1_asc,
            "planets": d1_planets,
        },
        "d9": {
            "ascendant_sign": SIGNS[d9_asc_sign],
            "ascendant_sign_sa": SIGNS_SA[d9_asc_sign],
            "planets": d9_planets,
        },
        "d10": {
            "ascendant_sign": SIGNS[d10_asc_sign],
            "ascendant_sign_sa": SIGNS_SA[d10_asc_sign],
            "planets": d10_planets,
        },
        "moon_nakshatra": moon["nakshatra"],
        "moon_nakshatra_lord": moon["nakshatra_lord"],
    }

"""Gochar (transit) calculations — current and upcoming."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import swisseph as swe

from app.astrology import PLANETS, RAHU_NODE_TYPE, house_from_asc, lon_to_nakshatra, lon_to_sign
from app.astrology.charts import _ascendant_sidereal, _jd_ut, _planet_sidereal_lon

# charts.py already configures ephemeris path + Lahiri; keep mode sticky here too.
swe.set_sid_mode(swe.SIDM_LAHIRI)

# Approximate synodic / orbital periods (days) for "next sign change" estimates
SIGN_CHANGE_DAYS = {
    "Moon": 2.5,
    "Sun": 30,
    "Mercury": 25,
    "Venus": 30,
    "Mars": 45,
    "Jupiter": 360,
    "Saturn": 800,
    "Rahu": 550,
    "Ketu": 550,
}


def _format_transit(name: str, lon: float, natal_asc: float | None = None) -> dict[str, Any]:
    s_idx, s_en, s_sa, deg = lon_to_sign(lon)
    _, n_name, n_lord, n_frac = lon_to_nakshatra(lon)
    row: dict[str, Any] = {
        "planet": name,
        "longitude": round(lon, 4),
        "sign": s_en,
        "sign_sa": s_sa,
        "degree": round(deg, 2),
        "nakshatra": n_name,
        "nakshatra_lord": n_lord,
        "nakshatra_pada": int(n_frac * 4) + 1,
    }
    if natal_asc is not None:
        row["house_from_natal_asc"] = house_from_asc(lon, natal_asc)
    return row


def current_gochar(
    latitude: float = 0.0,
    longitude: float = 0.0,
    natal_asc_lon: float | None = None,
    when: datetime | None = None,
) -> dict[str, Any]:
    """Current sidereal planetary positions (gochar)."""
    when = when or datetime.utcnow()
    jd = _jd_ut(when)
    positions = {p: _planet_sidereal_lon(jd, p) for p in PLANETS}
    asc = _ascendant_sidereal(jd, latitude, longitude) if latitude or longitude else None

    return {
        "when_utc": when.isoformat(timespec="minutes"),
        "ayanamsa": round(swe.get_ayanamsa_ut(jd), 4),
        "rahu_node_type": RAHU_NODE_TYPE,
        "ascendant": _format_transit("Ascendant", asc) if asc is not None else None,
        "planets": [_format_transit(p, positions[p], natal_asc_lon) for p in PLANETS],
    }


def upcoming_sign_changes(
    days_ahead: int = 90,
    natal_asc_lon: float | None = None,
) -> list[dict[str, Any]]:
    """Find upcoming sign ingresses for each planet within the window."""
    start = datetime.utcnow()
    events: list[dict[str, Any]] = []

    for planet in PLANETS:
        lon0 = _planet_sidereal_lon(_jd_ut(start), planet)
        sign0 = int((lon0 % 360) // 30)
        # Step through days looking for sign change
        step = max(1, int(SIGN_CHANGE_DAYS.get(planet, 30) / 10))
        prev_sign = sign0
        prev_lon = lon0
        t = start
        end = start + timedelta(days=days_ahead)
        while t <= end:
            t += timedelta(days=step)
            lon = _planet_sidereal_lon(_jd_ut(t), planet)
            sign = int((lon % 360) // 30)
            # Detect wrap for retrograde / forward
            if sign != prev_sign:
                # Refine with binary search
                lo, hi = t - timedelta(days=step), t
                for _ in range(16):
                    mid = lo + (hi - lo) / 2
                    m_lon = _planet_sidereal_lon(_jd_ut(mid), planet)
                    m_sign = int((m_lon % 360) // 30)
                    if m_sign == prev_sign:
                        lo = mid
                    else:
                        hi = mid
                ingress = hi
                new_lon = _planet_sidereal_lon(_jd_ut(ingress), planet)
                _, s_en, s_sa, _ = lon_to_sign(new_lon)
                events.append(
                    {
                        "planet": planet,
                        "date": ingress.strftime("%Y-%m-%d"),
                        "into_sign": s_en,
                        "into_sign_sa": s_sa,
                        "from_sign": lon_to_sign(prev_lon)[1],
                        "house_from_natal_asc": (
                            house_from_asc(new_lon, natal_asc_lon) if natal_asc_lon is not None else None
                        ),
                    }
                )
                prev_sign = int((new_lon % 360) // 30)
            prev_lon = lon

    events.sort(key=lambda e: e["date"])
    return events


def gochar_summary(natal_asc_lon: float | None = None, lat: float = 0.0, lon: float = 0.0) -> dict[str, Any]:
    current = current_gochar(lat, lon, natal_asc_lon)
    upcoming = upcoming_sign_changes(90, natal_asc_lon)
    return {"current": current, "upcoming": upcoming}

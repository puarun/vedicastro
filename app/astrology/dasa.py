"""Vimshottari Mahadasa and Antardasa calculations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.astrology import VIMSHOTTARI_ORDER, VIMSHOTTARI_YEARS, lon_to_nakshatra
from app.astrology.charts import local_to_utc, _jd_ut, _planet_sidereal_lon


DAYS_PER_YEAR = 365.2425


def _add_years(start: datetime, years: float) -> datetime:
    return start + timedelta(days=years * DAYS_PER_YEAR)


def compute_dasa(
    date_str: str,
    time_str: str,
    tz_offset_hours: float,
    until_years: float = 120.0,
) -> dict[str, Any]:
    """Build mahadasa and antardasa tables from birth Moon nakshatra."""
    dt_utc = local_to_utc(date_str, time_str, tz_offset_hours)
    # Use local civil datetime for display anchors
    hour, minute = map(int, time_str.split(":")[:2])
    year, month, day = map(int, date_str.split("-"))
    birth_local = datetime(year, month, day, hour, minute)

    jd = _jd_ut(dt_utc)
    moon_lon = _planet_sidereal_lon(jd, "Moon")
    _, nak_name, lord, frac = lon_to_nakshatra(moon_lon)

    # Balance of first mahadasa remaining at birth
    first_full_years = VIMSHOTTARI_YEARS[lord]
    balance_years = first_full_years * (1.0 - frac)

    start_idx = VIMSHOTTARI_ORDER.index(lord)
    cursor = birth_local
    end_limit = _add_years(birth_local, until_years)

    mahadasas: list[dict[str, Any]] = []
    antardasas: list[dict[str, Any]] = []

    # First (partial) mahadasa
    maha_end = _add_years(cursor, balance_years)
    mahadasas.append(
        {
            "lord": lord,
            "start": cursor.strftime("%Y-%m-%d"),
            "end": maha_end.strftime("%Y-%m-%d"),
            "years": round(balance_years, 3),
            "partial": True,
        }
    )
    _append_antardasas(antardasas, lord, cursor, balance_years, first_full_years)
    cursor = maha_end

    order_i = 1
    while cursor < end_limit:
        lord_i = VIMSHOTTARI_ORDER[(start_idx + order_i) % 9]
        years = VIMSHOTTARI_YEARS[lord_i]
        maha_end = _add_years(cursor, years)
        mahadasas.append(
            {
                "lord": lord_i,
                "start": cursor.strftime("%Y-%m-%d"),
                "end": maha_end.strftime("%Y-%m-%d"),
                "years": years,
                "partial": False,
            }
        )
        _append_antardasas(antardasas, lord_i, cursor, years, years)
        cursor = maha_end
        order_i += 1
        if order_i > 20:  # safety
            break

    now = datetime.utcnow()
    current_maha = None
    current_antar = None
    for m in mahadasas:
        if m["start"] <= now.strftime("%Y-%m-%d") <= m["end"]:
            current_maha = m
            break
    for a in antardasas:
        if a["start"] <= now.strftime("%Y-%m-%d") <= a["end"]:
            current_antar = a
            break

    return {
        "moon_nakshatra": nak_name,
        "starting_lord": lord,
        "balance_years_at_birth": round(balance_years, 4),
        "mahadasas": mahadasas,
        "antardasas": antardasas,
        "current_mahadasa": current_maha,
        "current_antardasa": current_antar,
    }


def _append_antardasas(
    out: list[dict[str, Any]],
    maha_lord: str,
    maha_start: datetime,
    maha_span_years: float,
    maha_full_years: float,
) -> None:
    """Proportionally fill antardasas within a mahadasa span."""
    start_idx = VIMSHOTTARI_ORDER.index(maha_lord)
    # Ideal antardasa lengths sum to maha_full_years
    ideal = []
    for i in range(9):
        antar_lord = VIMSHOTTARI_ORDER[(start_idx + i) % 9]
        portion = (VIMSHOTTARI_YEARS[antar_lord] * maha_full_years) / 120.0
        ideal.append((antar_lord, portion))

    # Scale to actual span (handles partial first mahadasa)
    scale = maha_span_years / maha_full_years if maha_full_years else 1.0
    cursor = maha_start
    for antar_lord, portion in ideal:
        years = portion * scale
        end = _add_years(cursor, years)
        out.append(
            {
                "maha_lord": maha_lord,
                "antar_lord": antar_lord,
                "start": cursor.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d"),
                "years": round(years, 4),
            }
        )
        cursor = end

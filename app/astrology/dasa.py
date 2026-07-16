"""Vimshottari Mahadasa and Antardasa calculations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.astrology import VIMSHOTTARI_ORDER, VIMSHOTTARI_YEARS, lon_to_nakshatra
from app.astrology.charts import local_to_utc, _jd_ut, _planet_sidereal_lon

# Traditional Vimshottari uses 360-day (savana) years.
# Using 365.25 drifts ~5.25 days per year (~6 months by mid-30s) vs most Indian software.
DAYS_PER_YEAR = 360.0


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
    hour, minute = map(int, time_str.split(":")[:2])
    year, month, day = map(int, date_str.split("-"))
    birth_local = datetime(year, month, day, hour, minute)

    jd = _jd_ut(dt_utc)
    moon_lon = _planet_sidereal_lon(jd, "Moon")
    _, nak_name, lord, frac = lon_to_nakshatra(moon_lon)

    # Elapsed fraction of the birth nakshatra → elapsed mahadasa years already used up
    first_full_years = VIMSHOTTARI_YEARS[lord]
    elapsed_years = first_full_years * frac
    balance_years = first_full_years - elapsed_years

    start_idx = VIMSHOTTARI_ORDER.index(lord)
    cursor = birth_local
    end_limit = _add_years(birth_local, until_years)

    mahadasas: list[dict[str, Any]] = []
    antardasas: list[dict[str, Any]] = []

    # First (partial) mahadasa — remaining balance only
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
    _append_antardasas(
        antardasas,
        lord,
        cursor,
        maha_span_years=balance_years,
        maha_full_years=first_full_years,
        elapsed_years_at_start=elapsed_years,
    )
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
        _append_antardasas(
            antardasas,
            lord_i,
            cursor,
            maha_span_years=years,
            maha_full_years=years,
            elapsed_years_at_start=0.0,
        )
        cursor = maha_end
        order_i += 1
        if order_i > 20:
            break

    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    current_maha = next((m for m in mahadasas if m["start"] <= today <= m["end"]), None)
    current_antar = next((a for a in antardasas if a["start"] <= today <= a["end"]), None)

    return {
        "moon_nakshatra": nak_name,
        "moon_longitude": round(moon_lon, 4),
        "starting_lord": lord,
        "elapsed_years_at_birth": round(elapsed_years, 4),
        "balance_years_at_birth": round(balance_years, 4),
        "year_length_days": DAYS_PER_YEAR,
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
    elapsed_years_at_start: float = 0.0,
) -> None:
    """Append antardasas for a mahadasa.

    For a partial first mahadasa, pass how many mahadasa-years were already elapsed
    at birth. We skip that elapsed portion of the natural antardasa sequence instead
    of compressing all nine antardasas into the remaining balance.
    """
    start_idx = VIMSHOTTARI_ORDER.index(maha_lord)
    portions: list[tuple[str, float]] = []
    for i in range(9):
        antar_lord = VIMSHOTTARI_ORDER[(start_idx + i) % 9]
        portion = (VIMSHOTTARI_YEARS[antar_lord] * maha_full_years) / 120.0
        portions.append((antar_lord, portion))

    skip = max(0.0, elapsed_years_at_start)
    cursor = maha_start
    remaining_span = maha_span_years

    for antar_lord, portion in portions:
        if remaining_span <= 1e-12:
            break
        if skip >= portion - 1e-12:
            skip -= portion
            continue

        # If birth falls mid-antardasa, only the leftover of that antardasa remains.
        usable = portion - skip
        skip = 0.0
        years = min(usable, remaining_span)
        if years <= 1e-12:
            break
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
        remaining_span -= years

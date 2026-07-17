"""Vimshottari year-length and balance regressions vs mainstream Indian software."""

from __future__ import annotations

from datetime import datetime

from app.astrology.dasa import DAYS_PER_YEAR, compute_dasa


def test_uses_solar_365_25_not_savana_360():
    """DrikPanchang / AstroSage / JHora default use 365.25d years, not 360."""
    assert DAYS_PER_YEAR == 365.25


def test_coimbatore_1983_lahiri_matches_solar_year_boundaries():
    """1983-12-27 13:45 IST, Coimbatore — Hasta Moon balance → Jupiter maha.

    With correct Lahiri Moon + 365.25d years, full mahadasas land on the same
    calendar day of year (solar-year arithmetic). Savana 360 drifts Jupiter
    start from ~2012-07-24 to ~2012-02-25 (~5 months early by age ~28).
    """
    d = compute_dasa("1983-12-27", "13:45", 5.5)
    assert d["moon_nakshatra"] == "Hasta"
    assert d["starting_lord"] == "Moon"
    assert abs(d["balance_years_at_birth"] - 3.5738) < 0.01

    # First cycle only (lords repeat after 120y — do not key by lord name).
    moon, mars, rahu, jupiter = d["mahadasas"][:4]
    assert moon["lord"] == "Moon" and moon["end"] == "1987-07-24"
    assert mars["lord"] == "Mars" and mars["start"] == "1987-07-24" and mars["end"] == "1994-07-24"
    assert rahu["lord"] == "Rahu" and rahu["end"] == "2012-07-24"
    assert jupiter["lord"] == "Jupiter" and jupiter["start"] == "2012-07-24"
    assert jupiter["end"] == "2028-07-24"


def test_savana_360_would_drift_months_by_midlife():
    """Document why 360 must not return: ~5.25d/year compounds to months."""
    birth = datetime(1983, 12, 27)
    now = datetime(2026, 7, 17)
    age_years = (now - birth).days / 365.25
    drift_days = age_years * (365.25 - 360.0)
    assert drift_days > 150  # >5 months by mid-40s

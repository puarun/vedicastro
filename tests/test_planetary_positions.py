"""Validate sidereal positions, mean-node Rahu, and whole-sign houses."""

from __future__ import annotations

import swisseph as swe

from app.astrology import SWE_IDS, house_from_asc
from app.astrology.charts import compute_charts, _ensure_swe_ready, _jd_ut, _planet_sidereal_lon, local_to_utc


# DrikPanchang Lahiri / mean-node reference: 1990-07-04 10:12 IST, New Delhi.
# https://www.drikpanchang.com/planet/position/planetary-positions-sidereal.html
DRIK_1990_07_04 = {
    "Sun": 78.23,
    "Moon": 215.33,
    "Mars": 0.51,
    "Mercury": 80.02,
    "Jupiter": 86.28,
    "Venus": 47.17,
    "Saturn": 269.06,
    "Rahu": 284.97,
    "Ketu": 104.97,
}


def test_rahu_uses_mean_node():
    assert SWE_IDS["Rahu"] == swe.MEAN_NODE == 10


def test_ephemeris_files_loaded():
    """Bundled SE files should be used (not silent Moshier fallback)."""
    _ensure_swe_ready()
    dt = local_to_utc("1990-07-04", "10:12", 5.5)
    jd = _jd_ut(dt)
    _xx, retflag = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    assert retflag & swe.FLG_SWIEPH, f"expected Swiss Ephemeris flag, got {retflag}"
    assert not (retflag & swe.FLG_MOSEPH), f"should not fall back to Moshier, got {retflag}"


def test_matches_drikpanchang_lahiri_within_arcminutes():
    """All grahas should match DrikPanchang Lahiri to ~0.02° (not ~1°)."""
    charts = compute_charts("1990-07-04", "10:12", 28.6139, 77.2090, 5.5)
    assert charts["ayanamsa_name"] == "Lahiri"
    assert abs(charts["ayanamsa"] - 23.7245) < 0.01

    by_name = {p["planet"]: p for p in charts["d1"]["planets"]}
    for planet, expected in DRIK_1990_07_04.items():
        got = by_name[planet]["longitude"]
        delta = abs(((got - expected + 180) % 360) - 180)
        assert delta < 0.02, f"{planet}: app={got:.4f} drik={expected} delta={delta:.4f}"


def test_not_fagan_bradley_one_degree_offset():
    """Fagan/Bradley (SE default) is ~0.9° from Lahiri — the classic 1° miss."""
    charts = compute_charts("1990-07-04", "10:12", 28.6139, 77.2090, 5.5)
    sun = next(p for p in charts["d1"]["planets"] if p["planet"] == "Sun")["longitude"]

    jd = charts["julian_day"]
    swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY)
    fagan_sun = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0] % 360
    # Restore Lahiri for other tests.
    _ensure_swe_ready()

    assert abs(((sun - fagan_sun + 180) % 360) - 180) > 0.7
    # App Sun must stay on Lahiri / Drik side, not Fagan.
    assert abs(((sun - DRIK_1990_07_04["Sun"] + 180) % 360) - 180) < 0.02


def test_lahiri_survives_swe_close_reset():
    """After swe.close(), SE falls back to Fagan/Bradley unless we re-init."""
    swe.close()
    # Default mode is Fagan — must not leak into compute_charts.
    charts = compute_charts("1990-07-04", "10:12", 28.6139, 77.2090, 5.5)
    sun = next(p for p in charts["d1"]["planets"] if p["planet"] == "Sun")["longitude"]
    assert abs(((sun - DRIK_1990_07_04["Sun"] + 180) % 360) - 180) < 0.02
    assert abs(charts["ayanamsa"] - 23.7245) < 0.01


def test_known_chart_lahiri_delhi():
    """Lahiri sidereal positions for 1990-07-04 10:12 IST, New Delhi."""
    charts = compute_charts("1990-07-04", "10:12", 28.6139, 77.2090, 5.5)
    assert charts["rahu_node_type"] == "mean"
    assert charts["ayanamsa_name"] == "Lahiri"

    by_name = {p["planet"]: p for p in charts["d1"]["planets"]}
    assert by_name["Sun"]["sign"] == "Gemini"
    assert abs(by_name["Sun"]["degree"] - 18.24) < 0.05
    assert by_name["Saturn"]["sign"] == "Sagittarius"
    assert by_name["Saturn"]["degree"] > 28.5
    assert charts["d1"]["ascendant"]["sign"] == "Leo"


def test_mean_vs_true_node_can_flip_sign_and_house():
    """True node can sit ~1.5–1.9° from mean and land in the previous sign/house."""
    jd = swe.julday(1952, 6, 24, 12.0)
    _ensure_swe_ready()
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    true_lon = swe.calc_ut(jd, swe.TRUE_NODE, flags)[0][0] % 360.0
    mean_lon = swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0] % 360.0

    assert int(true_lon // 30) != int(mean_lon // 30)
    assert abs(((true_lon - mean_lon + 180) % 360) - 180) > 1.0

    app_rahu = _planet_sidereal_lon(jd, "Rahu")
    assert abs(((app_rahu - mean_lon + 180) % 360) - 180) < 1e-6

    asc = 0.0
    assert house_from_asc(mean_lon, asc) != house_from_asc(true_lon, asc)
    assert house_from_asc(app_rahu, asc) == house_from_asc(mean_lon, asc)


def test_ketu_opposite_rahu():
    charts = compute_charts("1990-07-04", "10:12", 28.6139, 77.2090, 5.5)
    by_name = {p["planet"]: p for p in charts["d1"]["planets"]}
    sep = (by_name["Rahu"]["longitude"] - by_name["Ketu"]["longitude"]) % 360
    assert abs(sep - 180.0) < 1e-6

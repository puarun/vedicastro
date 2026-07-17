"""Validate sidereal positions, mean-node Rahu, and whole-sign houses."""

from __future__ import annotations

import swisseph as swe

from app.astrology import SWE_IDS, house_from_asc
from app.astrology.charts import compute_charts, _jd_ut, _planet_sidereal_lon, local_to_utc


def test_rahu_uses_mean_node():
    assert SWE_IDS["Rahu"] == swe.MEAN_NODE == 10


def test_ephemeris_files_loaded():
    """Bundled SE files should be used (not silent Moshier fallback)."""
    dt = local_to_utc("1990-07-04", "10:12", 5.5)
    jd = _jd_ut(dt)
    _xx, retflag = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    assert retflag & swe.FLG_SWIEPH, f"expected Swiss Ephemeris flag, got {retflag}"
    assert not (retflag & swe.FLG_MOSEPH), f"should not fall back to Moshier, got {retflag}"


def test_known_chart_lahiri_delhi():
    """Lahiri sidereal positions for 1990-07-04 10:12 IST, New Delhi."""
    charts = compute_charts("1990-07-04", "10:12", 28.6139, 77.2090, 5.5)
    assert charts["rahu_node_type"] == "mean"
    assert charts["ayanamsa_name"] == "Lahiri"
    assert abs(charts["ayanamsa"] - 23.7245) < 0.01

    by_name = {p["planet"]: p for p in charts["d1"]["planets"]}

    # Sun ~ Gemini 18.24° (tropical Cancer minus Lahiri)
    assert by_name["Sun"]["sign"] == "Gemini"
    assert abs(by_name["Sun"]["degree"] - 18.24) < 0.05

    # Saturn near Sagittarius end on this date
    assert by_name["Saturn"]["sign"] == "Sagittarius"
    assert by_name["Saturn"]["degree"] > 28.5

    # Ascendant Leo
    assert charts["d1"]["ascendant"]["sign"] == "Leo"


def test_mean_vs_true_node_can_flip_sign_and_house():
    """True node can sit ~1.5–1.9° from mean and land in the previous sign/house."""
    # 1952-06-24 12:00 UT — true Rahu in Capricorn, mean Rahu in Aquarius
    jd = swe.julday(1952, 6, 24, 12.0)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    true_lon = swe.calc_ut(jd, swe.TRUE_NODE, flags)[0][0] % 360.0
    mean_lon = swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0] % 360.0

    assert int(true_lon // 30) != int(mean_lon // 30)
    assert abs(((true_lon - mean_lon + 180) % 360) - 180) > 1.0

    # App Rahu must follow mean (not true) so it matches traditional tables.
    app_rahu = _planet_sidereal_lon(jd, "Rahu")
    assert abs(((app_rahu - mean_lon + 180) % 360) - 180) < 1e-6

    asc = 0.0  # Aries lagna for a simple whole-sign check
    assert house_from_asc(mean_lon, asc) != house_from_asc(true_lon, asc)
    assert house_from_asc(app_rahu, asc) == house_from_asc(mean_lon, asc)


def test_ketu_opposite_rahu():
    charts = compute_charts("1990-07-04", "10:12", 28.6139, 77.2090, 5.5)
    by_name = {p["planet"]: p for p in charts["d1"]["planets"]}
    sep = (by_name["Rahu"]["longitude"] - by_name["Ketu"]["longitude"]) % 360
    assert abs(sep - 180.0) < 1e-6

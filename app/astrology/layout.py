"""Chart layout helpers for South Indian and North Indian diagrams."""

from __future__ import annotations

from typing import Any

from app.astrology import SIGNS, SIGNS_SA

PLANET_ABBR = {
    "Sun": "Su",
    "Moon": "Mo",
    "Mars": "Ma",
    "Mercury": "Me",
    "Jupiter": "Ju",
    "Venus": "Ve",
    "Saturn": "Sa",
    "Rahu": "Ra",
    "Ketu": "Ke",
    "Ascendant": "As",
}

# South Indian fixed-sign grid (row, col) for sign index 0=Aries … 11=Pisces
SI_SIGN_CELL: dict[int, tuple[int, int]] = {
    11: (0, 0),  # Pisces
    0: (0, 1),  # Aries
    1: (0, 2),  # Taurus
    2: (0, 3),  # Gemini
    10: (1, 0),  # Aquarius
    3: (1, 3),  # Cancer
    9: (2, 0),  # Capricorn
    4: (2, 3),  # Leo
    8: (3, 0),  # Sagittarius
    7: (3, 1),  # Scorpio
    6: (3, 2),  # Libra
    5: (3, 3),  # Virgo
}

# North Indian house grid (row, col) for house 1..12 (Asc at top)
NI_HOUSE_CELL: dict[int, tuple[int, int]] = {
    1: (0, 1),
    2: (0, 2),
    3: (0, 3),
    4: (1, 3),
    5: (2, 3),
    6: (3, 3),
    7: (3, 2),
    8: (3, 1),
    9: (3, 0),
    10: (2, 0),
    11: (1, 0),
    12: (0, 0),
}


def _abbr(name: str) -> str:
    return PLANET_ABBR.get(name, name[:2])


def _sign_index_from_planet(p: dict[str, Any]) -> int | None:
    if "sign_index" in p and p["sign_index"] is not None:
        return int(p["sign_index"])
    sign = p.get("sign")
    if sign in SIGNS:
        return SIGNS.index(sign)
    return None


def prepare_varga_chart(
    title: str,
    planets: list[dict[str, Any]],
    asc_sign_index: int,
    asc_label: str | None = None,
) -> dict[str, Any]:
    """Build South (by sign) and North (by house) cell maps for a varga chart."""
    by_sign: dict[int, list[dict[str, str]]] = {i: [] for i in range(12)}
    for p in planets:
        idx = _sign_index_from_planet(p)
        if idx is None:
            continue
        entry = {
            "name": p["planet"],
            "abbr": _abbr(p["planet"]),
            "degree": p.get("degree"),
        }
        by_sign[idx].append(entry)

    # Ascendant marker in lagna sign
    by_sign[asc_sign_index].insert(
        0,
        {"name": "Ascendant", "abbr": "As", "degree": None},
    )

    south_cells: list[dict[str, Any]] = []
    for sign_i in range(12):
        r, c = SI_SIGN_CELL[sign_i]
        south_cells.append(
            {
                "row": r,
                "col": c,
                "sign_index": sign_i,
                "sign": SIGNS[sign_i],
                "sign_sa": SIGNS_SA[sign_i],
                "sign_short": SIGNS[sign_i][:2],
                "is_lagna": sign_i == asc_sign_index,
                "planets": by_sign[sign_i],
            }
        )

    north_cells: list[dict[str, Any]] = []
    for house in range(1, 13):
        sign_i = (asc_sign_index + house - 1) % 12
        r, c = NI_HOUSE_CELL[house]
        north_cells.append(
            {
                "row": r,
                "col": c,
                "house": house,
                "sign_index": sign_i,
                "sign": SIGNS[sign_i],
                "sign_sa": SIGNS_SA[sign_i],
                "sign_short": SIGNS[sign_i][:2],
                "is_lagna": house == 1,
                "planets": by_sign[sign_i],
            }
        )

    return {
        "title": title,
        "asc_sign": SIGNS[asc_sign_index],
        "asc_sign_sa": SIGNS_SA[asc_sign_index],
        "asc_label": asc_label,
        "south": south_cells,
        "north": north_cells,
    }


def charts_for_display(charts: dict[str, Any]) -> list[dict[str, Any]]:
    """Prepare D1/D9/D10 layout payloads for templates."""
    d1_asc = charts["d1"]["ascendant"]
    d1 = prepare_varga_chart(
        "D1 — Rasi",
        charts["d1"]["planets"],
        int(d1_asc["sign_index"]),
        asc_label=f"{d1_asc['sign']} {d1_asc['degree']}°",
    )
    d9_asc_sign = SIGNS.index(charts["d9"]["ascendant_sign"])
    d9 = prepare_varga_chart(
        "D9 — Navamsa",
        charts["d9"]["planets"],
        d9_asc_sign,
        asc_label=charts["d9"]["ascendant_sign"],
    )
    d10_asc_sign = SIGNS.index(charts["d10"]["ascendant_sign"])
    d10 = prepare_varga_chart(
        "D10 — Dasamsa",
        charts["d10"]["planets"],
        d10_asc_sign,
        asc_label=charts["d10"]["ascendant_sign"],
    )
    return [d1, d9, d10]

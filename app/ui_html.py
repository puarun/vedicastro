"""HTML helpers for Gradio chart / table rendering."""

from __future__ import annotations

from html import escape
from typing import Any

from app.astrology.layout import charts_for_display


CHART_CSS = """
<style>
.va-grid { display:grid; grid-template-columns:repeat(4,1fr); grid-template-rows:repeat(4,minmax(64px,auto));
  width:min(100%,420px); border:1px solid #444; background:#111; margin:0.5rem 0 1rem; }
.va-cell { border:1px solid #444; padding:4px; font-size:12px; min-height:64px; }
.va-cell.lagna { background:rgba(196,163,90,0.18); }
.va-sign { color:#aaa; font-size:10px; text-transform:uppercase; }
.va-chip { display:inline-block; margin:1px; padding:1px 4px; border:1px solid #555; border-radius:3px; font-weight:700; }
.va-chip.asc { background:#c4a35a; color:#111; border:none; }
.va-center { grid-row:2 / span 2; grid-column:2 / span 2; display:flex; align-items:center; justify-content:center;
  border:1px solid #444; color:#aaa; font-size:13px; text-align:center; }
.va-table { width:100%; border-collapse:collapse; font-size:13px; margin:0.5rem 0 1rem; }
.va-table th, .va-table td { border:1px solid #444; padding:6px 8px; text-align:left; vertical-align:top; }
.va-table th { color:#aaa; font-size:11px; text-transform:uppercase; }
.va-table tr.current { background:rgba(196,163,90,0.15); }
.va-muted { color:#999; }
.va-wrap { overflow-x:auto; }
</style>
"""


def _chips(planets: list[dict[str, Any]]) -> str:
    parts = []
    for p in planets:
        cls = "va-chip asc" if p.get("abbr") == "As" else "va-chip"
        title = escape(str(p.get("name", "")))
        parts.append(f'<span class="{cls}" title="{title}">{escape(p.get("abbr", "?"))}</span>')
    return "".join(parts)


def chart_html(chart: dict[str, Any], style: str = "south") -> str:
    cells = chart["south"] if style == "south" else chart["north"]
    label = "South Indian" if style == "south" else "North Indian"
    blocks = []
    for cell in cells:
        lagna = " lagna" if cell.get("is_lagna") else ""
        if style == "south":
            sign_line = escape(cell["sign_short"])
        else:
            sign_line = escape(f"H{cell['house']} · {cell['sign_short']}")
        blocks.append(
            f'<div class="va-cell{lagna}" style="grid-row:{cell["row"]+1};grid-column:{cell["col"]+1};">'
            f'<div class="va-sign">{sign_line}</div>'
            f'<div>{_chips(cell["planets"])}</div></div>'
        )
    title = escape(chart["title"])
    asc = escape(str(chart.get("asc_label") or chart.get("asc_sign")))
    return (
        f"{CHART_CSS}"
        f"<h3>{title}</h3>"
        f'<p class="va-muted">Lagna: {asc} · {label}</p>'
        f'<div class="va-grid">{"".join(blocks)}'
        f'<div class="va-center">{escape(chart["title"].split("—")[0].strip())}<br><small>{label}</small></div>'
        f"</div>"
    )


def all_charts_html(charts: dict[str, Any], style: str = "south") -> str:
    layouts = charts_for_display(charts)
    return "".join(chart_html(c, style) for c in layouts)


def planet_table_html(charts: dict[str, Any]) -> str:
    rows = []
    for p in charts["d1"]["planets"]:
        rows.append(
            "<tr>"
            f"<td>{escape(p['planet'])}</td>"
            f"<td>{escape(p['sign'])}</td>"
            f"<td>{p['degree']}°</td>"
            f"<td>{p['house']}</td>"
            f"<td>{escape(p['nakshatra'])}</td>"
            f"<td>{p['nakshatra_pada']}</td>"
            "</tr>"
        )
    return (
        f"{CHART_CSS}"
        "<h3>D1 details</h3>"
        '<div class="va-wrap"><table class="va-table">'
        "<thead><tr><th>Planet</th><th>Sign</th><th>Deg</th><th>House</th><th>Nakshatra</th><th>Pada</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def dasa_html(dasa: dict[str, Any]) -> str:
    cur_m = dasa.get("current_mahadasa") or {}
    cur_a = dasa.get("current_antardasa") or {}
    head = (
        f"<p><strong>Current Mahadasa:</strong> {escape(str(cur_m.get('lord', '—')))} "
        f"({escape(str(cur_m.get('start', '')))} → {escape(str(cur_m.get('end', '')))})</p>"
        f"<p><strong>Current Antardasa:</strong> {escape(str(cur_a.get('maha_lord', '')))}–"
        f"{escape(str(cur_a.get('antar_lord', '—')))} "
        f"({escape(str(cur_a.get('start', '')))} → {escape(str(cur_a.get('end', '')))})</p>"
        f"<p class=\"va-muted\">Birth Moon: {escape(str(dasa.get('moon_nakshatra', '')))} "
        f"(lord {escape(str(dasa.get('starting_lord', '')))}) · "
        f"balance at birth {dasa.get('balance_years_at_birth', '—')}y · "
        f"Vimshottari year = {dasa.get('year_length_days', 365.25)} days</p>"
        f"<p class=\"va-muted\">Tip: set TZ explicitly (e.g. 5.5 for IST). Dasa years use "
        f"solar 365.25-day length (DrikPanchang / AstroSage convention).</p>"
    )
    maha_rows = []
    for m in dasa.get("mahadasas", [])[:12]:
        cls = ' class="current"' if cur_m and m.get("start") == cur_m.get("start") else ""
        maha_rows.append(
            f"<tr{cls}><td>{escape(m['lord'])}</td><td>{escape(m['start'])}</td>"
            f"<td>{escape(m['end'])}</td><td>{m['years']}</td></tr>"
        )

    # antardasas for current maha
    antar_rows = []
    if cur_m:
        for a in dasa.get("antardasas", []):
            if a.get("maha_lord") != cur_m.get("lord"):
                continue
            if a.get("start", "") < cur_m.get("start", "") or a.get("end", "") > cur_m.get("end", "9999"):
                continue
            cls = (
                ' class="current"'
                if cur_a
                and a.get("start") == cur_a.get("start")
                and a.get("antar_lord") == cur_a.get("antar_lord")
                else ""
            )
            antar_rows.append(
                f"<tr{cls}><td>{escape(a['maha_lord'])}</td><td>{escape(a['antar_lord'])}</td>"
                f"<td>{escape(a['start'])}</td><td>{escape(a['end'])}</td><td>{a['years']}</td></tr>"
            )

    return (
        f"{CHART_CSS}{head}"
        "<h3>Mahadasa</h3>"
        '<div class="va-wrap"><table class="va-table">'
        "<thead><tr><th>Lord</th><th>Start</th><th>End</th><th>Years</th></tr></thead>"
        f"<tbody>{''.join(maha_rows)}</tbody></table></div>"
        "<h3>Antardasa (current mahadasa)</h3>"
        '<div class="va-wrap"><table class="va-table">'
        "<thead><tr><th>Maha</th><th>Antar</th><th>Start</th><th>End</th><th>Years</th></tr></thead>"
        f"<tbody>{''.join(antar_rows)}</tbody></table></div>"
    )


def gochar_html(gochar: dict[str, Any]) -> str:
    when = escape(str(gochar.get("current", {}).get("when_utc", "")))
    rows = []
    for p in gochar.get("current", {}).get("planets", []):
        rows.append(
            "<tr>"
            f"<td>{escape(p['planet'])}</td>"
            f"<td>{escape(p['sign'])}</td>"
            f"<td>{p['degree']}°</td>"
            f"<td>{p.get('house_from_natal_asc', '—')}</td>"
            f"<td>{escape(p.get('nakshatra', ''))}</td>"
            "</tr>"
        )
    up = []
    for e in gochar.get("upcoming", [])[:20]:
        up.append(
            "<tr>"
            f"<td>{escape(e['date'])}</td>"
            f"<td>{escape(e['planet'])}</td>"
            f"<td>{escape(e['from_sign'])}</td>"
            f"<td>{escape(e['into_sign'])}</td>"
            f"<td>{e.get('house_from_natal_asc') or '—'}</td>"
            "</tr>"
        )
    return (
        f"{CHART_CSS}"
        f'<p class="va-muted">As of {when} UTC</p>'
        "<h3>Current gochar</h3>"
        '<div class="va-wrap"><table class="va-table">'
        "<thead><tr><th>Planet</th><th>Sign</th><th>Deg</th><th>House</th><th>Nakshatra</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        "<h3>Upcoming sign changes (~90 days)</h3>"
        '<div class="va-wrap"><table class="va-table">'
        "<thead><tr><th>Date</th><th>Planet</th><th>From</th><th>Into</th><th>House</th></tr></thead>"
        f"<tbody>{''.join(up)}</tbody></table></div>"
    )

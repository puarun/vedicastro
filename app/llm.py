"""LLM client — Gemini (public demo) or Ollama (local-ai)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
import markdown as md

from app import config

QueryDomain = Literal["general", "relationship", "career", "auto"]


DOMAIN_HINTS = {
    "general": (
        "Primary focus: D1 (Rasi) for overall life themes, health, personality, and general timing. "
        "Still use D9/D10, dasa, and gochar when relevant."
    ),
    "relationship": (
        "Primary focus: D9 (Navamsa) for marriage, partnerships, and relationship strength. "
        "Also use D1 7th house / Venus / Jupiter, plus dasa and gochar."
    ),
    "career": (
        "Primary focus: D10 (Dasamsa) for career, profession, status, and work path. "
        "Also use D1 10th house / Sun / Saturn, plus dasa and gochar."
    ),
}


def classify_domain(question: str) -> QueryDomain:
    q = question.lower()
    rel = ["relationship", "marriage", "spouse", "partner", "love", "wedding", "divorce", "romance"]
    car = ["career", "job", "work", "profession", "business", "promotion", "office", "salary", "boss"]
    if any(w in q for w in rel):
        return "relationship"
    if any(w in q for w in car):
        return "career"
    return "general"


def _planet_lines(planets: list[dict], keys: list[str]) -> str:
    lines = []
    for p in planets:
        bits = [str(p.get("planet", ""))]
        for k in keys:
            if k in p and p[k] is not None:
                bits.append(f"{k}={p[k]}")
        lines.append("- " + ", ".join(bits))
    return "\n".join(lines)


def _fmt_rows(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return "(none)"
    lines = [" | ".join(fields)]
    lines.append(" | ".join("---" for _ in fields))
    for row in rows:
        lines.append(" | ".join(str(row.get(f, "")) for f in fields))
    return "\n".join(lines)


def build_context(
    profile: dict[str, Any],
    charts: dict[str, Any],
    dasa: dict[str, Any],
    gochar: dict[str, Any],
    domain: QueryDomain,
) -> str:
    """Full chart + dasa + gochar context for the model."""
    domain = domain if domain != "auto" else "general"
    hint = DOMAIN_HINTS[domain]
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    year = now.year

    current_maha = dasa.get("current_mahadasa") or {}
    current_antar = dasa.get("current_antardasa") or {}

    antar_blocks: list[dict[str, Any]] = []
    mahas = dasa.get("mahadasas", [])
    maha_lords: list[str] = []
    if current_maha:
        maha_lords.append(current_maha["lord"])
        idx = next(
            (
                i
                for i, m in enumerate(mahas)
                if m.get("lord") == current_maha.get("lord")
                and m.get("start") == current_maha.get("start")
            ),
            None,
        )
        if idx is not None and idx + 1 < len(mahas):
            maha_lords.append(mahas[idx + 1]["lord"])
        for lord in maha_lords:
            window = next((m for m in mahas if m.get("lord") == lord), None)
            if not window:
                continue
            subset = [
                a
                for a in dasa.get("antardasas", [])
                if a.get("maha_lord") == lord
                and a.get("start", "") >= window.get("start", "")
                and a.get("end", "") <= window.get("end", "9999-12-31")
            ]
            antar_blocks.extend(subset)

    nearby_mahas = []
    for m in mahas:
        if m.get("end", "") >= today:
            nearby_mahas.append(m)
        if len(nearby_mahas) >= 6:
            break

    gochar_when = gochar.get("current", {}).get("when_utc", now.isoformat(timespec="minutes"))
    upcoming = gochar.get("upcoming", [])

    parts = [
        "=== CLOCK (authoritative — do not invent dates) ===",
        f"Today's UTC date: {today}",
        f"Current calendar year: {year}",
        f"Gochar computed at (UTC): {gochar_when}",
        f"IMPORTANT: The current year is {year}, NOT 2024 or 2025 unless a provided date says so.",
        f"Only use dates that appear in the dasa/gochar sections below. Never default to 2024.",
        "",
        "=== Native ===",
        f"Name: {profile.get('name')}",
        f"Birth: {profile.get('birth_date')} {profile.get('birth_time')} (TZ offset hours {profile.get('timezone_offset')})",
        f"Place: {profile.get('place')}",
        f"Lat/Lon: {profile.get('latitude')}, {profile.get('longitude')}",
        f"Ayanamsa: {charts.get('ayanamsa_name')} {charts.get('ayanamsa')}",
        f"House system: {charts.get('house_system')}",
        f"Moon nakshatra: {charts.get('moon_nakshatra')} (lord {charts.get('moon_nakshatra_lord')})",
        "",
        "=== Analysis focus ===",
        hint,
        "You MUST consult D1, D9, D10, current/upcoming dasa, and current/upcoming gochar before answering.",
        "",
        "=== D1 Rasi (full) ===",
        f"Ascendant: {charts['d1']['ascendant'].get('sign')} "
        f"{charts['d1']['ascendant'].get('degree')}° "
        f"({charts['d1']['ascendant'].get('sign_sa')}), "
        f"nakshatra={charts['d1']['ascendant'].get('nakshatra')}",
        _planet_lines(
            charts["d1"]["planets"],
            ["sign", "sign_sa", "degree", "house", "nakshatra", "nakshatra_lord", "nakshatra_pada"],
        ),
        "",
        "=== D9 Navamsa (full) ===",
        f"Ascendant sign: {charts['d9']['ascendant_sign']} ({charts['d9']['ascendant_sign_sa']})",
        _planet_lines(charts["d9"]["planets"], ["sign", "sign_sa", "house"]),
        "",
        "=== D10 Dasamsa (full) ===",
        f"Ascendant sign: {charts['d10']['ascendant_sign']} ({charts['d10']['ascendant_sign_sa']})",
        _planet_lines(charts["d10"]["planets"], ["sign", "sign_sa", "house"]),
        "",
        "=== Vimshottari Dasa ===",
        f"Starting lord at birth: {dasa.get('starting_lord')}",
        f"Balance years at birth: {dasa.get('balance_years_at_birth')}",
        f"CURRENT Mahadasa: {json.dumps(current_maha)}",
        f"CURRENT Antardasa: {json.dumps(current_antar)}",
        "Nearby mahadasas (from today forward):",
        _fmt_rows(nearby_mahas, ["lord", "start", "end", "years"]),
        "Antardasas for current (+ next) mahadasa:",
        _fmt_rows(antar_blocks, ["maha_lord", "antar_lord", "start", "end", "years"]),
        "",
        "=== Current Gochar (transits) ===",
        f"As of UTC: {gochar_when}",
        _planet_lines(
            gochar.get("current", {}).get("planets", []),
            ["sign", "sign_sa", "degree", "house_from_natal_asc", "nakshatra", "nakshatra_lord"],
        ),
        "",
        "=== Upcoming Gochar sign changes (next ~90 days) ===",
        _fmt_rows(
            upcoming,
            ["date", "planet", "from_sign", "into_sign", "house_from_natal_asc"],
        ),
    ]
    return "\n".join(parts)


def _system_and_user(question: str, context: str, domain: QueryDomain) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    year = now.year
    domain_label = domain if domain != "auto" else classify_domain(question)

    system = (
        f"You are a Vedic astrology assistant for VedicAstro. "
        f"Today's real UTC date is {today} (year {year}). "
        f"Your training cutoff is irrelevant for dates — never assume the year is 2024 or 2025. "
        f"Use ONLY dates present in the provided context (dasa periods and gochar events). "
        f"If you mention timing, cite the exact start/end dates from context.\n\n"
        f"Use D1, D9, D10, dasa, and gochar from the context. "
        f"Primary lens for this query domain ({domain_label}) is described in the context.\n\n"
        f"Be clear and practical. Avoid fear-mongering. Do not invent planetary positions.\n\n"
        f"FORMAT RULES (strict):\n"
        f"- Write in Markdown.\n"
        f"- Start with one short summary paragraph (2–3 sentences max).\n"
        f"- Use ## for section headings.\n"
        f"- Prefer Markdown TABLES for structured content: chart factors, reasons, "
        f"dasa timing, gochar events, and advice. Example columns: Factor | Chart | Finding | Implication.\n"
        f"- Use bullet lists only for short action items.\n"
        f"- Do NOT wrap text with manual mid-sentence line breaks.\n"
        f"- Do NOT use emoji or HTML tags.\n"
        f"- Keep cells concise (one clause per cell)."
    )
    user_prompt = (
        f"Query domain: {domain_label}\n"
        f"Today (UTC): {today}\n\n"
        f"Full chart context:\n{context}\n\n"
        f"User question:\n{question}\n"
    )
    return system, user_prompt


async def ask_llm(question: str, context: str, domain: QueryDomain) -> str:
    """Route to Gemini or Ollama based on LLM_PROVIDER."""
    provider = config.LLM_PROVIDER
    if provider == "ollama":
        return await ask_ollama(question, context, domain)
    if provider == "gemini":
        return await ask_gemini(question, context, domain)
    raise RuntimeError(f"Unknown LLM_PROVIDER={provider!r}. Use 'gemini' or 'ollama'.")


async def ask_gemini(question: str, context: str, domain: QueryDomain) -> str:
    if not config.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it as a Hugging Face Space secret "
            "or export it locally. Get a key at https://aistudio.google.com/apikey"
        )

    system, user_prompt = _system_and_user(question, context, domain)
    model = config.GEMINI_MODEL
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.35, "maxOutputTokens": 4096},
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                url,
                params={"key": config.GEMINI_API_KEY},
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise RuntimeError(f"Gemini API error: {detail}") from exc
        except httpx.ConnectError as exc:
            raise RuntimeError("Cannot reach Gemini API. Check network access.") from exc

        data = resp.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Gemini response: {data}") from exc
        if not text:
            raise RuntimeError(f"Empty response from Gemini: {data}")
        return _strip_think_blocks(text)


async def ask_ollama(
    question: str,
    context: str,
    domain: QueryDomain,
    model: str | None = None,
) -> str:
    model = model or config.OLLAMA_MODEL
    system, user_prompt = _system_and_user(question, context, domain)
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        "options": {"temperature": 0.35},
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            resp = await client.post(f"{config.OLLAMA_URL}/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {config.OLLAMA_URL}. Is `ollama serve` running?"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Ollama error: {exc.response.text}") from exc

        data = resp.json()
        message = data.get("message") or {}
        content = message.get("content") or data.get("response") or ""
        if not content:
            raise RuntimeError(f"Empty response from Ollama: {data}")
        return _strip_think_blocks(content.strip())


def format_answer_html(text: str) -> str:
    """Render model Markdown to HTML optimized for readable wrapping/tables."""
    cleaned = _strip_think_blocks(text)
    cleaned = re.sub(r"^```(?:markdown|md)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = _unwrap_soft_line_breaks(cleaned)
    html = md.markdown(
        cleaned,
        extensions=["sane_lists", "tables"],
        output_format="html5",
    )
    html = re.sub(
        r"(<table>[\s\S]*?</table>)",
        r'<div class="md-table-wrap">\1</div>',
        html,
    )
    return html


def _unwrap_soft_line_breaks(text: str) -> str:
    """Join hard-wrapped prose lines so browsers can wrap naturally."""
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf:
            out.append(buf)
            buf = ""

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush()
            out.append("")
            continue

        structural = bool(
            re.match(r"^(#{1,6}\s|[-*+]\s|\d+\.\s|\|)", stripped)
            or stripped.startswith("```")
            or re.match(r"^[-*]{3,}$", stripped)
        )
        if structural:
            flush()
            out.append(stripped)
            continue

        if not buf:
            buf = stripped
            continue

        if not re.search(r"[.!?…:]$", buf):
            buf = f"{buf} {stripped}"
        else:
            flush()
            buf = stripped

    flush()
    compact: list[str] = []
    blank = 0
    for line in out:
        if line == "":
            blank += 1
            if blank <= 1:
                compact.append(line)
        else:
            blank = 0
            compact.append(line)
    return "\n".join(compact).strip()


def _strip_think_blocks(text: str) -> str:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    return cleaned.strip() or text.strip()

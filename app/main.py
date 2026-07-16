"""VedicAstro FastAPI application."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.astrology.charts import compute_charts
from app.astrology.dasa import compute_dasa
from app.astrology.gochar import gochar_summary
from app.astrology.layout import charts_for_display
from app.db import BirthProfile, get_db, init_db
from app.geo import estimate_timezone_offset, geocode_place
from app import config
from app.llm import ask_llm, build_context, classify_domain, format_answer_html

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="VedicAstro")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _load_profile_payload(profile: BirthProfile) -> tuple[dict, dict, dict]:
    charts = json.loads(profile.chart_json) if profile.chart_json else {}
    dasa = json.loads(profile.dasa_json) if profile.dasa_json else {}
    natal_asc = charts.get("d1", {}).get("ascendant", {}).get("longitude")
    gochar = gochar_summary(natal_asc, profile.latitude, profile.longitude)
    return charts, dasa, gochar


def _antar_view(dasa: dict) -> list:
    current_maha = dasa.get("current_mahadasa")
    if not current_maha:
        return dasa.get("antardasas", [])
    mahas = dasa.get("mahadasas", [])
    idx = next(
        (
            i
            for i, m in enumerate(mahas)
            if m.get("lord") == current_maha.get("lord")
            and m.get("start") == current_maha.get("start")
        ),
        None,
    )
    lords = {current_maha["lord"]}
    windows = {current_maha["lord"]: current_maha}
    if idx is not None and idx + 1 < len(mahas):
        nxt = mahas[idx + 1]
        lords.add(nxt["lord"])
        windows[nxt["lord"]] = nxt
    return [
        a
        for a in dasa.get("antardasas", [])
        if a["maha_lord"] in lords
        and a["start"] >= windows[a["maha_lord"]]["start"]
        and a["end"] <= windows[a["maha_lord"]]["end"]
    ]


def _resolve_birth_inputs(
    place: str,
    timezone_offset: str,
    latitude: str,
    longitude: str,
) -> tuple[str, float, float, float]:
    if latitude.strip() and longitude.strip():
        lat = float(latitude)
        lon = float(longitude)
        resolved_place = place.strip()
    else:
        geo = geocode_place(place.strip())
        lat = geo["latitude"]
        lon = geo["longitude"]
        resolved_place = geo["place"]

    if timezone_offset.strip():
        tz = float(timezone_offset)
    else:
        tz = estimate_timezone_offset(lon, resolved_place)
    return resolved_place, lat, lon, tz


def _profile_page(
    request: Request,
    profile: BirthProfile,
    charts: dict,
    dasa: dict,
    gochar: dict,
    *,
    answer: str | None = None,
    question: str = "",
    domain: str = "auto",
    resolved_domain: str | None = None,
    error: str | None = None,
    edit_error: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "profile": profile,
            "charts": charts,
            "chart_layouts": charts_for_display(charts),
            "dasa": dasa,
            "gochar": gochar,
            "antar_view": _antar_view(dasa),
            "answer_html": format_answer_html(answer) if answer else None,
            "question": question,
            "domain": domain,
            "resolved_domain": resolved_domain,
            "error": error,
            "edit_error": edit_error,
            "llm_label": config.llm_label(),
        },
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    profiles = db.query(BirthProfile).order_by(BirthProfile.id.desc()).limit(20).all()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "profiles": profiles,
            "error": None,
            "form": {},
            "action": "/profiles",
            "button_label": "Generate charts",
        },
    )


@app.post("/profiles", response_class=HTMLResponse)
async def create_profile(
    request: Request,
    name: str = Form(""),
    place: str = Form(...),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    timezone_offset: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form(""),
    db: Session = Depends(get_db),
):
    form = {
        "name": name,
        "place": place,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "timezone_offset": timezone_offset,
        "latitude": latitude,
        "longitude": longitude,
    }
    try:
        resolved_place, lat, lon, tz = _resolve_birth_inputs(
            place, timezone_offset, latitude, longitude
        )
        charts = compute_charts(birth_date, birth_time, lat, lon, tz)
        dasa = compute_dasa(birth_date, birth_time, tz)

        profile = BirthProfile(
            name=(name.strip() or "Seeker"),
            place=resolved_place,
            latitude=lat,
            longitude=lon,
            timezone_offset=tz,
            birth_date=birth_date,
            birth_time=birth_time,
            chart_json=json.dumps(charts),
            dasa_json=json.dumps(dasa),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return RedirectResponse(url=f"/profiles/{profile.id}", status_code=303)
    except Exception as exc:  # noqa: BLE001 — surface to form
        profiles = db.query(BirthProfile).order_by(BirthProfile.id.desc()).limit(20).all()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "profiles": profiles,
                "error": str(exc),
                "form": form,
                "action": "/profiles",
                "button_label": "Generate charts",
            },
            status_code=400,
        )


@app.post("/profiles/{profile_id}/update", response_class=HTMLResponse)
async def update_profile(
    request: Request,
    profile_id: int,
    name: str = Form(""),
    place: str = Form(...),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    timezone_offset: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form(""),
    db: Session = Depends(get_db),
):
    profile = db.get(BirthProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    try:
        resolved_place, lat, lon, tz = _resolve_birth_inputs(
            place, timezone_offset, latitude, longitude
        )
        charts = compute_charts(birth_date, birth_time, lat, lon, tz)
        dasa = compute_dasa(birth_date, birth_time, tz)

        profile.name = name.strip() or "Seeker"
        profile.place = resolved_place
        profile.latitude = lat
        profile.longitude = lon
        profile.timezone_offset = tz
        profile.birth_date = birth_date
        profile.birth_time = birth_time
        profile.chart_json = json.dumps(charts)
        profile.dasa_json = json.dumps(dasa)
        db.commit()
        db.refresh(profile)
        return RedirectResponse(url=f"/profiles/{profile.id}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        charts, dasa, gochar = _load_profile_payload(profile)
        return _profile_page(
            request,
            profile,
            charts,
            dasa,
            gochar,
            edit_error=str(exc),
        )


@app.get("/profiles/{profile_id}", response_class=HTMLResponse)
async def view_profile(request: Request, profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(BirthProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    charts, dasa, gochar = _load_profile_payload(profile)
    return _profile_page(request, profile, charts, dasa, gochar)


@app.post("/profiles/{profile_id}/ask", response_class=HTMLResponse)
async def ask_profile(
    request: Request,
    profile_id: int,
    question: str = Form(...),
    domain: str = Form("auto"),
    db: Session = Depends(get_db),
):
    profile = db.get(BirthProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    charts, dasa, gochar = _load_profile_payload(profile)
    resolved = (
        domain if domain in {"general", "relationship", "career"} else classify_domain(question)
    )

    profile_dict = {
        "name": profile.name,
        "place": profile.place,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "timezone_offset": profile.timezone_offset,
        "birth_date": profile.birth_date,
        "birth_time": profile.birth_time,
    }

    answer = None
    error = None
    try:
        context = build_context(profile_dict, charts, dasa, gochar, resolved)  # type: ignore[arg-type]
        answer = await ask_llm(question, context, resolved)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

    return _profile_page(
        request,
        profile,
        charts,
        dasa,
        gochar,
        answer=answer,
        question=question,
        domain=domain,
        resolved_domain=resolved,
        error=error,
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": "vedicastro",
        "llm_provider": config.LLM_PROVIDER,
        "llm": config.llm_label(),
    }

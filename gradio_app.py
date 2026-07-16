"""
VedicAstro — Hugging Face Gradio entrypoint (ZeroGPU-compatible).

ZeroGPU Spaces require at least one `@spaces.GPU` function at startup.
We decorate Ask AI; chart math stays on CPU.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Callable

import gradio as gr

try:
    import spaces
except ImportError:
    spaces = None  # type: ignore

from app.astrology.charts import compute_charts
from app.astrology.dasa import compute_dasa
from app.astrology.gochar import gochar_summary
from app.config import llm_label
from app.geo import estimate_timezone_offset, geocode_place
from app.llm import ask_llm, build_context, classify_domain, format_answer_html
from app.ui_html import all_charts_html, dasa_html, gochar_html, planet_table_html

os.environ.setdefault("LLM_PROVIDER", "gemini")


def _gpu(fn: Callable) -> Callable:
    """Apply ZeroGPU decorator when running on Hugging Face Spaces."""
    if spaces is None:
        return fn
    return spaces.GPU(fn)


def _resolve_place(
    place: str,
    timezone_offset: str,
    latitude: str,
    longitude: str,
) -> tuple[str, float, float, float]:
    if latitude.strip() and longitude.strip():
        lat = float(latitude)
        lon = float(longitude)
        resolved = place.strip()
    else:
        geo = geocode_place(place.strip())
        lat = geo["latitude"]
        lon = geo["longitude"]
        resolved = geo["place"]
    tz = float(timezone_offset) if timezone_offset.strip() else estimate_timezone_offset(lon)
    return resolved, lat, lon, tz


def generate(
    name: str,
    place: str,
    birth_date: str,
    birth_time: str,
    timezone_offset: str,
    latitude: str,
    longitude: str,
    chart_style: str,
) -> tuple[str, str, str, str, str, dict[str, Any]]:
    if not place or not birth_date or not birth_time:
        raise gr.Error("Place, date, and time of birth are required.")

    resolved, lat, lon, tz = _resolve_place(place, timezone_offset, latitude, longitude)
    charts = compute_charts(birth_date, birth_time, lat, lon, tz)
    dasa = compute_dasa(birth_date, birth_time, tz)
    natal_asc = charts["d1"]["ascendant"]["longitude"]
    gochar = gochar_summary(natal_asc, lat, lon)

    style = "north" if chart_style.lower().startswith("north") else "south"
    summary = (
        f"**{name.strip() or 'Seeker'}** · {birth_date} {birth_time} (TZ {tz}h)\n\n"
        f"{resolved} ({lat:.4f}, {lon:.4f})\n\n"
        f"Ayanamsa {charts['ayanamsa_name']} {charts['ayanamsa']}° · "
        f"Moon in {charts['moon_nakshatra']} ({charts['moon_nakshatra_lord']}) · "
        f"AI: {llm_label()}"
    )
    state = {
        "name": name.strip() or "Seeker",
        "place": resolved,
        "latitude": lat,
        "longitude": lon,
        "timezone_offset": tz,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "charts": charts,
        "dasa": dasa,
        "gochar": gochar,
        "chart_style": style,
    }
    return (
        summary,
        all_charts_html(charts, style),
        planet_table_html(charts),
        dasa_html(dasa),
        gochar_html(gochar),
        state,
    )


def refresh_style(chart_style: str, state: dict[str, Any] | None):
    if not state or "charts" not in state:
        raise gr.Error("Generate a chart first.")
    style = "north" if chart_style.lower().startswith("north") else "south"
    state = {**state, "chart_style": style}
    return all_charts_html(state["charts"], style), state


@_gpu
async def ask(question: str, domain: str, state: dict[str, Any] | None) -> str:
    """ZeroGPU-decorated entry for Q&A (required on ZeroGPU hardware)."""
    if not state or "charts" not in state:
        raise gr.Error("Generate a chart first, then ask a question.")
    if not (question or "").strip():
        raise gr.Error("Enter a question.")

    resolved = domain if domain in {"general", "relationship", "career"} else classify_domain(question)
    profile = {
        "name": state["name"],
        "place": state["place"],
        "latitude": state["latitude"],
        "longitude": state["longitude"],
        "timezone_offset": state["timezone_offset"],
        "birth_date": state["birth_date"],
        "birth_time": state["birth_time"],
    }
    natal_asc = state["charts"]["d1"]["ascendant"]["longitude"]
    gochar = gochar_summary(natal_asc, state["latitude"], state["longitude"])
    context = build_context(profile, state["charts"], state["dasa"], gochar, resolved)  # type: ignore[arg-type]
    try:
        answer = await ask_llm(question, context, resolved)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        raise gr.Error(str(exc)) from exc
    return format_answer_html(answer)


with gr.Blocks(title="VedicAstro") as demo:
    gr.Markdown(
        "# VedicAstro\n"
        "Enter birth details for D1 / D9 / D10, Vimshottari dasa, gochar, then ask Gemini.\n\n"
        f"*Provider: {llm_label()} · Sidereal Lahiri · Whole-sign houses*"
    )
    state = gr.State({})

    with gr.Row():
        name = gr.Textbox(label="Name", value="", placeholder="Your name")
        place = gr.Textbox(label="Place of birth", placeholder="City, Country")
    with gr.Row():
        birth_date = gr.Textbox(label="Date (YYYY-MM-DD)", placeholder="1990-05-15")
        birth_time = gr.Textbox(label="Time (HH:MM)", placeholder="10:30")
        timezone_offset = gr.Textbox(label="TZ offset hours", placeholder="5.5 for IST")
    with gr.Accordion("Advanced: manual coordinates", open=False):
        with gr.Row():
            latitude = gr.Textbox(label="Latitude", placeholder="optional")
            longitude = gr.Textbox(label="Longitude", placeholder="optional")
    chart_style = gr.Radio(
        choices=["South Indian", "North Indian"],
        value="South Indian",
        label="Chart style",
    )
    gen_btn = gr.Button("Generate charts", variant="primary")

    summary = gr.Markdown()
    charts_out = gr.HTML()
    details_out = gr.HTML()
    dasa_out = gr.HTML()
    gochar_out = gr.HTML()

    gen_btn.click(
        generate,
        inputs=[name, place, birth_date, birth_time, timezone_offset, latitude, longitude, chart_style],
        outputs=[summary, charts_out, details_out, dasa_out, gochar_out, state],
    )
    chart_style.change(refresh_style, inputs=[chart_style, state], outputs=[charts_out, state])

    gr.Markdown(f"## Ask {llm_label()}")
    domain = gr.Dropdown(
        choices=["auto", "general", "relationship", "career"],
        value="auto",
        label="Domain (general→D1, relationship→D9, career→D10)",
    )
    question = gr.Textbox(
        label="Question",
        lines=3,
        placeholder="e.g. What does my current period suggest for career focus?",
    )
    ask_btn = gr.Button("Ask AI", variant="primary")
    answer = gr.HTML()
    ask_btn.click(ask, inputs=[question, domain, state], outputs=[answer])

demo.queue()

if __name__ == "__main__":
    demo.launch(ssr_mode=False)

---
title: VedicAstro
emoji: 🕉️
colorFrom: yellow
colorTo: green
sdk: gradio
sdk_version: 5.49.1
python_version: "3.12"
app_file: gradio_app.py
pinned: false
license: mit
short_description: Vedic charts (D1/D9/D10), dasa, gochar, Gemini Q&A
---

# VedicAstro

Public Gradio demo (Hugging Face **ZeroGPU** / free Gradio Spaces) for Vedic charts (D1 / D9 / D10), Vimshottari dasa, gochar, and Q&A via **Gemini**.

Astrology math runs on CPU. Gemini is called over the API (no local model / no GPU required).

## Space secrets

In **Settings → Secrets** add:

- `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/apikey)

Optional:

- `GEMINI_MODEL` (default `gemini-2.5-flash-lite`)
- `LLM_PROVIDER=gemini`

## Hardware

Use **ZeroGPU** (or free Gradio CPU if available). Do **not** use the Docker SDK on the free tier.

## Local run (Gradio)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-local.txt
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=your_key_here
python gradio_app.py
```

## Local run (FastAPI + Ollama)

```bash
pip install -r requirements-local.txt
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=qwen3:4b
ollama serve
python run.py
```

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Public Gradio demo + Gemini |
| `local-ai` | Ollama-focused local use |

## Notes

- Sidereal Lahiri ayanamsa, whole-sign houses
- Set TZ offset explicitly when possible (e.g. `5.5` for IST)

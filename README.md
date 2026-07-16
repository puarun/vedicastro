---
title: VedicAstro
emoji: 🕉️
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Vedic charts (D1/D9/D10), dasa, gochar, Gemini Q&A
---

# VedicAstro

Public demo of Vedic astrology charts (D1 / D9 / D10), Vimshottari dasa, gochar, and Q&A via **Gemini** (free tier).

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Public demo — Hugging Face Spaces + Gemini |
| `local-ai` | Private/local use — Ollama on your machine |

## Hugging Face Spaces setup

1. Create a Space: **Docker** SDK, name e.g. `vedicastro`.
2. Push this repo’s `main` branch to the Space (or connect a GitHub repo).
3. In **Settings → Variables and secrets**, add secret:
   - `GEMINI_API_KEY` = your key from [Google AI Studio](https://aistudio.google.com/apikey)
4. Optional variables:
   - `GEMINI_MODEL` (default `gemini-2.0-flash`)
   - `LLM_PROVIDER=gemini` (already set in the Dockerfile)

## Local run (main / Gemini)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=your_key_here
python run.py
```

Open http://127.0.0.1:8000

## Local run (`local-ai` / Ollama)

```bash
git checkout local-ai
# or on main:
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=qwen3:4b
ollama serve   # separate terminal
python run.py
```

## Notes

- Sidereal Lahiri ayanamsa, whole-sign houses
- SQLite profiles are ephemeral on free Spaces (reset on rebuild); fine for a demo
- Set TZ offset explicitly when possible (e.g. `5.5` for IST)

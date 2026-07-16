"""Runtime configuration via environment variables."""

from __future__ import annotations

import os
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# "gemini" for public demo (HF Spaces); "ollama" for local-ai branch
LLM_PROVIDER = _env("LLM_PROVIDER", "gemini").lower()

GEMINI_API_KEY = _env("GEMINI_API_KEY")
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-2.5-flash-lite")

OLLAMA_URL = _env("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = _env("OLLAMA_MODEL", "qwen3:4b")

# HF Spaces expects 7860; local default remains 8000 via run.py
PORT = int(_env("PORT", "8000"))

# Persist SQLite under /data on Spaces if present, else project data/
_default_data = Path(__file__).resolve().parent.parent / "data"
DATA_DIR = Path(_env("DATA_DIR", str(_default_data)))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def llm_label() -> str:
    if LLM_PROVIDER == "ollama":
        return f"Ollama ({OLLAMA_MODEL})"
    return f"Gemini ({GEMINI_MODEL})"

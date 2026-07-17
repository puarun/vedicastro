#!/usr/bin/env python3
"""Upload current tree to the Hugging Face Space (skips .se1 binaries)."""

from __future__ import annotations

import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
REPO_ID = "puarun/vedicastro"
IGNORE = [
    ".git*",
    ".venv*",
    "**/__pycache__/**",
    ".pytest_cache/**",
    "app/ephe/*.se1",
    "tests/**",
    "*.db",
    "data/**",
    ".env",
]


def main() -> int:
    token = None
    if len(sys.argv) > 1:
        token = sys.argv[1]
    api = HfApi(token=token)
    print(f"Uploading {ROOT} → spaces/{REPO_ID} (excluding ephe binaries)...")
    api.upload_folder(
        folder_path=str(ROOT),
        repo_id=REPO_ID,
        repo_type="space",
        ignore_patterns=IGNORE,
    )
    print("Done. Watch the Space rebuild: https://huggingface.co/spaces/puarun/vedicastro")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path

try:
    from .paths import default_creative_notes_path
except ImportError:
    from paths import default_creative_notes_path


def load_creative_notes(path: Path | None = None) -> str:
    notes_path = path or default_creative_notes_path()
    if not notes_path.exists():
        return ""
    return notes_path.read_text(encoding="utf-8")


def save_creative_notes(content: str, path: Path | None = None) -> None:
    notes_path = path or default_creative_notes_path()
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(content, encoding="utf-8")

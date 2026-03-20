from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

try:
    from .paths import default_settings_path
except ImportError:
    from paths import default_settings_path


@dataclass(slots=True)
class AppSettings:
    github_token: str = ""


def load_settings(path: Path | None = None) -> AppSettings:
    settings_path = path or default_settings_path()
    if not settings_path.exists():
        return AppSettings()

    data = json.loads(settings_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return AppSettings()
    return AppSettings(github_token=str(data.get("github_token", "")).strip())


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    settings_path = path or default_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps({"github_token": settings.github_token.strip()}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

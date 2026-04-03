from __future__ import annotations

from pathlib import Path
import sys


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def default_db_path() -> Path:
    return app_base_dir() / "data" / "oil_prices.db"


def default_log_path() -> Path:
    return app_base_dir() / "data" / "oil_tracker.log"


def default_settings_path() -> Path:
    return app_base_dir() / "data" / "settings.json"


def default_commit_stats_cache_path() -> Path:
    return app_base_dir() / "data" / "commit_stats_cache.json"


def default_us_debt_history_path() -> Path:
    return app_base_dir() / "data" / "us_debt_history.json"


def default_creative_notes_path() -> Path:
    return app_base_dir() / "data" / "creative_notes.txt"


def default_creative_vector_art_path() -> Path:
    return app_base_dir() / "data" / "creative_vector_art.svg"


def default_pizza_watch_history_path() -> Path:
    return app_base_dir() / "data" / "pizza_watch_history.json"

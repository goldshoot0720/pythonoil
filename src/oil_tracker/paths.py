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

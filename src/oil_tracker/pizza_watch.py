from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import html
import json
from pathlib import Path
import re
import ssl
import urllib.request

try:
    from .paths import default_pizza_watch_history_path
except ImportError:
    from paths import default_pizza_watch_history_path


PIZZA_WATCH_URL = "https://www.pizzint.watch/"


@dataclass(frozen=True)
class PizzaWatchShop:
    name: str
    status: str
    distance_miles: float


@dataclass(frozen=True)
class PizzaWatchSnapshot:
    fetched_at: datetime
    doughcon_level: int
    doughcon_title: str
    doughcon_message: str
    monitored_locations: int
    site_status: str
    shops: tuple[PizzaWatchShop, ...]
    source_url: str = PIZZA_WATCH_URL


@dataclass(frozen=True)
class PizzaWatchStreaks:
    consecutive_days: int
    consecutive_weeks: int


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def fetch_pizza_watch_snapshot(timeout: int = 30) -> PizzaWatchSnapshot:
    request = urllib.request.Request(PIZZA_WATCH_URL, headers={"User-Agent": "PythonOil/0.1"})
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        html_text = response.read().decode("utf-8", errors="replace")
    return parse_pizza_watch_snapshot(html_text)


def parse_pizza_watch_snapshot(html_text: str) -> PizzaWatchSnapshot:
    monitored_match = re.search(r"(\d+)\s+LOC(?:ATIONS MONITORED)?", html_text)
    doughcon_match = re.search(
        r"DOUGHCON\s+(\d+).*?<div[^>]*>\s*<span>([^<]+)</span>.*?<span>([^<]+)</span>\s*</div>",
        html_text,
        re.S,
    )
    site_status_match = re.search(r"STATUS:</span><span[^>]*>([A-Z]+)</span>", html_text)

    if monitored_match is None or doughcon_match is None or site_status_match is None:
        raise ValueError("Unable to parse PizzINT summary data")

    shop_matches = re.findall(
        r"alt=\"Pizza slice\"[^>]*>.*?<h3[^>]*>([^<]+)</h3>.*?<span class=\"text-gray-300 font-bold\">(OPEN|CLOSED)</span>.*?"
        r"<div class=\"text-xs text-gray-400 font-mono\">([0-9.]+) mi</div>.*?POPULAR TIMES ANALYSIS",
        html_text,
        re.S,
    )
    if not shop_matches:
        raise ValueError("Unable to parse PizzINT shop cards")

    shops = tuple(
        PizzaWatchShop(
            name=html.unescape(name).strip(),
            status=status.strip(),
            distance_miles=float(distance),
        )
        for name, status, distance in shop_matches
    )

    return PizzaWatchSnapshot(
        fetched_at=datetime.now(),
        doughcon_level=int(doughcon_match.group(1)),
        doughcon_title=html.unescape(doughcon_match.group(2).strip()),
        doughcon_message=html.unescape(doughcon_match.group(3).strip()),
        monitored_locations=int(monitored_match.group(1)),
        site_status=site_status_match.group(1).strip(),
        shops=shops,
    )


def load_pizza_watch_history(path: Path | None = None) -> list[date]:
    history_path = path or default_pizza_watch_history_path()
    if not history_path.exists():
        return []
    payload = json.loads(history_path.read_text(encoding="utf-8"))
    values = payload if isinstance(payload, list) else payload.get("dates", [])
    dates = sorted({date.fromisoformat(str(value)) for value in values})
    return dates


def save_pizza_watch_history(dates: list[date], path: Path | None = None) -> None:
    history_path = path or default_pizza_watch_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = [value.isoformat() for value in sorted(set(dates))]
    history_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def update_pizza_watch_history(snapshot: PizzaWatchSnapshot, path: Path | None = None) -> list[date]:
    dates = load_pizza_watch_history(path)
    snapshot_date = snapshot.fetched_at.date()
    if snapshot_date not in dates:
        dates.append(snapshot_date)
        dates.sort()
        save_pizza_watch_history(dates, path)
    return dates


def calculate_pizza_watch_streaks(dates: list[date]) -> PizzaWatchStreaks:
    if not dates:
        return PizzaWatchStreaks(consecutive_days=0, consecutive_weeks=0)

    ordered_dates = sorted(set(dates))
    consecutive_days = 1
    cursor = ordered_dates[-1]
    for current in reversed(ordered_dates[:-1]):
        if current == cursor - timedelta(days=1):
            consecutive_days += 1
            cursor = current
            continue
        break

    week_starts = sorted({value - timedelta(days=value.weekday()) for value in ordered_dates})
    consecutive_weeks = 1
    cursor_week = week_starts[-1]
    for current in reversed(week_starts[:-1]):
        if current == cursor_week - timedelta(days=7):
            consecutive_weeks += 1
            cursor_week = current
            continue
        break

    return PizzaWatchStreaks(consecutive_days=consecutive_days, consecutive_weeks=consecutive_weeks)

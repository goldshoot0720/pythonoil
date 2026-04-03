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


@dataclass(frozen=True)
class PizzaWatchHistoryEntry:
    snapshot_date: date
    doughcon_level: int
    monitored_locations: int
    open_shop_count: int
    nearest_distance_miles: float


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


def load_pizza_watch_history(path: Path | None = None) -> list[PizzaWatchHistoryEntry]:
    history_path = path or default_pizza_watch_history_path()
    if not history_path.exists():
        return []
    payload = json.loads(history_path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload and isinstance(payload[0], str):
        return [
            PizzaWatchHistoryEntry(
                snapshot_date=date.fromisoformat(value),
                doughcon_level=0,
                monitored_locations=0,
                open_shop_count=0,
                nearest_distance_miles=0.0,
            )
            for value in sorted(set(str(item) for item in payload))
        ]

    values = payload if isinstance(payload, list) else payload.get("entries", [])
    entries: dict[date, PizzaWatchHistoryEntry] = {}
    for value in values:
        snapshot_date = date.fromisoformat(str(value["snapshot_date"]))
        entries[snapshot_date] = PizzaWatchHistoryEntry(
            snapshot_date=snapshot_date,
            doughcon_level=int(value.get("doughcon_level", 0)),
            monitored_locations=int(value.get("monitored_locations", 0)),
            open_shop_count=int(value.get("open_shop_count", 0)),
            nearest_distance_miles=float(value.get("nearest_distance_miles", 0.0)),
        )
    return [entries[key] for key in sorted(entries)]


def save_pizza_watch_history(entries: list[PizzaWatchHistoryEntry], path: Path | None = None) -> None:
    history_path = path or default_pizza_watch_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    deduped = {entry.snapshot_date: entry for entry in entries}
    serializable = [
        {
            "snapshot_date": entry.snapshot_date.isoformat(),
            "doughcon_level": entry.doughcon_level,
            "monitored_locations": entry.monitored_locations,
            "open_shop_count": entry.open_shop_count,
            "nearest_distance_miles": entry.nearest_distance_miles,
        }
        for entry in (deduped[key] for key in sorted(deduped))
    ]
    history_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def build_history_entry(snapshot: PizzaWatchSnapshot) -> PizzaWatchHistoryEntry:
    open_shop_count = sum(1 for shop in snapshot.shops if shop.status == "OPEN")
    nearest_distance = min((shop.distance_miles for shop in snapshot.shops), default=0.0)
    return PizzaWatchHistoryEntry(
        snapshot_date=snapshot.fetched_at.date(),
        doughcon_level=snapshot.doughcon_level,
        monitored_locations=snapshot.monitored_locations,
        open_shop_count=open_shop_count,
        nearest_distance_miles=nearest_distance,
    )


def update_pizza_watch_history(snapshot: PizzaWatchSnapshot, path: Path | None = None) -> list[PizzaWatchHistoryEntry]:
    entries = load_pizza_watch_history(path)
    entry = build_history_entry(snapshot)
    entry_map = {item.snapshot_date: item for item in entries}
    entry_map[entry.snapshot_date] = entry
    updated_entries = [entry_map[key] for key in sorted(entry_map)]
    save_pizza_watch_history(updated_entries, path)
    return updated_entries


def calculate_pizza_watch_streaks(history: list[date] | list[PizzaWatchHistoryEntry]) -> PizzaWatchStreaks:
    if not history:
        return PizzaWatchStreaks(consecutive_days=0, consecutive_weeks=0)

    ordered_dates = sorted(
        {
            value.snapshot_date if isinstance(value, PizzaWatchHistoryEntry) else value
            for value in history
        }
    )
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

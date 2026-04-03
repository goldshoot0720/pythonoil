from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import re
import ssl
import urllib.request


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

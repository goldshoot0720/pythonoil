from __future__ import annotations

from dataclasses import dataclass
import html
import re
import ssl
import urllib.request


POLYMARKET_EVENT_URL = "https://polymarket.com/zh/event/us-forces-enter-iran-by"


@dataclass(frozen=True)
class PolymarketOutcome:
    label: str
    probability: float
    yes_price: float
    no_price: float


@dataclass(frozen=True)
class PolymarketEvent:
    title: str
    volume: str
    outcomes: list[PolymarketOutcome]
    source_url: str = POLYMARKET_EVENT_URL


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def fetch_polymarket_event(timeout: int = 30) -> PolymarketEvent:
    request = urllib.request.Request(
        POLYMARKET_EVENT_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
            "Accept-Language": "zh-TW,zh-CN;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        html_text = response.read().decode("utf-8", errors="replace")
    return parse_polymarket_event(html_text)


def parse_polymarket_event(html_text: str) -> PolymarketEvent:
    title_match = re.search(r"#\s*([^\n<]+)", html_text)
    title = html.unescape(title_match.group(1).strip()) if title_match else ""
    if not title:
        title_tag_match = re.search(r"<title>([^<]+)</title>", html_text, re.IGNORECASE)
        if title_tag_match:
            title = html.unescape(title_tag_match.group(1).strip())
    if not title:
        title = "Polymarket Event"
    if " | " in title:
        title = title.split(" | ", 1)[0].strip()

    volume_match = re.search(r"(\$[0-9,]+)\s*\u4ea4\u6613\u91cf", html_text)
    volume = volume_match.group(1) if volume_match else "-"

    outcomes: list[PolymarketOutcome] = []
    seen: set[str] = set()
    pattern = re.compile(
        r"(\d{1,2}\u6708\d{1,2}\u65e5).*?(<1%|\d+%)\s*\u4e70\u5165\s*\u662f\s*([0-9.]+)\u00a2\s*\u4e70\u5165\s*\u5426\s*([0-9.]+)\u00a2",
        re.S,
    )
    for label, percent_text, yes_price, no_price in pattern.findall(html_text):
        label = html.unescape(label.strip())
        if label in seen:
            continue
        seen.add(label)
        probability = 0.5 if percent_text.strip() == "<1%" else float(percent_text.strip().replace("%", ""))
        outcomes.append(
            PolymarketOutcome(
                label=label,
                probability=probability,
                yes_price=float(yes_price),
                no_price=float(no_price),
            )
        )

    return PolymarketEvent(title=title, volume=volume, outcomes=outcomes)

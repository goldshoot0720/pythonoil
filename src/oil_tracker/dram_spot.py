from __future__ import annotations

from dataclasses import dataclass
import html as html_lib
from datetime import datetime
import re
import ssl
import urllib.request


DRAM_SPOT_URL = "https://www.trendforce.com/price/dram/lpddr_spot"


@dataclass(frozen=True)
class DramSpotRow:
    item: str
    daily_high: float | None
    daily_low: float | None
    session_high: float | None
    session_low: float | None
    session_average: float | None
    session_change: str


@dataclass(frozen=True)
class DramSpotSnapshot:
    last_update: str
    rows: list[DramSpotRow]
    source_url: str = DRAM_SPOT_URL


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def fetch_dram_spot_snapshot(timeout: int = 30) -> DramSpotSnapshot:
    request = urllib.request.Request(DRAM_SPOT_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        html = response.read().decode("utf-8", errors="replace")
    return parse_dram_spot_html(html)


def parse_dram_spot_html(html: str) -> DramSpotSnapshot:
    last_update_match = re.search(r"Last Update\\s*([^<]+)</p>", html)
    if last_update_match is None:
        last_update_match = re.search(r"Last Update\s*([^<]+)</p>", html)
    last_update = last_update_match.group(1).strip() if last_update_match else "Unknown"

    tbody_match = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    if tbody_match is None:
        raise ValueError("DRAM spot table not found")
    tbody = tbody_match.group(1)

    rows: list[DramSpotRow] = []
    for row_html in re.findall(r"<tr>(.*?)</tr>", tbody, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)
        if len(cells) < 7:
            continue
        item = _strip_tags(cells[0])
        if not item:
            continue
        daily_high = _parse_float(_strip_tags(cells[1]))
        daily_low = _parse_float(_strip_tags(cells[2]))
        session_high = _parse_float(_strip_tags(cells[3]))
        session_low = _parse_float(_strip_tags(cells[4]))
        session_average = _parse_float(_strip_tags(cells[5]))
        session_change = html_lib.unescape(_strip_tags(cells[6]).replace("\xa0", " ").strip())
        rows.append(
            DramSpotRow(
                item=item,
                daily_high=daily_high,
                daily_low=daily_low,
                session_high=session_high,
                session_low=session_low,
                session_average=session_average,
                session_change=session_change,
            )
        )
    if not rows:
        raise ValueError("DRAM spot rows not parsed")
    return DramSpotSnapshot(last_update=last_update, rows=rows)


def _strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\\s+", " ", text).strip()


def _parse_float(value: str) -> float | None:
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None

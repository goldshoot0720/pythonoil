from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from html import unescape
from html.parser import HTMLParser
import re
from urllib.request import Request, urlopen

GME_URL = "https://www.gulfmerc.com/"
USER_AGENT = "Mozilla/5.0 (compatible; oil-tracker/0.1; +https://www.gulfmerc.com/)"


@dataclass(slots=True)
class OilPriceRecord:
    price_date: date
    price: float
    source_url: str = GME_URL


def fetch_price_record(timeout: int = 20) -> OilPriceRecord:
    request = Request(GME_URL, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8", errors="ignore")
    return parse_price_record(html)


def parse_price_record(html: str) -> OilPriceRecord:
    parser = _TextExtractor()
    parser.feed(html)
    text = unescape("\n".join(parser.lines))
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines):
        if line != "OQD Daily Marker Price":
            continue

        price = _extract_price(lines, index + 1)
        price_date = _extract_date(lines, index + 1)
        if price is not None and price_date is not None:
            return OilPriceRecord(price_date=price_date, price=price)

    raise ValueError("Could not locate OQD Daily Marker Price block in page content.")


def _extract_price(lines: list[str], start_index: int) -> float | None:
    for line in lines[start_index : start_index + 6]:
        if re.fullmatch(r"\d+(?:,\d{3})*(?:\.\d+)?", line):
            return float(line.replace(",", ""))
    return None


def _extract_date(lines: list[str], start_index: int) -> date | None:
    for line in lines[start_index : start_index + 8]:
        normalized = re.sub(r"[-\s,]+", "-", line.strip(" -,"))
        for fmt in ("%d-%b-%Y", "%d-%B-%Y"):
            try:
                return datetime.strptime(normalized, fmt).date()
            except ValueError:
                continue
    return None


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.lines.append(stripped)

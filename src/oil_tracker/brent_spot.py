from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import csv
from io import StringIO
import ssl
import urllib.request


BRENT_SPOT_CSV_URL = "https://datahub.io/core/oil-prices/_r/-/data/brent-daily.csv"
BRENT_SPOT_SOURCE_URL = "https://datahub.io/core/oil-prices"


@dataclass(frozen=True)
class BrentSpotPoint:
    price_date: date
    price: float


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def fetch_brent_spot_series(limit: int = 180, timeout: int = 30) -> list[BrentSpotPoint]:
    request = urllib.request.Request(BRENT_SPOT_CSV_URL, headers={"User-Agent": "PythonOil/0.1"})
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        csv_text = response.read().decode("utf-8", errors="replace")
    return parse_brent_spot_csv(csv_text, limit=limit)


def parse_brent_spot_csv(csv_text: str, limit: int | None = None) -> list[BrentSpotPoint]:
    reader = csv.DictReader(StringIO(csv_text))
    points: list[BrentSpotPoint] = []
    for row in reader:
        if not row.get("Date") or not row.get("Price"):
            continue
        try:
            price_date = datetime.strptime(row["Date"], "%Y-%m-%d").date()
            price = float(row["Price"])
        except ValueError:
            continue
        points.append(BrentSpotPoint(price_date=price_date, price=price))
    points.sort(key=lambda item: item.price_date)
    if limit is not None:
        return points[-limit:]
    return points

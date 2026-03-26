from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    from .paths import default_us_debt_history_path
except ImportError:
    from paths import default_us_debt_history_path

US_DEBT_URL = "https://www.usadebtclock.com/"
USER_AGENT = "Mozilla/5.0 (compatible; oil-tracker/0.1; +https://www.usadebtclock.com/)"


@dataclass(slots=True)
class USDebtRecord:
    snapshot_date: date
    national_debt_cents: int
    source_url: str = US_DEBT_URL


@dataclass(slots=True)
class USDebtSaveResult:
    record: USDebtRecord
    previous_debt_cents: int | None
    inserted: bool
    updated: bool

    @property
    def change_cents(self) -> int | None:
        if self.previous_debt_cents is None:
            return None
        return self.record.national_debt_cents - self.previous_debt_cents


def fetch_us_national_debt(timeout: int = 20) -> USDebtRecord:
    request = Request(US_DEBT_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(f"Unable to reach usadebtclock.com: {reason}") from exc
    return parse_us_national_debt(html)


def parse_us_national_debt(html: str) -> USDebtRecord:
    parser = _TextExtractor()
    parser.feed(html)
    text = unescape("\n".join(parser.lines))
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    amount_cents = None
    snapshot_date = None
    for index, line in enumerate(lines):
        if amount_cents is None:
            amount_cents = _extract_amount_from_line(line)
        if amount_cents is None and line == "United States National Debt":
            amount_cents = _extract_currency_cents(lines, index + 1)
        if snapshot_date is None:
            snapshot_date = _extract_snapshot_date(line)
        if amount_cents is not None and snapshot_date is not None:
            break

    if amount_cents is None:
        raise ValueError("Could not locate United States National Debt value in page content.")

    if snapshot_date is None:
        snapshot_date = datetime.now().date()

    return USDebtRecord(snapshot_date=snapshot_date, national_debt_cents=amount_cents)


def _extract_amount_from_line(line: str) -> int | None:
    match = re.search(
        r"United States National Debt(?:\s+Per\s+Person|\s+Per\s+Household)?",
        line,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    if "Per Person" in line or "Per Household" in line:
        return None

    currency_match = re.search(r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", line[match.end() :])
    if currency_match is None:
        return None

    dollars, _, cents = currency_match.group(1).replace(",", "").partition(".")
    return int(dollars) * 100 + int((cents or "00").ljust(2, "0")[:2])


def load_us_debt_history(path: Path | None = None) -> list[USDebtRecord]:
    history_path = path or default_us_debt_history_path()
    if not history_path.exists():
        return []

    data = json.loads(history_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []

    records: list[USDebtRecord] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            records.append(
                USDebtRecord(
                    snapshot_date=date.fromisoformat(str(item["snapshot_date"])),
                    national_debt_cents=int(item["national_debt_cents"]),
                    source_url=str(item.get("source_url", US_DEBT_URL)),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    return sorted(records, key=lambda record: record.snapshot_date)


def save_us_debt_record(record: USDebtRecord, path: Path | None = None) -> USDebtSaveResult:
    history_path = path or default_us_debt_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)

    records = load_us_debt_history(history_path)
    previous_record = next((item for item in reversed(records) if item.snapshot_date < record.snapshot_date), None)

    inserted = True
    updated = False
    replaced = False
    for index, existing in enumerate(records):
        if existing.snapshot_date == record.snapshot_date:
            records[index] = record
            inserted = False
            updated = existing.national_debt_cents != record.national_debt_cents
            replaced = True
            break

    if not replaced:
        records.append(record)

    records = sorted(records, key=lambda item: item.snapshot_date)
    history_path.write_text(
        json.dumps(
            [
                {
                    "snapshot_date": item.snapshot_date.isoformat(),
                    "national_debt_cents": item.national_debt_cents,
                    "source_url": item.source_url,
                }
                for item in records
            ],
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    return USDebtSaveResult(
        record=record,
        previous_debt_cents=None if previous_record is None else previous_record.national_debt_cents,
        inserted=inserted,
        updated=updated,
    )


def _extract_currency_cents(lines: list[str], start_index: int) -> int | None:
    for line in lines[start_index : start_index + 4]:
        match = re.fullmatch(r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", line)
        if not match:
            continue

        dollars, _, cents = match.group(1).replace(",", "").partition(".")
        return int(dollars) * 100 + int((cents or "00").ljust(2, "0")[:2])
    return None


def _extract_snapshot_date(line: str) -> date | None:
    match = re.search(r"last updated\s+(\d{4}-\d{2}-\d{2})", line, flags=re.IGNORECASE)
    if match is None:
        return None
    return date.fromisoformat(match.group(1))


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.lines.append(stripped)

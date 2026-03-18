from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import sqlite3
from pathlib import Path

try:
    from .gme import OilPriceRecord
except ImportError:
    from gme import OilPriceRecord


@dataclass(slots=True)
class SaveResult:
    record: OilPriceRecord
    previous_price: float | None
    inserted: bool

    @property
    def change(self) -> float | None:
        if self.previous_price is None:
            return None
        return round(self.record.price - self.previous_price, 2)


class OilPriceRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS oil_prices (
                    price_date TEXT PRIMARY KEY,
                    price REAL NOT NULL,
                    source_url TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )
                """
            )

    def save(self, record: OilPriceRecord) -> SaveResult:
        previous_price = self.get_previous_price(record.price_date)

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO oil_prices (price_date, price, source_url, fetched_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    record.price_date.isoformat(),
                    record.price,
                    record.source_url,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                ),
            )

        return SaveResult(
            record=record,
            previous_price=previous_price,
            inserted=cursor.rowcount == 1,
        )

    def get_previous_price(self, current_date: date) -> float | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT price
                FROM oil_prices
                WHERE price_date < ?
                ORDER BY price_date DESC
                LIMIT 1
                """,
                (current_date.isoformat(),),
            ).fetchone()
        return None if row is None else float(row["price"])

    def list_recent(self, limit: int = 30) -> list[OilPriceRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT price_date, price, source_url
                FROM oil_prices
                ORDER BY price_date DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            OilPriceRecord(
                price_date=date.fromisoformat(row["price_date"]),
                price=float(row["price"]),
                source_url=row["source_url"],
            )
            for row in rows
        ]

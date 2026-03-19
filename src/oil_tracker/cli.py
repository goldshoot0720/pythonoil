from __future__ import annotations

import argparse
from pathlib import Path

from .gme import fetch_price_record
from .paths import default_db_path
from .storage import OilPriceRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track daily OQD marker prices.")
    parser.add_argument(
        "--db",
        type=Path,
        default=default_db_path(),
        help="SQLite database path. Default: ./data/oil_prices.db next to the app",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    record = fetch_price_record()
    repository = OilPriceRepository(args.db)
    result = repository.save(record)

    print(f"Date: {result.record.price_date.isoformat()}")
    print(f"OQD Daily Marker Price: {result.record.price:.2f}")

    if result.change is None:
        print("Change: N/A (no previous record)")
    else:
        print(f"Change: {result.change:+.2f}")

    if result.inserted:
        print(f"Saved to: {args.db}")
    else:
        print(f"Record already exists for {result.record.price_date.isoformat()}: {args.db}")


if __name__ == "__main__":
    main()

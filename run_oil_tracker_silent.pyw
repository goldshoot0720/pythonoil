import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "src"))

from oil_tracker.gme import fetch_price_record
from oil_tracker.paths import default_db_path, default_log_path
from oil_tracker.storage import OilPriceRepository

log_path = default_log_path()
log_path.parent.mkdir(parents=True, exist_ok=True)

def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")

try:
    repository = OilPriceRepository(default_db_path())
    record = fetch_price_record()
    result = repository.save(record)
    if result.change is None:
        change_text = "N/A"
    else:
        change_text = f"{result.change:+.2f}"
    state = "inserted" if result.inserted else "exists"
    log(f"date={record.price_date.isoformat()} price={record.price:.2f} change={change_text} state={state}")
except Exception as exc:
    log(f"error={type(exc).__name__}: {exc}")

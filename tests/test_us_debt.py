from datetime import date
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.us_debt import (
    USDebtRecord,
    load_us_debt_history,
    parse_us_national_debt,
    save_us_debt_record,
)


class USDebtTests(unittest.TestCase):
    def test_parse_us_national_debt_extracts_amount_and_date(self) -> None:
        html = """
        <html>
            <body>
                <table>
                    <tr><td>United States National Debt</td><td>$39,013,530,100,939.09</td></tr>
                </table>
                <p>(last updated 2026-03-25/Close of previous day debt was $38999855700424.49 )</p>
            </body>
        </html>
        """

        record = parse_us_national_debt(html)

        self.assertEqual(record.snapshot_date.isoformat(), "2026-03-25")
        self.assertEqual(record.national_debt_cents, 3901353010093909)

    def test_parse_us_national_debt_extracts_amount_when_label_and_value_share_line(self) -> None:
        html = """
        <html>
            <body>
                <div>United States National Debt $39,013,556,294,668.89</div>
                <p>(last updated 2026-03-25/Close of previous day debt was $38999855700424.49 )</p>
            </body>
        </html>
        """

        record = parse_us_national_debt(html)

        self.assertEqual(record.snapshot_date.isoformat(), "2026-03-25")
        self.assertEqual(record.national_debt_cents, 3901355629466889)

    def test_save_us_debt_record_persists_sorted_history(self) -> None:
        test_dir = Path("tests_tmp") / self._testMethodName
        if test_dir.exists():
            shutil.rmtree(test_dir)
        history_path = test_dir / "us_debt_history.json"

        save_us_debt_record(
            USDebtRecord(snapshot_date=date(2026, 3, 26), national_debt_cents=3902000000000000),
            history_path,
        )
        save_us_debt_record(
            USDebtRecord(snapshot_date=date(2026, 3, 25), national_debt_cents=3901000000000000),
            history_path,
        )

        records = load_us_debt_history(history_path)

        self.assertEqual([record.snapshot_date.isoformat() for record in records], ["2026-03-25", "2026-03-26"])
        self.assertEqual(records[-1].national_debt_cents, 3902000000000000)

    def test_save_us_debt_record_updates_existing_day(self) -> None:
        test_dir = Path("tests_tmp") / self._testMethodName
        if test_dir.exists():
            shutil.rmtree(test_dir)
        history_path = test_dir / "us_debt_history.json"

        save_us_debt_record(
            USDebtRecord(snapshot_date=date(2026, 3, 25), national_debt_cents=3901000000000000),
            history_path,
        )
        result = save_us_debt_record(
            USDebtRecord(snapshot_date=date(2026, 3, 25), national_debt_cents=3901000000001234),
            history_path,
        )

        records = load_us_debt_history(history_path)

        self.assertFalse(result.inserted)
        self.assertTrue(result.updated)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].national_debt_cents, 3901000000001234)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.brent_spot import parse_brent_spot_csv


class BrentSpotTests(unittest.TestCase):
    def test_parse_brent_spot_csv(self) -> None:
        csv_text = "Date,Price\n2026-04-01,80.12\n2026-04-02,81.45\n"

        points = parse_brent_spot_csv(csv_text)

        self.assertEqual(len(points), 2)
        self.assertEqual(points[0].price_date.isoformat(), "2026-04-01")
        self.assertEqual(points[1].price, 81.45)


if __name__ == "__main__":
    unittest.main()

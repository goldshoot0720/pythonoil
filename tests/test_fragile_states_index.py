from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.fragile_states_index import extract_china_point


class FragileStatesIndexTests(unittest.TestCase):
    def test_extract_china_point(self) -> None:
        rows = [
            {"Country": "Japan", "Year": "2023", "Rank": "150", "Total": "42.1"},
            {"Country": "China", "Year": "2023", "Rank": "90", "Total": "70.2"},
        ]

        point = extract_china_point(rows, 2023)

        self.assertIsNotNone(point)
        self.assertEqual(point.year, 2023)
        self.assertEqual(point.rank, 90)
        self.assertAlmostEqual(point.total_score, 70.2)


if __name__ == "__main__":
    unittest.main()

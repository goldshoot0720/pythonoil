from datetime import date
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.gme import OilPriceRecord
from oil_tracker.storage import OilPriceRepository


class OilPriceRepositoryTests(unittest.TestCase):
    def test_repository_saves_and_calculates_change(self) -> None:
        test_dir = Path("tests_tmp") / self._testMethodName
        if test_dir.exists():
            shutil.rmtree(test_dir)

        repository = OilPriceRepository(test_dir / "oil_prices.db")
        first = OilPriceRecord(price_date=date(2026, 3, 16), price=150.0)
        second = OilPriceRecord(price_date=date(2026, 3, 17), price=152.58)

        first_result = repository.save(first)
        second_result = repository.save(second)

        self.assertTrue(first_result.inserted)
        self.assertIsNone(first_result.change)
        self.assertTrue(second_result.inserted)
        self.assertEqual(second_result.previous_price, 150.0)
        self.assertEqual(second_result.change, 2.58)


if __name__ == "__main__":
    unittest.main()

from datetime import datetime
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.gui import get_birthday_easter_egg, is_birthday_easter_egg_day


class GuiDateTests(unittest.TestCase):
    def test_birthday_easter_egg_day_is_april_third(self) -> None:
        self.assertTrue(is_birthday_easter_egg_day(datetime(2026, 4, 3, 9, 0, 0)))
        easter_egg = get_birthday_easter_egg(datetime(2026, 4, 3, 9, 0, 0))
        self.assertIsNotNone(easter_egg)
        self.assertEqual(easter_egg.title, "塗哥生日快樂")

    def test_birthday_easter_egg_day_is_november_twenty_seventh(self) -> None:
        self.assertTrue(is_birthday_easter_egg_day(datetime(2026, 11, 27, 8, 30, 0)))
        easter_egg = get_birthday_easter_egg(datetime(2026, 11, 27, 8, 30, 0))
        self.assertIsNotNone(easter_egg)
        self.assertEqual(easter_egg.title, "鋒兄生日快樂")
        self.assertEqual(easter_egg.subtitle, "高考三級資訊處理榜首鋒兄")

    def test_birthday_easter_egg_day_is_false_on_other_days(self) -> None:
        self.assertFalse(is_birthday_easter_egg_day(datetime(2026, 4, 2, 23, 59, 59)))
        self.assertFalse(is_birthday_easter_egg_day(datetime(2026, 4, 4, 0, 0, 0)))
        self.assertIsNone(get_birthday_easter_egg(datetime(2026, 11, 26, 12, 0, 0)))


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.taiwan_lottery import GAME_CONFIG_MAP, build_group_summaries, parse_lottery_csv


class TaiwanLotteryTests(unittest.TestCase):
    def test_parse_super_lotto_csv_builds_comparisons(self) -> None:
        csv_text = """遊戲名稱,期別,開獎日期,銷售總額,銷售注數,總獎金,獎號1,獎號2,獎號3,獎號4,獎號5,獎號6,第二區
威力彩,115000999,2026/03/30,0,0,0,7,11,23,32,33,38,02
"""
        draws = parse_lottery_csv(csv_text, GAME_CONFIG_MAP["super_lotto638"])

        self.assertEqual(len(draws), 1)
        draw = draws[0]
        self.assertEqual(draw.issue, "115000999")
        self.assertEqual(draw.main_numbers, (7, 11, 23, 32, 33, 38))
        self.assertEqual(draw.special_number, 2)
        self.assertTrue(draw.comparisons[0].exact_match)
        self.assertFalse(draw.comparisons[1].exact_match)
        self.assertEqual(draw.comparisons[1].matched_main, 6)
        self.assertFalse(draw.comparisons[1].special_matched)

    def test_parse_daily_cash_csv_counts_matches(self) -> None:
        csv_text = """遊戲名稱,期別,開獎日期,銷售總額,銷售注數,總獎金,獎號1,獎號2,獎號3,獎號4,獎號5
今彩539,115000111,2026/03/30,0,0,0,19,8,11,27,37
今彩539,115000112,2026/03/31,0,0,0,1,2,3,4,5
"""
        draws = parse_lottery_csv(csv_text, GAME_CONFIG_MAP["daily_cash"])

        self.assertEqual(draws[0].comparisons[0].matched_main, 5)
        self.assertTrue(draws[0].comparisons[0].exact_match)
        self.assertEqual(draws[0].comparisons[1].matched_main, 3)
        self.assertEqual(draws[1].comparisons[0].matched_main, 0)

    def test_build_group_summaries_reports_best_hit(self) -> None:
        csv_text = """遊戲名稱,期別,開獎日期,銷售總額,銷售注數,總獎金,獎號1,獎號2,獎號3,獎號4,獎號5,獎號6
大樂透,115000211,2026/03/30,0,0,0,19,8,11,27,37,16
大樂透,115000212,2026/03/31,0,0,0,19,8,4,3,37,16
"""
        config = GAME_CONFIG_MAP["lotto649"]
        summaries = build_group_summaries(config, parse_lottery_csv(csv_text, config))

        self.assertEqual(
            summaries,
            [
                "第一組: 完全相符 1 期，最高 6/6",
                "第二組: 完全相符 1 期，最高 6/6",
            ],
        )


if __name__ == "__main__":
    unittest.main()

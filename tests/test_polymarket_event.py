from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.polymarket_event import parse_polymarket_event


class PolymarketEventTests(unittest.TestCase):
    def test_parse_polymarket_event(self) -> None:
        title = "\u7f8e\u519b\u8fdb\u5165\u4f0a\u6717\u7684\u65b9\u5f0f\u662f.. \uff1f"
        html = f"""
        # {title}
        $114,896,600 \u4ea4\u6613\u91cf
        4\u670830\u65e5
        85%
        \u4e70\u5165 \u662f 85\u00a2\u4e70\u5165 \u5426 16\u00a2
        12\u670831\u65e5
        90%
        \u4e70\u5165 \u662f 90\u00a2\u4e70\u5165 \u5426 11\u00a2
        3\u670831\u65e5
        <1%
        \u4e70\u5165 \u662f 0.1\u00a2\u4e70\u5165 \u5426 0.0\u00a2
        """

        event = parse_polymarket_event(html)

        self.assertEqual(event.title, title)
        self.assertEqual(event.volume, "$114,896,600")
        self.assertEqual(len(event.outcomes), 3)
        self.assertEqual(event.outcomes[0].label, "4\u670830\u65e5")
        self.assertAlmostEqual(event.outcomes[0].probability, 85.0)
        self.assertAlmostEqual(event.outcomes[2].probability, 0.5)


if __name__ == "__main__":
    unittest.main()

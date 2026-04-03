from datetime import date, datetime
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.pizza_watch import (
    PizzaWatchSnapshot,
    PizzaWatchShop,
    calculate_pizza_watch_streaks,
    load_pizza_watch_history,
    parse_pizza_watch_snapshot,
    update_pizza_watch_history,
)


class PizzaWatchTests(unittest.TestCase):
    def test_parse_pizza_watch_snapshot(self) -> None:
        html_text = """
        <span class="lg:hidden">8 LOC</span><span class="hidden lg:inline">8 LOCATIONS MONITORED</span>
        <div class="text-4xl">DOUGHCON 4</div><div><span>DOUBLE TAKE</span><span class="opacity-60">•</span><span>INCREASED INTELLIGENCE WATCH</span></div>
        <span>STATUS:</span><span>OPERATIONAL</span>
        <img alt="Pizza slice" src="/pizza.svg" />
        <h3>DOMINO&#x27;S PIZZA</h3>
        <span class="text-gray-300 font-bold">OPEN</span>
        <div class="text-xs text-gray-400 font-mono">1.4 mi</div>
        <div>POPULAR TIMES ANALYSIS</div>
        <img alt="Pizza slice" src="/pizza.svg" />
        <h3>EXTREME PIZZA</h3>
        <span class="text-gray-300 font-bold">CLOSED</span>
        <div class="text-xs text-gray-400 font-mono">0.5 mi</div>
        <div>POPULAR TIMES ANALYSIS</div>
        """

        snapshot = parse_pizza_watch_snapshot(html_text)

        self.assertEqual(snapshot.monitored_locations, 8)
        self.assertEqual(snapshot.doughcon_level, 4)
        self.assertEqual(snapshot.doughcon_title, "DOUBLE TAKE")
        self.assertEqual(snapshot.doughcon_message, "INCREASED INTELLIGENCE WATCH")
        self.assertEqual(snapshot.site_status, "OPERATIONAL")
        self.assertEqual(len(snapshot.shops), 2)
        self.assertEqual(snapshot.shops[0].name, "DOMINO'S PIZZA")
        self.assertEqual(snapshot.shops[0].status, "OPEN")
        self.assertEqual(snapshot.shops[1].distance_miles, 0.5)

    def test_calculate_streaks(self) -> None:
        streaks = calculate_pizza_watch_streaks(
            [
                date(2026, 4, 1),
                date(2026, 4, 2),
                date(2026, 4, 3),
                date(2026, 4, 8),
                date(2026, 4, 15),
            ]
        )

        self.assertEqual(streaks.consecutive_days, 1)
        self.assertEqual(streaks.consecutive_weeks, 3)

    def test_update_history_persists_unique_dates(self) -> None:
        test_dir = Path("tests_tmp") / self._testMethodName
        if test_dir.exists():
            shutil.rmtree(test_dir)
        history_path = test_dir / "pizza_watch_history.json"
        snapshot = PizzaWatchSnapshot(
            fetched_at=datetime(2026, 4, 3, 9, 0, 0),
            doughcon_level=4,
            doughcon_title="DOUBLE TAKE",
            doughcon_message="INCREASED INTELLIGENCE WATCH",
            monitored_locations=8,
            site_status="OPERATIONAL",
            shops=(PizzaWatchShop(name="DOMINO'S PIZZA", status="OPEN", distance_miles=1.4),),
        )

        update_pizza_watch_history(snapshot, history_path)
        update_pizza_watch_history(snapshot, history_path)
        dates = load_pizza_watch_history(history_path)

        self.assertEqual(dates, [date(2026, 4, 3)])


if __name__ == "__main__":
    unittest.main()

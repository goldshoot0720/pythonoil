from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.pizza_watch import parse_pizza_watch_snapshot


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


if __name__ == "__main__":
    unittest.main()

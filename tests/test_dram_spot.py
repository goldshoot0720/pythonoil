from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oil_tracker.dram_spot import parse_dram_spot_html


class DramSpotTests(unittest.TestCase):
    def test_parse_dram_spot_html(self) -> None:
        html = """
        <div class="price-last-update"><p>Last Update 2026-04-03 18:10 (GMT+8)</p></div>
        <table class="price-table">
            <tbody>
                <tr>
                    <td style="width:auto"><span>DDR5 16Gb (2Gx8) 4800/5600</span></td>
                    <td class="lcd-num-l">48.00</td>
                    <td class="lcd-num-l">25.80</td>
                    <td class="lcd-num-l">48.00</td>
                    <td class="lcd-num-l">26.00</td>
                    <td class="lcd-num-l">37.00</td>
                    <td class="percent-cell"><span class="flat-trend"><span>&mdash;</span> 0.00 %</span></td>
                </tr>
            </tbody>
        </table>
        """

        snapshot = parse_dram_spot_html(html)

        self.assertEqual(snapshot.last_update, "2026-04-03 18:10 (GMT+8)")
        self.assertEqual(len(snapshot.rows), 1)
        self.assertEqual(snapshot.rows[0].item, "DDR5 16Gb (2Gx8) 4800/5600")
        self.assertEqual(snapshot.rows[0].session_average, 37.0)


if __name__ == "__main__":
    unittest.main()

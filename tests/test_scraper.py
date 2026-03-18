from datetime import date
import unittest

from oil_tracker.gme import parse_price_record


class ParsePriceRecordTests(unittest.TestCase):
    def test_parse_price_record_reads_price_and_date(self) -> None:
        html = """
        <html>
          <body>
            <section>
              <h2>Market Summary</h2>
              <div>OQD Daily Marker Price</div>
              <div>152.58</div>
              <div>17 Mar, 2026</div>
            </section>
          </body>
        </html>
        """

        record = parse_price_record(html)

        self.assertEqual(record.price, 152.58)
        self.assertEqual(record.price_date, date(2026, 3, 17))


if __name__ == "__main__":
    unittest.main()

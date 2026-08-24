import unittest
from decimal import Decimal

import pandas as pd

from analytics.pipeline import _complete_daily_series, calculate_kpis


class PipelineMetricTests(unittest.TestCase):
    def test_buyer_conversion_counts_distinct_buyers_not_orders(self):
        result = calculate_kpis({
            "users": 10,
            "buyers": 2,
            "paid_orders": 5,
            "orders": 8,
            "cancelled_orders": 2,
            "revenue": Decimal("500.00"),
            "topics_today": 3,
            "comments_today": 4,
        })

        self.assertEqual(result["buyer_conversion_rate"], 20.0)
        self.assertEqual(result["average_ticket"], 100.0)
        self.assertEqual(result["community_today"], 7)
        self.assertEqual(result["order_cancellation_rate"], 25.0)

    def test_zero_denominators_are_safe(self):
        result = calculate_kpis({"users": 0, "buyers": 0, "paid_orders": 0, "revenue": 0})
        self.assertEqual(result["buyer_conversion_rate"], 0.0)
        self.assertEqual(result["average_ticket"], 0.0)
        self.assertEqual(result["order_cancellation_rate"], 0.0)

    def test_timeseries_fills_days_without_events(self):
        today = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
        result = _complete_daily_series(pd.DataFrame({"day": [today], "value": [2]}), 7)
        self.assertEqual(len(result), 7)
        self.assertEqual(float(result["value"].sum()), 2.0)
        self.assertEqual(int((result["value"] == 0).sum()), 6)


if __name__ == "__main__":
    unittest.main()

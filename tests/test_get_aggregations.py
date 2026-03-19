import datetime as dt
import unittest
from unittest.mock import patch

import pandas as pd

from app.services.get_aggregations import get_daily_summary


def _build_daily_summary_frame() -> dict[str, pd.DataFrame]:
    index = pd.date_range("2000-01-01", periods=24 * 60 * 60, freq="s").strftime("%H:%M:%S")
    mean_df = pd.DataFrame({63: range(len(index)), 125: range(len(index))}, index=index)
    min_df = pd.DataFrame({63: range(len(index)), 125: range(len(index))}, index=index)
    max_df = pd.DataFrame({63: range(len(index)), 125: range(len(index))}, index=index)
    count_df = pd.DataFrame({63: [1] * len(index), 125: [1] * len(index)}, index=index)
    return {
        "mean": mean_df,
        "min": min_df,
        "max": max_df,
        "count": count_df,
    }


class GetAggregationsTests(unittest.TestCase):
    @patch("app.services.get_aggregations._resolve_hydrophone")
    def test_get_daily_summary_auto_interval_uses_smallest_bucket_within_target(
        self, mock_resolve_hydrophone
    ):
        class FakeHydrophone:
            name = "ORCASOUND_LAB"

        class FakeDailyNoiseAnalysis:
            def __init__(self, hydrophone):
                self.hydrophone = hydrophone

            def create_daily_noise_summary_df(self, start_date, num_days):
                return _build_daily_summary_frame()

        mock_resolve_hydrophone.return_value = (
            "orcasound_lab",
            FakeDailyNoiseAnalysis,
            FakeHydrophone(),
        )

        result = get_daily_summary(
            "orcasound_lab",
            dt.date(2020, 1, 1),
            30,
            63,
            8000,
        )

        self.assertEqual(result.interval, "5m")
        self.assertEqual(result.mean_length, 288)
        self.assertEqual(result.min_length, 288)
        self.assertEqual(result.max_length, 288)
        self.assertEqual(result.count_length, 288)

    @patch("app.services.get_aggregations._resolve_hydrophone")
    def test_get_daily_summary_rejects_explicit_interval_above_point_limit(
        self, mock_resolve_hydrophone
    ):
        class FakeHydrophone:
            name = "ORCASOUND_LAB"

        class FakeDailyNoiseAnalysis:
            def __init__(self, hydrophone):
                self.hydrophone = hydrophone

            def create_daily_noise_summary_df(self, start_date, num_days):
                return _build_daily_summary_frame()

        mock_resolve_hydrophone.return_value = (
            "orcasound_lab",
            FakeDailyNoiseAnalysis,
            FakeHydrophone(),
        )

        with self.assertRaisesRegex(ValueError, "exceeds the limit"):
            get_daily_summary(
                "orcasound_lab",
                dt.date(2020, 1, 1),
                30,
                63,
                8000,
                interval="10s",
            )


if __name__ == "__main__":
    unittest.main()

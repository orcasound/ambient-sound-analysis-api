import datetime as dt
import unittest
from unittest.mock import patch

import pandas as pd

from app.models.responses import FrequencyBandOptions, HydrophoneOptions, TimeResolutionOptions
from app.services.get_timeseries import (
    TimeseriesDataIntegrityError,
    get_broadband_timeseries,
    get_psd_timeseries,
)


class GetTimeseriesTests(unittest.TestCase):
    @patch("app.services.get_timeseries._load_timeseries_df")
    @patch("app.services.get_timeseries._validate_broadband_request")
    def test_get_broadband_timeseries_skips_validation_when_disabled(
        self, mock_validate_broadband_request, mock_load_timeseries_df
    ):
        class FakeHydrophone:
            name = "SANDBOX"

        df = pd.DataFrame(
            {"0": [1.2, 1.4]},
            index=[dt.datetime(2026, 1, 27, 0, 0, 0), dt.datetime(2026, 1, 27, 0, 0, 1)],
        )
        mock_load_timeseries_df.return_value = (FakeHydrophone(), df)

        result = get_broadband_timeseries(
            "sandbox",
            dt.datetime(2026, 1, 27, 0, 0, 0),
            dt.datetime(2026, 1, 27, 0, 1, 0),
            1,
            validate=False,
        )

        mock_validate_broadband_request.assert_not_called()
        self.assertEqual(len(result.points), 2)

    @patch("app.services.get_timeseries._get_options_for_hydrophone")
    def test_get_psd_timeseries_rejects_invalid_combination(self, mock_get_options_for_hydrophone):
        mock_get_options_for_hydrophone.return_value = HydrophoneOptions(
            hydrophone="sandbox",
            broadband=[],
            octave_bands=[],
            delta_hz=[
                FrequencyBandOptions(
                    delta_f=500,
                    delta_t=10,
                    first_start="2023-02-10T05:00:00",
                    last_end="2023-02-10T15:00:00",
                    file_count=1,
                )
            ],
        )

        with self.assertRaisesRegex(ValueError, "No PSD combination"):
            get_psd_timeseries(
                "sandbox",
                dt.datetime(2023, 2, 10, 0, 0, 0),
                dt.datetime(2023, 2, 11, 0, 0, 10),
                1,
                "50hz",
                validate=True,
            )

    @patch("app.services.get_timeseries._get_options_for_hydrophone")
    def test_get_psd_timeseries_rejects_out_of_coverage_window(self, mock_get_options_for_hydrophone):
        mock_get_options_for_hydrophone.return_value = HydrophoneOptions(
            hydrophone="sandbox",
            broadband=[],
            octave_bands=[
                FrequencyBandOptions(
                    delta_f=3,
                    delta_t=1,
                    first_start="2020-01-01T00:00:00",
                    last_end="2021-11-01T00:00:00",
                    file_count=22,
                )
            ],
            delta_hz=[],
        )

        with self.assertRaisesRegex(ValueError, "outside the coverage area"):
            get_psd_timeseries(
                "sandbox",
                dt.datetime(2026, 1, 27, 0, 0, 0),
                dt.datetime(2026, 1, 27, 0, 10, 0),
                1,
                "3oct",
                validate=True,
            )

    @patch("app.services.get_timeseries._matching_file_count", return_value=1)
    @patch("app.services.get_timeseries._import_orcasound_noise")
    def test_load_timeseries_df_raises_data_integrity_error_when_file_matches_but_rows_do_not(
        self, mock_import_orcasound_noise, mock_matching_file_count
    ):
        class FakeHydrophoneEnum:
            SANDBOX = object()

            def __getitem__(self, key):
                return getattr(self, key)

        class FakeAccessor:
            def __init__(self, hydrophone):
                self.hydrophone = hydrophone

            def create_df(self, **kwargs):
                return pd.DataFrame(columns=["0"])

        mock_import_orcasound_noise.return_value = (FakeAccessor, FakeHydrophoneEnum(), object())

        from app.services.get_timeseries import _load_timeseries_df

        with self.assertRaises(TimeseriesDataIntegrityError):
            _load_timeseries_df(
                "sandbox",
                dt.datetime(2023, 2, 10, 0, 0, 0),
                dt.datetime(2023, 2, 11, 0, 0, 10),
                10,
                "500hz",
                detect_data_integrity=True,
            )


if __name__ == "__main__":
    unittest.main()

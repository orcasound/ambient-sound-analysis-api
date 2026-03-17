import unittest
from unittest.mock import patch

from app.models.responses import FrequencyBandOptions, HydrophoneOptions, TimeResolutionOptions
from app.services import get_options


class GetOptionsTests(unittest.TestCase):
    @patch("app.services.get_options._scan_hydrophone_archive")
    @patch("app.services.get_options._import_orcasound_noise")
    def test_get_options_for_hydrophone_builds_split_response(
        self, mock_import_orcasound_noise, mock_scan_hydrophone_archive
    ):
        class FakeHydrophone:
            def __init__(self, name):
                self.name = name

        class FakeHydrophoneEnum:
            SANDBOX = FakeHydrophone("SANDBOX")

            def __getitem__(self, key):
                return getattr(self, key)

        mock_import_orcasound_noise.return_value = (object(), FakeHydrophoneEnum(), object())
        mock_scan_hydrophone_archive.return_value = {
            "broadband": {
                1: {
                    "starts": [],
                    "ends": [],
                    "file_count": 2,
                }
            },
            "octave_bands": {
                (3, 1): {
                    "starts": [],
                    "ends": [],
                    "file_count": 4,
                }
            },
            "delta_hz": {
                (500, 10): {
                    "starts": [],
                    "ends": [],
                    "file_count": 1,
                }
            },
        }

        result = get_options._get_options_for_hydrophone("sandbox")

        self.assertIsInstance(result, HydrophoneOptions)
        self.assertEqual(result.hydrophone, "sandbox")
        self.assertEqual(result.broadband[0].delta_t, 1)
        self.assertEqual(result.broadband[0].file_count, 2)
        self.assertEqual(result.octave_bands[0].delta_f, 3)
        self.assertEqual(result.octave_bands[0].delta_t, 1)
        self.assertEqual(result.delta_hz[0].delta_f, 500)
        self.assertEqual(result.delta_hz[0].delta_t, 10)

    @patch("app.services.get_options._get_options_for_hydrophone")
    @patch("app.services.get_options._cached_available_hydrophones")
    def test_get_options_filters_single_hydrophone(
        self, mock_cached_available_hydrophones, mock_get_options_for_hydrophone
    ):
        mock_cached_available_hydrophones.return_value = ("sandbox", "orcasound_lab")
        mock_get_options_for_hydrophone.return_value = HydrophoneOptions(
            hydrophone="sandbox",
            broadband=[TimeResolutionOptions(delta_t=1, first_start=None, last_end=None, file_count=1)],
            octave_bands=[],
            delta_hz=[],
        )

        result = get_options.get_options("sandbox")

        self.assertEqual(len(result.hydrophones), 1)
        self.assertEqual(result.hydrophones[0].hydrophone, "sandbox")
        mock_get_options_for_hydrophone.assert_called_once_with("sandbox")


if __name__ == "__main__":
    unittest.main()

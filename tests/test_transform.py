import os
import unittest
from unittest import mock

import ddt
import philter_lite

from generative_philter_surrogates import Scrubber


@ddt.ddt
class TestTransformUnit(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        with mock.patch("generative_philter_surrogates.philter.Scrubber._init_config", return_value=None):
            self.scrubber = Scrubber(seed=1, debug=True)

    def test_multiple_transform(self):
        tracker = philter_lite.philter.DataTracker(
            "Call Ms Jane Smith at 555-123-4567",
            [
                philter_lite.philter.PhiEntry(8, 18, "", "NAME"),
                philter_lite.philter.PhiEntry(22, 34, "", "PHONE"),
            ],
            []
        )
        transformed = self.scrubber.transform_text_surrogates(tracker)
        self.assertEqual("Call Ms Lisa Ellis at 070-434-1925", transformed)

    def test_too_small(self):
        tracker = philter_lite.philter.DataTracker(
            "555",
            [
                philter_lite.philter.PhiEntry(0, 3, "", "PHONE"),
            ],
            []
        )
        transformed = self.scrubber.transform_text_surrogates(tracker)
        self.assertEqual("281", transformed)

    def test_too_big(self):
        tracker = philter_lite.philter.DataTracker(
            "555-123-4567-8901-2345-6789",
            [
                philter_lite.philter.PhiEntry(0, 27, "", "PHONE"),
            ],
            []
        )
        transformed = self.scrubber.transform_text_surrogates(tracker)
        self.assertEqual("665.894.7847x093665.894.784", transformed)

    # "ADDRESS_CITY",
    # "ADDRESS_STREET",
    # "AGE",
    # "CONTACT",  # email, phone number, etc
    # "DATE",
    # "ID",  # MRN, social security number, etc
    # "LOCATION",  # hospital names, etc
    # "NAME",
    @ddt.data(
        # PHI type, expected
        ("ADDRESS_CITY", "West Davidmouth"),
        ("ADDRESS_STREET", "648 Smith Ridge"),
        ("NAME", "Jeffrey Simpson"),
        ("PHONE", "+1-963-745-7913"),
    )
    @ddt.unpack
    def test_phi_type(self, phi_type, expected):
        tracker = philter_lite.philter.DataTracker(
            "0" * 15,
            [
                philter_lite.philter.PhiEntry(0, 15, "", phi_type),
            ],
            []
        )
        transformed = self.scrubber.transform_text_surrogates(tracker)
        self.assertEqual(expected, transformed)


@ddt.ddt
class TestTransformIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.scrubber = Scrubber(seed=2, debug=True)

    def setUp(self):
        super().setUp()
        self.maxDiff = None  # pylint:

    @ddt.data(
        "variety", "curated", "synthetic"
    )
    def test_transform_integration(self, filename):
        sample_data = open(f"{os.path.dirname(__file__)}/{filename}.in", "r").read()
        expected_response = open(f"{os.path.dirname(__file__)}/{filename}.out", "r").read()
        transformed = self.scrubber.scrub_text(sample_data)
        print(transformed)  # keep this around -- it's easier to copy and past result when changes happen
        self.assertEqual(expected_response, transformed)

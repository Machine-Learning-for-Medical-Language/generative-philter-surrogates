"""Philter integration"""

import functools
import os
from typing import Callable, List, Optional

import faker
import rich
import rich.table

import nltk
import philter_lite


class Scrubber:
    # NOTE: the order of the types here will affect the resulting order of PHI entries.
    #       Meaning that if you reorder these, you'll get different prioritization of surrogates.
    PHI_TYPES = [
        "NAME",  # this catches a lot of address pieces too, so run it first
        "CITY",
        "STREET",
        "HOSPITAL",  # hospital names, etc

        "URL",  # this catches emails too, so run it before email
        "EMAIL",

        "AGE",
        "ID",  # MRN, etc
        "SSN",
        "PHONE",
        "DATE",  # ID will catch dates too
    ]

    def __init__(self, seed: int = None, debug: bool = False, asterisk: bool = False):
        self.fake = faker.Faker()
        self.fake.seed_instance(seed)
        self.cache = {}
        self.filters = self._init_config()
        self.debug = debug
        self.asterisk = asterisk

    @staticmethod
    def _init_config():
        # Ensure all the nltk data that our filter_config (below) needs is available.
        #nltk.download("averaged_perceptron_tagger", quiet=True)
        filter_config = os.path.join(os.path.dirname(__file__), "resources", "philter_config.toml")
        return philter_lite.load_filters(filter_config)

    def scrub_text(self, text: str) -> str:
        return self.transform_text_surrogates(self.detect_phi(text))

    def detect_phi(self, text: str) -> philter_lite.philter.DataTracker:
        _, _, tracker = philter_lite.detect_phi(text, self.filters, phi_type_list=self.PHI_TYPES)
        return tracker

    def transform_text_surrogates(self, tag_data: philter_lite.philter.DataTracker) -> str:
        """
        A drop-in replacement for philter_lite.transform_text_asterisk, but for surrogate data.

        For example:
         "Please call Ms Jane Smith at 555-123-4567" -> "Please call Ms Susy Jones at 617-142-1693"

        :param tag_data: the generated tracking data from philter_lite (3rd response from detect_phi)
        :returns: transformed text, with all PHI replaced by surrogate data of the same length
        """
        new_text = tag_data.text

        table = rich.table.Table(
            "Type",
            rich.table.Column(header="Original", overflow="fold"),
            rich.table.Column(header="Surrogate", overflow="fold"),
        )

        for entry in tag_data.phi:
            surrogate = self._generate_surrogate(entry.word, entry.phi_type, entry.stop - entry.start)
            table.add_row(entry.phi_type, entry.word, surrogate)
            new_text = self._replace_slice(new_text, entry.start, entry.stop, surrogate)

        if self.debug:
            rich.get_console().print(table)

        return new_text

    def _generate_surrogate(self, original: str, phi_type: str, length: int) -> Optional[str]:
        if self.asterisk:
            return "*" * length  # easy!

        methods = {
            # leave age & dates alone -- they won't confuse machine learning and leaving them in is still a valid
            # research use case (a HIPAA "limited data set")
            "AGE": None,
            "DATE": self.fake.date,

            "CITY": self.fake.city,
            "STREET": self.fake.street_address,
            "EMAIL": self.fake.email,
            "HOSPITAL": self.fake.company,
            "ID": functools.partial(self.fake.random_number, digits=length, fix_len=True),
            "NAME": self.fake.name if ' ' in original else self.fake.first_name,
            "PHONE": self.fake.phone_number,
            "SSN": self.fake.ssn,
            "URL": self.fake.url,
        }
        if phi_type in methods:
            method = methods[phi_type]
            if method is None:
                return original
            return self._generate_with_cache(phi_type, length, method)

        return "*" * length  # fall back to asterisks

    def _generate_with_cache(self, phi_type: str, length: int, generator: Callable[[], str], max_tries: int = 300) -> str:
        # Grab an existing one if it exists
        phi_len_list = self._get_cache(phi_type, length)
        if phi_len_list:
            return phi_len_list.pop()

        # OK, we don't have one. Generate a few options until we either find a match for length or hit max tries
        for i in range(max_tries):
            attempt = str(generator())
            attempt_len = len(attempt)
            if attempt_len == length:
                return attempt

            # Store it and try again
            self._get_cache(phi_type, attempt_len).append(attempt)

        # We could not find a surrogate of the appropriate length at all...
        # Either chop a generated attempt early or smash it together a bunch until we get the length we want.
        # This is bad, but :shrug: we're out of reasonable options
        attempt = str(generator())
        attempt_len = len(attempt)
        extras = length // attempt_len
        attempt = attempt + (attempt * extras).replace(" ", "").lower()
        return attempt[:length]

    def _get_cache(self, phi_type: str, length: int) -> List[str]:
        phi_cache = self.cache.setdefault(phi_type, {})
        return phi_cache.setdefault(length, [])

    @staticmethod
    def _replace_slice(text: str, start: int, end: int, new: str) -> str:
        return text[:start] + new + text[end:]

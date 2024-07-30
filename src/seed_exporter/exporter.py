"""Module containing seed exporter class."""

import logging as log
from dataclasses import dataclass

from seed_exporter.config import Config


@dataclass
class Exporter:
    """Class for exporting seed data."""

    conf: Config

    def run(self):
        """Export seed data."""

        log.info("Exporting seed data...")
        log.info("Not implemented: returning")

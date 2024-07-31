"""Module containing seed exporter class."""

import logging as log
from dataclasses import dataclass

from seed_exporter.config import Config
from seed_exporter.input import InputReader


@dataclass
class Exporter:
    """Class for exporting seed data."""

    conf: Config

    def run(self):
        """Export seed data."""

        log.debug("Starting export...")
        log.debug("Reading input data...")
        input_reader = InputReader(self.conf.crawler_path, self.conf.timestamp)
        df = input_reader.get_data()
        log.info("Data processing not implemented: returning")

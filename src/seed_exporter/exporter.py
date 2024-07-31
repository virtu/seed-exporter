"""Module containing seed exporter class."""

import logging as log
from dataclasses import dataclass

from seed_exporter.config import Config
from seed_exporter.input import InputReader
from seed_exporter.stats import DataProcessor


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

        log.debug("Processing input data...")
        processor = DataProcessor(df)
        df2 = processor.process_data()
        print(df2)

        log.info("Outputting data not implemented: returning")

"""Module containing seed exporter class."""

import logging as log
from dataclasses import dataclass

from seed_exporter.config import Config
from seed_exporter.input import CrawlerInputReader
from seed_exporter.output import FormattedOutputWriter
from seed_exporter.processing import DataProcessing


@dataclass
class Exporter:
    """Class for exporting seed data."""

    conf: Config

    def run(self):
        """Export seed data."""

        log.debug("Starting export...")
        log.debug("Reading input data...")
        input_reader = CrawlerInputReader(self.conf.crawler_path, self.conf.timestamp)
        df_input = input_reader.get_data()

        log.debug("Processing input data...")
        df_stats = DataProcessing.process_data(df_input)

        log.debug("Writing results...")
        writer = FormattedOutputWriter(self.conf.result_path, self.conf.timestamp)
        writer.write(df_stats)

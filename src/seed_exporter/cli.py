"""Command-line interface for the seed exporter."""

import logging as log
import time

from seed_exporter.config import get_config
from seed_exporter.exporter import Exporter


def main():
    """Parse command-line arguments, set up logging, and run seed exporter."""

    conf = get_config()
    log.basicConfig(
        level=conf.log_level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    log.Formatter.converter = time.gmtime
    log.info("Using configuration: %s", conf)

    exporter = Exporter(conf)
    exporter.run()

    log.info("Finished seed export")


if __name__ == "__main__":
    main()

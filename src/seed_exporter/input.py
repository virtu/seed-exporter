"""Module to read input data from p2p-crawler results."""

import datetime as dt
import logging as log
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class InputReader:
    """Class to read input data from p2p-crawler results."""

    path: str
    timestamp: dt.datetime

    def _find_matching_files(self, date_range) -> list[Path]:
        """Find relevant input files, ensuring data is available for the last 30 days."""
        matching_files = []
        for date in date_range:
            files = list(Path(self.path).glob(f"{date}T*reachable_nodes.csv.bz2"))
            if not files:
                raise FileNotFoundError(f"No data found for date: {date}")
            matching_files.extend(files)
        return matching_files

    def get_data(self) -> pd.DataFrame:
        """Read input files and return a combined DataFrame."""

        current_day = self.timestamp.date()
        date_range = [current_day - dt.timedelta(days=i) for i in range(30)]
        files = self._find_matching_files(date_range)
        log.debug("Found %s input files: %s", len(files), files)

        data_frames = []
        for file in files:
            timestamp = dt.datetime.fromisoformat(file.name.split("Z_")[0])
            df = pd.read_csv(file)
            log.debug("Read %s rows from %s", len(df), file)
            df["timestamp"] = timestamp
            data_frames.append(df)
        combined_df = pd.concat(data_frames).set_index("timestamp")
        log.debug(
            "Consolidated %s data frames with %s rows",
            len(data_frames),
            len(combined_df),
        )
        return combined_df

"""Module to read input data from p2p-crawler results."""

import datetime as dt
import logging as log
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class InputReader:
    """Class to read input data from p2p-crawler results."""

    path: Path
    timestamp: dt.datetime

    def _find_matching_files(self, date_range) -> list[Path]:
        """Find relevant input files, ensuring data is available for the last 30 days."""
        matching_files = []
        for date in date_range:
            files = list(self.path.glob(f"{date}T*reachable_nodes.csv.bz2"))
            if not files:
                raise FileNotFoundError(f"No data found for date: {date}")
            matching_files.extend(files)
        return matching_files

    @staticmethod
    def postprocess_data(df: pd.DataFrame) -> pd.DataFrame:
        """Perform post-processing:
        1. Ensure DateTimeIndex
        2. Rename host column to address
        3. Drop nodes who did not complete the handshake
        4. Replace missing user-agent data with "(empty)"
        """

        df.index = pd.to_datetime(df.index)
        df.rename(columns={"host": "address"}, inplace=True)
        num_total = len(df)
        df = df[df["handshake_successful"] == True]
        num_valid = len(df)
        df.loc[df["user_agent"].isnull(), "user_agent"] = "(empty)"
        log.debug(
            "Dropping nodes with failed handshake (original=%d, dropped=%d, remaining=%d)",
            num_total,
            num_total - num_valid,
            num_valid,
        )
        return df

    def get_data(self) -> pd.DataFrame:
        """Read input files and return a combined DataFrame."""

        current_day = self.timestamp.date()
        date_range = [current_day - dt.timedelta(days=i) for i in range(30)]
        files = self._find_matching_files(date_range)
        log.debug("Found %s input files: %s", len(files), [f.name for f in files])

        time_start = dt.datetime.now()
        data_frames = []
        for file in files:
            timestamp_str = file.name.split("Z_")[0]
            timestamp = dt.datetime.strptime(timestamp_str, "%Y-%m-%dT%H-%M-%S")
            df = pd.read_csv(file)
            log.debug("Read %s rows from %s", len(df), file)
            df["timestamp"] = timestamp
            data_frames.append(df)
        combined_df = pd.concat(data_frames).set_index("timestamp")
        result = InputReader.postprocess_data(combined_df)

        elapsed = dt.datetime.now() - time_start
        log.info(
            "Consolidated %s rows from %d files in %.2fs",
            len(result),
            len(files),
            elapsed.total_seconds(),
        )
        return result

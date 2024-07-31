"""Module for processing data and calculating statistics."""

import datetime as dt
import logging as log
from dataclasses import dataclass

import pandas as pd


@dataclass
class DataProcessor:
    """Class for processing data and calculating statistics."""

    data: pd.DataFrame

    def _calculate_share(
        self, window_name: str, window_delta: dt.timedelta
    ) -> pd.DataFrame:
        """
        Calculate the share of unique timestamps containing each address, port pair within the given time delta.
        """
        end_time = self.data.index.max()
        start_time = end_time - window_delta

        filtered_df = self.data[
            (self.data.index >= start_time) & (self.data.index <= end_time)
        ]
        if filtered_df.empty:
            return pd.DataFrame(columns=["address", "port", window_name])

        total_timestamps = filtered_df.index.nunique()
        grouped = (
            filtered_df.groupby(["address", "port"])
            .size()
            .to_frame("count")
            .reset_index()
        )
        grouped[window_name] = grouped["count"] / total_timestamps
        grouped = grouped.drop(columns=["count"])

        return grouped

    def _get_latest_info(self) -> pd.DataFrame:
        """
        Extract the latest information for each unique address, port pair.
        """
        latest_entries = self.data.groupby(["address", "port"]).nth(-1).reset_index()
        metadata = latest_entries[
            [
                "address",
                "port",
                "handshake_timestamp",
                "services",
                "latest_block",
                "version",
                "user_agent",
            ]
        ].copy()

        log.debug("Renaming selection...")
        metadata.rename(
            columns={
                "handshake_timestamp": "lastSuccess",
                "services": "svcs",
                "latest_block": "blocks",
            },
            inplace=True,
        )
        metadata["version"] = (
            metadata["version"].astype(str) + " " + metadata["user_agent"]
        )

        return metadata[["address", "port", "lastSuccess", "svcs", "blocks", "version"]]

    def process_data(self) -> pd.DataFrame:
        """
        Process the dataframe to calculate the share of appearances of each unique address, port pair
        in different time windows.
        """
        windows = {
            "last_2_hours": dt.timedelta(hours=2),
            "last_8_hours": dt.timedelta(hours=8),
            "last_day": dt.timedelta(days=1),
            "last_7_days": dt.timedelta(days=7),
            "last_30_days": dt.timedelta(days=30),
        }

        results = pd.DataFrame(columns=["address", "port"])

        log.info("Computing share of appearances in different time windows")
        for window_name, window_delta in windows.items():
            log.debug("Processing window: %s", window_name)
            window_result = self._calculate_share(window_name, window_delta)
            results = pd.merge(
                results, window_result, on=["address", "port"], how="outer"
            )

        # address good  lastSuccess    %(2h)   %(8h)   %(1d)   %(7d)  %(30d)  blocks svcs version

        log.info("Finished computing shares")

        log.info("Getting metadata...")
        latest_info_df = self._get_latest_info()
        results = pd.merge(results, latest_info_df, on=["address", "port"], how="outer")

        return results.fillna(0)

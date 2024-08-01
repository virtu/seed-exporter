"""Module for processing data and calculating statistics."""

import datetime as dt
import logging as log

import pandas as pd


class DataProcessing:
    """Class for processing data and calculating statistics."""

    @staticmethod
    def compute_availability_shares(
        df: pd.DataFrame, window_name: str, window_delta: dt.timedelta
    ) -> pd.DataFrame:
        """
        Calculate availability share for each node (address-port pair) in the given time window.

        Begin by filtering the dataframe to only include entries within the
        given time window; exit early if window is empty. Next, group the
        filtered dataframe by node and count the number of timestamps each node
        appears in. Then, derive share.
        """

        df.index = pd.to_datetime(df.index)
        end_time = df.index.max()
        assert isinstance(end_time, pd.Timestamp), "end_time must be a pd.Timestamp"
        start_time = end_time - window_delta
        filtered_df = df[(df.index >= start_time) & (df.index <= end_time)]
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

    @staticmethod
    def get_metadata(df: pd.DataFrame) -> pd.DataFrame:
        """
        Get most recent metadata for each node (address-port pair).

        The most recent data for each node is obtained by grouping by node and
        selecting the last entry.

        For each node (address-port pair), the following metadata is included:
          - handshake_timestamp: the time of the last successful handshake
          - services: the services advertised by the node
          - latest_block: the latest block the node is aware of
          - version: the version of the node software
          - user_agent: the user agent of the node software
        """
        selection = [
            "address",
            "port",
            "handshake_timestamp",
            "services",
            "latest_block",
            "version",
            "user_agent",
        ]

        latest_entries = df.groupby(["address", "port"]).nth(-1).reset_index()
        metadata = latest_entries.loc[:, selection].copy()
        return metadata

    @staticmethod
    def process_data(df_input: pd.DataFrame) -> pd.DataFrame:
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

        log.debug("Computing node availability shares for different time windows")
        results = pd.DataFrame(columns=["address", "port"])
        for window_name, window_size in windows.items():
            log.debug("Processing window: %s", window_name)
            window_result = DataProcessing.compute_availability_shares(
                df_input, window_name, window_size
            )
            results = pd.merge(
                results, window_result, on=["address", "port"], how="outer"
            )

        log.debug("Extracting metadata...")
        metadata = DataProcessing.get_metadata(df_input)
        results = pd.merge(results, metadata, on=["address", "port"], how="outer")

        # postprocessing
        # 1. fill in nan values in the availability shares columns
        # 2. ensure there's no nan records in the remaining columns
        share_cols = list(windows.keys())
        results[share_cols] = results[share_cols].fillna(0)
        nan_rows = results[results.isna().any(axis=1)]
        if not nan_rows.empty:
            error_str = f"Missing metadata in {len(nan_rows)} row(s):"
            for _, row in nan_rows.iterrows():
                nan_columns = row.index[row.isna()].tolist()
                address, port = row["address"], row["port"]
                error_str += f"\n{address}:{port}: {nan_columns}"
            raise ValueError(f"Missing (meta)data: {error_str}")
        return results

"""Module for processing data and calculating statistics."""

import datetime as dt
import logging as log
from dataclasses import dataclass
from typing import ClassVar

import pandas as pd

from seed_exporter.input import InputColumns as InCol


@dataclass(frozen=True)
class StatsColumns:
    """Mappings for statistics columns."""

    GOOD: ClassVar[str] = "good"
    AVAILABILITY_2H: ClassVar[str] = "availability_2_hours"
    AVAILABILITY_8H: ClassVar[str] = "availability_8_hours"
    AVAILABILITY_1D: ClassVar[str] = "availability_1_day"
    AVAILABILITY_7D: ClassVar[str] = "availability_7_days"
    AVAILABILITY_30D: ClassVar[str] = "availability_30_days"


@dataclass
class DataProcessing:
    """Class for processing data and calculating statistics.

    Computes node availability statistics for each node (address-port pair) seen
    in the input data.

    In addition to statistics, the following metadata is included for each node
      - handshake_timestamp: the time of the last successful handshake
      - services: the services advertised by the node
      - latest_block: the latest block the node is aware of
      - version: the version of the node software
      - user_agent: the user agent of the node software
    """

    METADATA_COLS: ClassVar[list] = [
        InCol.IP_ADDRESS,
        InCol.PORT,
        InCol.TIMESTAMP,
        InCol.SERVICES,
        InCol.BLOCKS,
        InCol.VERSION,
        InCol.USER_AGENT,
    ]

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
            return pd.DataFrame(columns=[InCol.IP_ADDRESS, InCol.PORT, window_name])

        total_timestamps = filtered_df.index.nunique()
        grouped = (
            filtered_df.groupby([InCol.IP_ADDRESS, InCol.PORT])
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
        """
        latest_entries = (
            df.groupby([InCol.IP_ADDRESS, InCol.PORT]).nth(-1).reset_index()
        )
        metadata = latest_entries.loc[:, DataProcessing.METADATA_COLS].copy()
        return metadata

    @staticmethod
    def process_data(df_input: pd.DataFrame) -> pd.DataFrame:
        """
        Process the dataframe to calculate the availability of all nodes for
        different time windows, and add latest metadata for each node.
        """
        windows = {
            StatsColumns.AVAILABILITY_2H: dt.timedelta(hours=2),
            StatsColumns.AVAILABILITY_8H: dt.timedelta(hours=8),
            StatsColumns.AVAILABILITY_1D: dt.timedelta(days=1),
            StatsColumns.AVAILABILITY_7D: dt.timedelta(days=7),
            StatsColumns.AVAILABILITY_30D: dt.timedelta(days=30),
        }

        log.debug("Computing node availability shares for different time windows")
        results = pd.DataFrame(columns=[InCol.IP_ADDRESS, InCol.PORT])
        for window_name, window_size in windows.items():
            log.debug("Processing window: %s", window_name)
            window_result = DataProcessing.compute_availability_shares(
                df_input, window_name, window_size
            )
            results = pd.merge(
                results, window_result, on=[InCol.IP_ADDRESS, InCol.PORT], how="outer"
            )

        log.debug("Extracting metadata...")
        metadata = DataProcessing.get_metadata(df_input)
        results = pd.merge(
            results, metadata, on=[InCol.IP_ADDRESS, InCol.PORT], how="outer"
        )

        # postprocessing
        # 1. fill in nan values in the availability shares columns
        # 2. ensure there's no nan records in the remaining columns
        # 3. add 'good' column (presume all nodes to be good)
        share_cols = list(windows.keys())
        results[share_cols] = results[share_cols].fillna(0)
        nan_rows = results[results.isna().any(axis=1)]
        if not nan_rows.empty:
            error_str = f"Missing metadata in {len(nan_rows)} row(s):"
            for _, row in nan_rows.iterrows():
                nan_columns = row.index[row.isna()].tolist()
                address, port = row[InCol.IP_ADDRESS], row[InCol.PORT]
                error_str += f"\n{address}:{port}: {nan_columns}"
            raise ValueError(f"Missing (meta)data: {error_str}")
        # Todo: implement
        results[StatsColumns.GOOD] = 1
        return results

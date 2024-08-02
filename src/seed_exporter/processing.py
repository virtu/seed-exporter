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
            .to_frame(window_name + "_count")
            .reset_index()
        )

        grouped[window_name] = grouped[window_name + "_count"] / total_timestamps
        return grouped

    @staticmethod
    def get_metadata(df: pd.DataFrame) -> pd.DataFrame:
        """
        Get most recent metadata for each node (address-port pair).

        The most recent data for each node is obtained by grouping by node and
        selecting the last entry.
        """
        df_meta = df.groupby([InCol.IP_ADDRESS, InCol.PORT]).nth(-1).reset_index()
        return df_meta

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

        log.debug("Filling in missing availability values...")
        share_cols = list(windows.keys()) + [col + "_count" for col in windows]
        results[share_cols] = results[share_cols].fillna(0)

        log.debug("Ensuring no data is missing...")
        nan_rows = results[results.isna().any(axis=1)]
        if not nan_rows.empty:
            error_str = f"Missing metadata in {len(nan_rows)} row(s):"
            for _, row in nan_rows.iterrows():
                nan_columns = row.index[row.isna()].tolist()
                address, port = row[InCol.IP_ADDRESS], row[InCol.PORT]
                error_str += f"\n{address}:{port}: {nan_columns}"
            raise ValueError(f"Missing (meta)data: {error_str}")

        log.debug("Evaluating node quality...")
        results[StatsColumns.GOOD] = DataProcessing.is_good(results)
        return results

    @staticmethod
    def is_good(df: pd.DataFrame) -> pd.Series:
        """
        Evaluate node quality: good vs. bad.

        Define a quality function and apply it to each column using df.apply().

        Inspired by https://github.com/sipa/bitcoin-seeder/blob/ff482e465ff84ea6fa276d858ccb7ef32e3355d3/db.h#L104-L119.
        """

        default_ports = [0, 8333]  # beware of i2p, which does not use a port
        node_network = 1 << 0
        version_threshold = 70001
        # if the block was seen during the last 30 days, it should not be more
        # than 100 days of blocks behind the median blocks of other nodes
        block_threshold = df[InCol.BLOCKS].median() - 100 * 24 * 6

        def is_good_node(row: pd.DataFrame) -> bool:
            """Evaluate node quality for a single node/row."""
            if row[InCol.PORT] not in default_ports:
                return False

            # the goal is to get peers, not blocks from the node, so this
            # requirement might unnecessarily limit the node pool
            # if not row[InCol.PORT] & node_network:
            #     return False
            #

            if row[InCol.VERSION] < version_threshold:
                return False

            if row[InCol.BLOCKS] < block_threshold:
                return False

            # Not sure about this. We wouldn't want to allow a node we've
            # observed only a couple of times even it was reachable more than
            # half of the time if that was a month ago
            # if (total <= 3 && success * 2 >= total)
            #     return True

            def has_reliablility(window: str, share: float, count: int):
                """Check if the node has been reliable in the given time window."""
                return row[window] > share and row[window + "_count"] > count

            if (
                has_reliablility(StatsColumns.AVAILABILITY_2H, 0.85, 2)
                or has_reliablility(StatsColumns.AVAILABILITY_8H, 0.70, 4)
                or has_reliablility(StatsColumns.AVAILABILITY_1D, 0.55, 8)
                or has_reliablility(StatsColumns.AVAILABILITY_7D, 0.45, 16)
                or has_reliablility(StatsColumns.AVAILABILITY_30D, 0.35, 32)
            ):
                return True
            return False

        good_col = df.apply(is_good_node, axis=1)

        log.info(
            "Node analysis: network=%-9s total=%-8d good=%-8d share=%.1f%%",
            "all",
            len(df),
            good_col.sum(),
            good_col.mean() * 100,
        )
        for net_type in ["ipv4", "ipv6", "onion_v3", "i2p", "cjdns"]:
            df_net_good = df[good_col][df[good_col][InCol.NETWORK] == net_type]
            df_net_all = df[df[InCol.NETWORK] == net_type]
            num_good = len(df_net_good)
            num_total = len(df_net_all)
            share_good = num_good / num_total if num_total > 0 else 0
            log.info(
                "               network=%-9s total=%-8d good=%-8d share=%.1f%%",
                net_type,
                num_total,
                num_good,
                share_good * 100,
            )

        return good_col

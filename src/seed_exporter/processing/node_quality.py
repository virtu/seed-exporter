"""Module for processing data and calculating statistics."""

import logging as log
from dataclasses import dataclass
from typing import ClassVar

import pandas as pd

from seed_exporter.input import InputColumns as InCol

from .columns import StatsColumns


@dataclass(frozen=True)
class NodeQuality:
    """Class for evaluating node quality."""

    DEFAULT_PORT: ClassVar[int] = 8333
    NODE_NETWORK: ClassVar[int] = 1 << 0
    VERSION_THRESHOLD: ClassVar[int] = 70001
    CONNECTION_TIMEOUTS: ClassVar[dict[str, float]] = {
        "regular": 5 * 1000 * 0.5,  # 5s - 50% (prefer responsive nodes)
        "socks5": 20 * 1000 * 1.2,  # 20s + 20% (address performance fluctuations)
    }

    @staticmethod
    def considered_reliable(row: pd.DataFrame) -> bool:
        """Evaluate if the node is considered reliable."""

        def was_reliable(window: str, share: float, count: int):
            """Check if the node has been reliable in the given time window."""
            return row[window] > share and row[StatsColumns.count(window)] > count

        return (
            was_reliable(StatsColumns.AVAILABILITY_2H, 0.85, 2)
            or was_reliable(StatsColumns.AVAILABILITY_8H, 0.70, 4)
            or was_reliable(StatsColumns.AVAILABILITY_1D, 0.55, 8)
            or was_reliable(StatsColumns.AVAILABILITY_7D, 0.45, 16)
            or was_reliable(StatsColumns.AVAILABILITY_30D, 0.35, 32)
        )

    @staticmethod
    def get_block_threshold(df: pd.DataFrame) -> int:
        """
        Estimate block threshold:

        If the node was online during the last 30 days, it should not be more
        than 100 days of blocks behind the median of other nodes' blocks.
        """

        return df[InCol.BLOCKS].median() - 100 * 24 * 6

    @staticmethod
    def uses_standard_port(row: pd.DataFrame) -> bool:
        """
        Determine if node uses default port (8333 for all network types except
        I2P, which uses dummy port 0).
        """
        if row[InCol.NETWORK] != "i2p" and row[InCol.PORT] == NodeQuality.DEFAULT_PORT:
            return True
        if row[InCol.NETWORK] == "i2p" and row[InCol.PORT] == 0:
            return True
        return False

    @staticmethod
    def exceeds_timeouts(row: pd.DataFrame) -> bool:
        """
        Determine if node exceeds connection timeouts (see NodeQuality.CONNECTION_TIMEOUTS).
        """
        if row[InCol.NETWORK] in ("onion_v3", "i2p"):
            if row[InCol.CONNECTION_TIME] < NodeQuality.CONNECTION_TIMEOUTS["socks5"]:
                return False
        if row[InCol.CONNECTION_TIME] < NodeQuality.CONNECTION_TIMEOUTS["regular"]:
            return False
        return True

    @staticmethod
    def evaluate(df: pd.DataFrame) -> pd.Series:
        """
        Evaluate node quality: good vs. bad.

        Inspired by https://github.com/sipa/bitcoin-seeder/blob/ff482e465ff84ea6fa276d858ccb7ef32e3355d3/db.h#L104-L119.
        """

        def evaluate_node(row: pd.DataFrame) -> bool:
            """Evaluate node quality for a single node/row."""

            if not NodeQuality.uses_standard_port(row):
                return False

            if not row[InCol.PORT] & NodeQuality.NODE_NETWORK:
                return False

            if row[InCol.VERSION] < NodeQuality.VERSION_THRESHOLD:
                return False

            if row[InCol.BLOCKS] < NodeQuality.get_block_threshold(df):
                return False

            if NodeQuality.exceeds_timeouts(row):
                return False

            # Not sure about this. We wouldn't want to allow a node we've
            # observed only a couple of times even it was reachable more than
            # half of the time if that was a month ago
            # if (total <= 3 && success * 2 >= total)
            #     return True

            if NodeQuality.considered_reliable(row):
                return True

            return False

        good_col = df.apply(evaluate_node, axis=1)

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

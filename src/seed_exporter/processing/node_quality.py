"""Module for processing data and calculating statistics."""

import logging as log
from collections import defaultdict
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
    STATS: ClassVar[defaultdict] = defaultdict(lambda: defaultdict(lambda: 0))

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

            NodeQuality.STATS[row[InCol.NETWORK]]["total"] += 1

            if not NodeQuality.uses_standard_port(row):
                NodeQuality.STATS[row[InCol.NETWORK]]["port"] += 1
                return False

            if not row[InCol.SERVICES] & NodeQuality.NODE_NETWORK:
                NodeQuality.STATS[row[InCol.NETWORK]]["services"] += 1
                return False

            if row[InCol.VERSION] < NodeQuality.VERSION_THRESHOLD:
                NodeQuality.STATS[row[InCol.NETWORK]]["version"] += 1
                return False

            if row[InCol.BLOCKS] < NodeQuality.get_block_threshold(df):
                NodeQuality.STATS[row[InCol.NETWORK]]["blocks"] += 1
                return False

            if NodeQuality.exceeds_timeouts(row):
                NodeQuality.STATS[row[InCol.NETWORK]]["timeout"] += 1
                return False

            # Not sure about this. We wouldn't want to allow a node we've
            # observed only a couple of times even it was reachable more than
            # half of the time if that was a month ago
            # if not (total <= 3 && success * 2 >= total)
            #     return False

            if not NodeQuality.considered_reliable(row):
                NodeQuality.STATS[row[InCol.NETWORK]]["reliability"] += 1
                return False

            NodeQuality.STATS[row[InCol.NETWORK]]["good"] += 1
            return True

        good_col = df.apply(evaluate_node, axis=1)

        NodeQuality.log_statistics()

        return good_col

    @staticmethod
    def log_statistics():
        """Log node evaluation statistics."""

        def log_aligned(fmt, *args):
            """Helper functions to log columns with alignment."""
            log.info(fmt, *[str(arg) for arg in args])

        cols = [
            "Network",
            "Total",
            "Good",
            "Share",
            "Port",
            "Services",
            "Version",
            "Blocks",
            "Timeout",
            "Reliability",
        ]

        # Create format string
        # First row is left-aligned, other columns are right-aligned.
        # Add extra whitespace to all column header string lengths and make
        # sure second to last columns have minimum width of 6.
        fmt = f"%-{len(cols[0])+1}s "
        padding = [max(len(col) + 1, 6) for col in cols[1:]]
        fmt = fmt + " ".join([f"%{pad}s" for pad in padding])

        log.info("Evaluation statistics:")
        log_aligned(fmt, *cols)
        for net_type in ["ipv4", "ipv6", "onion_v3", "i2p", "cjdns"]:
            stats = NodeQuality.STATS[net_type]
            good_share = stats["good"] / stats["total"] if stats["total"] > 0 else 0
            good_share = f"{good_share:.1%}"
            log_aligned(
                fmt,
                net_type if net_type != "onion_v3" else "onion",
                stats["total"],
                stats["good"],
                good_share,
                stats["port"],
                stats["services"],
                stats["version"],
                stats["blocks"],
                stats["timeout"],
                stats["reliability"],
            )

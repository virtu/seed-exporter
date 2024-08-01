"""Module to write seed exporter results."""

import datetime as dt
import logging as log
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd


@dataclass
class OutputColumn:

    """Class representing an output columns.

    name: name of the column in the output file
    alignment: < or > for left or right alignment
    max_width: maximum width of the column

    Columns can either:
    - come from a column by another name
      - sometimes without any transformation
      - sometimes with a type cast
      - sometimes with a transformation (float to % string, string to quote-surrounded-string, hex-value)
    - be constructed from multiple columns

    Figure out how to cover all of these as simply as possible.
    """

    name: str
    generator: Callable
    alignment: str = ">"


OutputColumns = [
    OutputColumn(
        name="address",
        generator=(
            lambda row: f"[{row['address']}]:{row['port']}"
            if ":" in row["address"]
            else f"{row['address']}:{row['port']}"
        ),
        alignment="<",
    ),
    OutputColumn(name="lastSuccess", generator=lambda row: row["handshake_timestamp"]),
    OutputColumn(name="%(2h)", generator=lambda row: f"{row['last_2_hours']:.2%}"),
    OutputColumn(name="%(8h)", generator=lambda row: f"{row['last_8_hours']:.2%}"),
    OutputColumn(name="%(1d)", generator=lambda row: f"{row['last_day']:.2%}"),
    OutputColumn(name="%(7d)", generator=lambda row: f"{row['last_7_days']:.2%}"),
    OutputColumn(name="%(30d)", generator=lambda row: f"{row['last_30_days']:.2%}"),
    OutputColumn(name="svcs", generator=lambda row: f"{row['services']:08x}"),
    OutputColumn(name="blocks", generator=lambda row: int(row["latest_block"])),
    OutputColumn(
        name="version",
        generator=(lambda row: f"{int(row['version'])} \"row['user_agent']\""),
        alignment="<",
    ),
]


@dataclass
class OutputWriter:
    """Class to write seed exporter results."""

    path: Path
    timestamp: dt.datetime

    @staticmethod
    def _format_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply formatting expected by Bitcoin Core's makeseeds.py:

        # address                   good lastSuccess   %(2h)   %(8h)   %(1d)   %(7d)  %(30d)  blocks      svcs  version
        [2a01:4f9:1a:a966::2]:8333  1     1722411779 100.00% 100.00% 100.00% 100.00% 100.00%  854768  00000409  70016 "/Satoshi:22.0.0/"
        [2a01:4f8:272:4cd9::2]:8333 1     1722411841 100.00% 100.00% 100.00% 100.00% 100.00%  854768  00000409  70016 "/Satoshi:24.0.1/"

        Necessary steps:
        1. Rename columns
        2. Sort by "%(30d)" column (before converting to string)
        3. Format columns
        4. Combine address and port into single address, adding brackets where
           necessary (IPv6, CJDNS)
        5. Combine version and user_agent into single field
        6. Order columns
        """
        column_map = {
            "handshake_timestamp": "lastSuccess",
            "latest_block": "blocks",
            "services": "svcs",
            "last_2_hours": "%(2h)",
            "last_8_hours": "%(8h)",
            "last_day": "%(1d)",
            "last_7_days": "%(7d)",
            "last_30_days": "%(30d)",
        }
        df.rename(columns=column_map, inplace=True)

        # sort before converting float to string
        df = df.sort_values(by="%(30d)", ascending=False)

        for col in ["%(2h)", "%(8h)", "%(1d)", "%(7d)", "%(30d)"]:
            df[col] = df[col].apply(lambda x: f"{x:.2%}")

        df["svcs"] = df["svcs"].astype(int)
        df["svcs"] = df["svcs"].apply(lambda x: f"{x:08x}")

        df["address"] = df.apply(
            lambda row: f"[{row['address']}]:{row['port']}"
            if ":" in row["address"]
            else f"{row['address']}:{row['port']}",
            axis=1,
        )
        df.drop(columns=["port"], inplace=True)

        df["blocks"] = df["blocks"].astype(int)

        df["version"] = df["version"].astype(int)
        df["version"] = df["version"].astype(str) + " " + '"' + df["user_agent"] + '"'
        df.drop(columns=["user_agent"], inplace=True)

        # todo: add good once you know what that means
        df = df[
            [
                "address",
                "good",
                "lastSuccess",
                "%(2h)",
                "%(8h)",
                "%(1d)",
                "%(7d)",
                "%(30d)",
                "blocks",
                "svcs",
                "version",
            ]
        ]

        return df

    def write(self, df: pd.DataFrame):
        """Write results."""
        df_formatted = self._format_columns(df)
        timestamp_str = dt.datetime.strftime(self.timestamp, "%Y-%m-%dT%H-%M-%SZ")
        filename = self.path / f"seeds-{timestamp_str}.txt"
        # df_formatted.to_csv(filename, index=False)
        self._write_formatted(df_formatted, filename)
        log.info("Wrote %s rows to %s", len(df_formatted), filename)

    @staticmethod
    def _write_formatted(df: pd.DataFrame, filename: Path):
        alignments = {
            "address": "<",
            "lastSuccess": ">",
            "%(2h)": ">",
            "%(8h)": ">",
            "%(1d)": ">",
            "%(7d)": ">",
            "%(30d)": ">",
            "svcs": ">",
            "blocks": ">",
            "version": "<",
        }

        max_len = {
            col: max(df[col].astype(str).apply(len).max(), len(col))
            for col in df.columns
        }

        # Prefix "# " in header
        max_len["address"] -= 2

        header = " ".join(
            f"{col:{alignments.get(col, '>')}{max_len[col]}}" for col in df.columns
        )
        header = f"# {header}"

        # Prefix "# " in header
        max_len["address"] += 2

        # Format each row according to column specifications
        formatted_rows = [
            " ".join(
                f"{str(row[col]):{alignments.get(col, '>')}{max_len[col]}}"
                for col in df.columns
            ).rstrip()
            for _, row in df.iterrows()
        ]
        output = "\n".join([header] + formatted_rows)
        with Path.open(filename, "w", encoding="UTF8") as file:
            file.write(output)

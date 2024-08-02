"""Formatting used by FormattedOutputWriter."""

import logging as log
from dataclasses import dataclass
from typing import Callable, ClassVar, List

import pandas as pd

from seed_exporter.input import InputColumns as InCol
from seed_exporter.processing import StatsColumns as StatCol


@dataclass(frozen=True)
class OutCol:
    """Mappings for statistics columns."""

    SOCKET_ADDRESS: ClassVar[str] = "address"
    GOOD: ClassVar[str] = "good"
    TIMESTAMP: ClassVar[str] = "lastSuccess"
    AVAILABILITY_2H: ClassVar[str] = "%(2h)"
    AVAILABILITY_8H: ClassVar[str] = "%(8h)"
    AVAILABILITY_1D: ClassVar[str] = "%(1d)"
    AVAILABILITY_7D: ClassVar[str] = "%(7d)"
    AVAILABILITY_30D: ClassVar[str] = "%(30d)"
    SERVICES: ClassVar[str] = "svcs"
    BLOCKS: ClassVar[str] = "blocks"
    VERSION: ClassVar[str] = "version"
    USER_AGENT: ClassVar[str] = "useragent"


@dataclass
class ColFmt:

    """
    Class representing an column format for output columns.

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
    input: str | List[str]
    formatter: Callable
    align: str = ">"

    def format(self, df: pd.DataFrame):
        """Format the column in the dataframe."""
        if isinstance(self.input, str):
            return df[self.input].apply(self.formatter)
        return df.apply(lambda row: self.formatter(row[self.input]), axis=1)


@dataclass(frozen=True)
class ColumnFormatter:
    """Class to format columns."""

    COLUMNS: ClassVar[list[ColFmt]] = [
        ColFmt(
            OutCol.SOCKET_ADDRESS,
            [InCol.IP_ADDRESS, InCol.PORT],
            formatter=(
                lambda x: f"[{x.iloc[0]}]:{x.iloc[1]}"
                if ":" in x.iloc[0]
                else f"{x.iloc[0]}:{x.iloc[1]}"
            ),
            align="<",
        ),
        ColFmt(OutCol.GOOD, StatCol.GOOD, lambda x: f"{int(x)}"),
        ColFmt(OutCol.TIMESTAMP, InCol.TIMESTAMP, lambda x: f"{int(x)}"),
        ColFmt(OutCol.AVAILABILITY_2H, StatCol.AVAILABILITY_2H, lambda x: f"{x:.2%}"),
        ColFmt(OutCol.AVAILABILITY_8H, StatCol.AVAILABILITY_8H, lambda x: f"{x:.2%}"),
        ColFmt(OutCol.AVAILABILITY_1D, StatCol.AVAILABILITY_1D, lambda x: f"{x:.2%}"),
        ColFmt(OutCol.AVAILABILITY_7D, StatCol.AVAILABILITY_7D, lambda x: f"{x:.2%}"),
        ColFmt(OutCol.AVAILABILITY_30D, StatCol.AVAILABILITY_30D, lambda x: f"{x:.2%}"),
        ColFmt(OutCol.SERVICES, InCol.SERVICES, lambda x: f"{int(x):08x}"),
        ColFmt(OutCol.BLOCKS, InCol.BLOCKS, lambda x: f"{int(x)}"),
        ColFmt(OutCol.VERSION, InCol.VERSION, lambda x: f"{int(x)}"),
        ColFmt(OutCol.USER_AGENT, InCol.USER_AGENT, lambda x: f'"{x}"', align="<"),
    ]

    @staticmethod
    def format(df: pd.DataFrame) -> pd.DataFrame:
        """Get formatted columns, concatenated them and return dataframe."""
        formatted_cols = {}
        for col in ColumnFormatter.COLUMNS:
            log.debug("Formatting column %s", col.name)
            formatted_cols[col.name] = col.format(df)
        return pd.DataFrame(formatted_cols)

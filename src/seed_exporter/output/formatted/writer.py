"""Writer that outputs data in a makeseeds.py-compatible formatting."""

import datetime as dt
import logging as log
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pandas as pd

from seed_exporter.processing import StatsColumns

from .column_format import ColumnFormatter


@dataclass
class FormattedOutputWriter:
    """Writer that outputs data in a makeseeds.py-compatible formatting."""

    path: Path
    timestamp: dt.datetime
    SORT_KEY: ClassVar[str] = StatsColumns.AVAILABILITY_30D

    def write(self, df: pd.DataFrame):
        """Sort columns, apply formatting and write results."""
        # sort key might no longer be a number after formatting, so sort first
        df_sorted = df.sort_values(by=self.SORT_KEY, ascending=False)
        df_formatted = ColumnFormatter.format(df_sorted)
        timestamp_str = dt.datetime.strftime(self.timestamp, "%Y-%m-%dT%H-%M-%SZ")
        filename = self.path / f"seeds-{timestamp_str}.txt"
        self._write_formatted(df_formatted, filename)
        log.info("Wrote %s rows to %s", len(df_formatted), filename)

    @staticmethod
    def _write_formatted(df: pd.DataFrame, filename: Path):
        """
        Write formatted data to file.

        Determine column alignments and widths (max of length of all entries and
        the column name). Write header (with prefix) and rows.
        """
        col_align = {col.name: col.align for col in ColumnFormatter.COLUMNS}
        col_width = {
            col: max(df[col].astype(str).apply(len).max(), len(col))
            for col in df.columns
        }

        header_prefix = "# "
        header = header_prefix + " ".join(
            f"{col:{col_align[col]}{col_width[col] - (len(header_prefix) if col == df.columns[0] else 0)}}"
            for col in df.columns
        )

        formatted_rows = [
            " ".join(
                f"{str(row[col]):{col_align[col]}{col_width[col]}}"
                for col in df.columns
            ).rstrip()
            for _, row in df.iterrows()
        ]
        output = "\n".join([header] + formatted_rows)
        with Path.open(filename, "w", encoding="UTF8") as file:
            file.write(output)

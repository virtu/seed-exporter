"""Writer that outputs data in a makeseeds.py-compatible formatting."""

import datetime as dt
import gzip
import logging as log
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pandas as pd

from seed_exporter.config import __version__
from seed_exporter.processing import StatsColumns

from .column_format import ColumnFormatter


@dataclass
class FormattedOutputWriter:
    """Writer that outputs data in a makeseeds.py-compatible formatting."""

    path: Path
    timestamp: dt.datetime
    SORT_KEY: ClassVar[str] = StatsColumns.AVAILABILITY_30D

    def write(self, df: pd.DataFrame) -> Path:
        """Sort columns, apply formatting and write results."""
        # sort key might no longer be a number after formatting, so sort first
        df_sorted = df.sort_values(by=self.SORT_KEY, ascending=False)
        df_formatted = ColumnFormatter.format(df_sorted)
        timestamp_str = dt.datetime.strftime(self.timestamp, "%Y-%m-%dT%H-%M-%SZ")
        filename = self.path / f"seeds-{timestamp_str}.txt.gz"
        self._write_formatted_gz(df_formatted, filename, self.timestamp)
        log.info("Wrote %d rows to %s", len(df_formatted), filename)
        return filename

    @staticmethod
    def _write_formatted_gz(df: pd.DataFrame, filename: Path, timestamp: dt.datetime):
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

        run_info = (
            f"# created by {socket.gethostname()} "
            f"on {timestamp.isoformat(timespec='seconds')}Z "
            f"with seed-exporter {__version__}"
        )

        header_prefix = "# "
        header = (
            header_prefix
            + " ".join(
                f"{col:{col_align[col]}{col_width[col] - (len(header_prefix) if col == df.columns[0] else 0)}}"
                for col in df.columns
            ).rstrip()
        )

        formatted_rows = [
            " ".join(
                f"{str(row[col]):{col_align[col]}{col_width[col]}}"
                for col in df.columns
            ).rstrip()
            for _, row in df.iterrows()
        ]
        output = "\n".join([run_info] + [header] + formatted_rows) + "\n"

        with gzip.open(filename, "wb") as file:
            file.write(output.encode("utf-8"))

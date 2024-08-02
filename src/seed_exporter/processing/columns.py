"""Mapping for statistic columns."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class StatsColumns:
    """Mappings for statistics columns."""

    GOOD: ClassVar[str] = "good"
    AVAILABILITY_2H: ClassVar[str] = "availability_2_hours"
    AVAILABILITY_8H: ClassVar[str] = "availability_8_hours"
    AVAILABILITY_1D: ClassVar[str] = "availability_1_day"
    AVAILABILITY_7D: ClassVar[str] = "availability_7_days"
    AVAILABILITY_30D: ClassVar[str] = "availability_30_days"

    @staticmethod
    def count(col: str) -> str:
        """Converts a column name to a count column name."""

        return f"{col}_count"

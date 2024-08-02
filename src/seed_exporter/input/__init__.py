"""
Input module.

Exports reader(s) and the InputColumns mapping reader are expected to follow.
"""

from .columns import InputColumns
from .crawler import CrawlerInputReader

__all__ = ["InputColumns", "CrawlerInputReader"]

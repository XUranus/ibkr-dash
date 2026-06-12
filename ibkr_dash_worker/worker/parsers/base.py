"""Parser protocol and base types for multi-format Flex file parsing.

All parsers (XML, CSV, TXT) implement the FlexParser protocol.
The registry in __init__.py auto-detects format and routes to the right parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class FlexParseResult:
    """Standardized output from any Flex parser.

    Each parser produces one FlexParseResult per FlexStatement in the file.
    The writer layer consumes these dicts directly.
    """

    account_id: str = ""
    report_date: str = ""  # YYYY-MM-DD
    positions: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)
    cash_flows: list[dict] = field(default_factory=list)
    account_snapshot: dict = field(default_factory=dict)


@runtime_checkable
class FlexParser(Protocol):
    """Protocol that all Flex file parsers must implement."""

    @staticmethod
    def can_parse(file_path: Path) -> bool:
        """Return True if this parser can handle the given file.

        Typically checks file extension or first-line content.
        """
        ...

    @staticmethod
    def parse(file_path: Path) -> list[FlexParseResult]:
        """Parse the file and return standardized results.

        Returns a list because a single file may contain multiple
        FlexStatements (e.g., one per account/date).
        """
        ...

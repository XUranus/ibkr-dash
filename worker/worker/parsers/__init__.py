"""Parser registry: auto-detect file format and route to the right parser.

Usage:
    from worker.parsers import parse_flex_file
    results = parse_flex_file(Path("data.xml"))
"""

from __future__ import annotations

import logging
from pathlib import Path

from worker.parsers.base import FlexParseResult

logger = logging.getLogger(__name__)


def parse_flex_file(file_path: Path) -> list[FlexParseResult]:
    """Auto-detect file format and parse it.

    Tries each registered parser in order. The first one whose
    can_parse() returns True is used.

    Raises:
        ValueError: If no parser can handle the file.
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Lazy imports to avoid circular dependencies
    from worker.parsers.flex_xml_parser import FlexXmlParser
    from worker.parsers.flex_csv_parser import FlexCsvParser

    parsers = [FlexXmlParser, FlexCsvParser]

    for parser in parsers:
        if parser.can_parse(file_path):
            logger.info("Parsing %s with %s", file_path.name, parser.__name__)
            return parser.parse(file_path)

    raise ValueError(
        f"No parser found for file: {file_path}. "
        f"Supported formats: XML (FlexQueryResponse), CSV (Flex Export)."
    )

"""Parser for IBKR Flex Query CSV reports.

IBKR Flex exports use a multi-section CSV format with record type markers:
  BOF  - Beginning of file (metadata)
  BOA  - Beginning of account (key-value metadata pairs)
  BOS  - Beginning of section
  HEADER - Column headers for the current section
  DATA   - A data row in the current section
  EOS  - End of section
  EOF  - End of file

Sections include: ACCT, EQUT, POST, TRNT, CTRN, FIFO, MYTD, NETP, SECU, PPPO, etc.
"""

from collections import Counter
from dataclasses import dataclass, field
from csv import reader as csv_reader
from pathlib import Path

from worker.utils.dates import to_iso_date
from worker.utils.numbers import clean_string


@dataclass
class FlexSection:
    """A parsed section from the Flex CSV."""
    name: str
    headers: list[str] = field(default_factory=list)
    rows: list[dict[str, str | None]] = field(default_factory=list)


@dataclass
class FlexStatementMetadata:
    """Metadata extracted from BOF/BOA records."""
    query_name: str | None
    from_date: str | None
    to_date: str | None
    account_ids: list[str]
    raw: dict[str, str | None] = field(default_factory=dict)


@dataclass
class FlexStatement:
    """A fully parsed Flex CSV statement."""
    source_file: Path
    metadata: FlexStatementMetadata
    sections: dict[str, FlexSection]
    record_counts: dict[str, int]

    def get_section(self, section_name: str) -> FlexSection | None:
        """Return a section by name, or None if not present."""
        return self.sections.get(section_name)


def _normalize_row(row: list[str]) -> list[str]:
    """Strip whitespace from every cell in a row."""
    return [column.strip() for column in row]


def _strip_leading_section_name(
    payload: list[str], section_name: str | None
) -> list[str]:
    """Remove the leading section name cell if present."""
    if section_name and payload and payload[0].strip().upper() == section_name.upper():
        return payload[1:]
    return payload


def _pairwise_metadata(payload: list[str]) -> dict[str, str | None]:
    """Interpret payload cells as key-value pairs."""
    metadata: dict[str, str | None] = {}
    for index in range(0, len(payload) - 1, 2):
        key = clean_string(payload[index])
        if key is None:
            continue
        metadata[key] = clean_string(payload[index + 1])
    return metadata


def _find_value(
    row: dict[str, str | None], aliases: tuple[str, ...]
) -> str | None:
    """Look up a value in a row dict by trying multiple case-insensitive aliases."""
    normalized = {key.lower(): value for key, value in row.items()}
    for alias in aliases:
        if alias.lower() in normalized and normalized[alias.lower()]:
            return normalized[alias.lower()]
    return None


def _extract_metadata(
    sections: dict[str, FlexSection],
    raw_metadata: dict[str, str | None],
) -> FlexStatementMetadata:
    """Build FlexStatementMetadata from parsed sections and raw metadata."""
    account_ids: list[str] = []
    acct_section = sections.get("ACCT")
    if acct_section:
        for row in acct_section.rows:
            account_id = _find_value(
                row, ("AccountId", "Account", "ClientAccountID", "Account ID")
            )
            if account_id and account_id not in account_ids:
                account_ids.append(account_id)

    query_name = raw_metadata.get("QueryName")
    from_date = raw_metadata.get("FromDate")
    to_date = raw_metadata.get("ToDate")

    if acct_section and acct_section.rows:
        first_row = acct_section.rows[0]
        query_name = query_name or _find_value(first_row, ("QueryName", "StatementName"))
        from_date = from_date or _find_value(first_row, ("FromDate", "PeriodStartDate"))
        to_date = to_date or _find_value(first_row, ("ToDate", "PeriodEndDate", "ReportDate"))

    return FlexStatementMetadata(
        query_name=query_name,
        from_date=to_iso_date(from_date),
        to_date=to_iso_date(to_date),
        account_ids=account_ids,
        raw=raw_metadata,
    )


def parse_flex_csv(file_path: str | Path) -> FlexStatement:
    """Parse an IBKR Flex Query CSV file into a FlexStatement.

    Args:
        file_path: Path to the Flex CSV file.

    Returns:
        A FlexStatement with all sections, metadata, and record counts.
    """
    source_file = Path(file_path)
    sections: dict[str, FlexSection] = {}
    record_counts: Counter[str] = Counter()
    raw_metadata: dict[str, str | None] = {}
    current_section_name: str | None = None

    with source_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv_reader(handle)
        for raw_row in reader:
            normalized_row = _normalize_row(raw_row)
            if not any(normalized_row):
                continue

            record_type = normalized_row[0].upper()
            payload = normalized_row[1:]
            record_counts[record_type] += 1

            if record_type == "BOA":
                raw_metadata.update(_pairwise_metadata(payload))
                continue

            if record_type == "BOF":
                if len(payload) >= 1 and "AccountId" not in raw_metadata:
                    raw_metadata["AccountId"] = clean_string(payload[0])
                if len(payload) >= 2 and "QueryName" not in raw_metadata:
                    raw_metadata["QueryName"] = clean_string(payload[1])
                if len(payload) >= 4 and "FromDate" not in raw_metadata:
                    raw_metadata["FromDate"] = clean_string(payload[3])
                if len(payload) >= 5 and "ToDate" not in raw_metadata:
                    raw_metadata["ToDate"] = clean_string(payload[4])
                continue

            if record_type == "BOS":
                current_section_name = clean_string(payload[0]) if payload else None
                if current_section_name is None:
                    current_section_name = f"UNKNOWN_SECTION_{len(sections) + 1}"
                sections.setdefault(
                    current_section_name, FlexSection(name=current_section_name)
                )
                continue

            if record_type == "HEADER" and current_section_name:
                header_values = _strip_leading_section_name(payload, current_section_name)
                sections[current_section_name].headers = header_values
                continue

            if record_type == "DATA" and current_section_name:
                section = sections[current_section_name]
                data_values = _strip_leading_section_name(payload, current_section_name)
                row_dict: dict[str, str | None] = {}

                for index, header in enumerate(section.headers):
                    value = data_values[index] if index < len(data_values) else ""
                    row_dict[header] = clean_string(value)

                if len(data_values) > len(section.headers):
                    extras = data_values[len(section.headers):]
                    for offset, extra_value in enumerate(extras, start=1):
                        row_dict[f"__extra_{offset}"] = clean_string(extra_value)

                section.rows.append(row_dict)
                continue

            if record_type == "EOS":
                current_section_name = None

    metadata = _extract_metadata(sections, raw_metadata)
    return FlexStatement(
        source_file=source_file,
        metadata=metadata,
        sections=sections,
        record_counts=dict(record_counts),
    )

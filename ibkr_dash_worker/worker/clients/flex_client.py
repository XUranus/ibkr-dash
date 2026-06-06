"""IBKR Flex Web Service client.

Sends flex queries, polls for statement readiness, and downloads the result.
Uses the requests library for HTTP communication with the IBKR Flex API.
"""

from pathlib import Path
import logging
import time
import xml.etree.ElementTree as ET

import requests

from worker.core.config import Settings

logger = logging.getLogger(__name__)

SEND_REQUEST_PATH = "SendRequest"
GET_STATEMENT_PATH = "GetStatement"
STATEMENT_PENDING_CODES = {"1018", "1019"}


class FlexClientError(RuntimeError):
    """Raised when the IBKR Flex Web Service returns an error."""


class FlexStatementNotReady(FlexClientError):
    """Raised when the statement is still being generated."""


class FlexClient:
    """Client for the IBKR Flex Web Service API.

    Handles the full lifecycle of a flex query: submit, poll, and download.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ibkr-dash-worker/0.1"})

    def _require_token(self) -> str:
        """Return the flex token or raise if not configured."""
        if not self.settings.flex_token:
            raise FlexClientError(
                "FLEX_TOKEN is missing. Please fill FLEX_TOKEN in ibkr_dash_worker/.env before calling IBKR."
            )
        return self.settings.flex_token

    def _parse_xml(self, xml_text: str) -> ET.Element:
        """Parse an XML string, raising FlexClientError on failure."""
        try:
            return ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise FlexClientError("IBKR Flex response is not valid XML.") from exc

    def _extract_text(self, root: ET.Element, tag_names: tuple[str, ...]) -> str | None:
        """Extract text from the first matching XML element."""
        for tag_name in tag_names:
            element = root.find(f".//{tag_name}")
            if element is not None and element.text:
                return element.text.strip()
        return None

    def _build_url(self, endpoint: str) -> str:
        """Build the full URL for a Flex API endpoint."""
        return f"{self.settings.flex_base_url.rstrip('/')}/{endpoint}"

    def send_request(self, query_id: str) -> str:
        """Submit a flex query and return the reference code.

        Args:
            query_id: The IBKR Flex Query ID to execute.

        Returns:
            The reference code for polling the statement.

        Raises:
            FlexClientError: If the request fails or returns an error.
        """
        token = self._require_token()
        response = self.session.get(
            self._build_url(SEND_REQUEST_PATH),
            params={"t": token, "q": query_id, "v": "3"},
            timeout=30,
        )
        response.raise_for_status()
        root = self._parse_xml(response.text)

        status = self._extract_text(root, ("Status",))
        reference_code = self._extract_text(root, ("ReferenceCode",))
        error_code = self._extract_text(root, ("ErrorCode", "Code"))
        error_message = self._extract_text(root, ("ErrorMessage", "Message"))

        if status and status.lower() == "success" and reference_code:
            logger.info("submitted Flex query %s successfully", query_id)
            return reference_code

        message = error_message or "Unknown IBKR Flex send_request failure."
        if error_code:
            message = f"{message} (error_code={error_code})"
        raise FlexClientError(message)

    def get_statement(self, reference_code: str) -> str:
        """Poll for a statement result using the reference code.

        Args:
            reference_code: The reference code from send_request.

        Returns:
            The statement content as a string.

        Raises:
            FlexStatementNotReady: If the statement is still being generated.
            FlexClientError: If the request fails or returns an error.
        """
        token = self._require_token()
        response = self.session.get(
            self._build_url(GET_STATEMENT_PATH),
            params={"t": token, "q": reference_code, "v": "3"},
            timeout=60,
        )
        response.raise_for_status()
        body = response.text
        stripped = body.lstrip()

        if stripped.startswith("<"):
            root = self._parse_xml(body)
            error_code = self._extract_text(root, ("ErrorCode", "Code"))
            error_message = self._extract_text(root, ("ErrorMessage", "Message"))
            status = self._extract_text(root, ("Status",))
            message = error_message or "IBKR Flex statement is not ready."

            if error_code in STATEMENT_PENDING_CODES:
                raise FlexStatementNotReady(message)

            # Successful FlexQueryResponse (contains the actual data)
            if root.tag == "FlexQueryResponse" and root.find(".//FlexStatement") is not None:
                return body

            if status and status.lower() == "success":
                url = self._extract_text(root, ("Url",))
                if url:
                    download_response = self.session.get(url, timeout=60)
                    download_response.raise_for_status()
                    return download_response.text

            raise FlexClientError(f"{message} (error_code={error_code or 'unknown'})")

        return body

    def download_flex_statement(self, query_id: str, save_path: str | Path) -> Path:
        """Download a flex statement with retry logic.

        Submits the query, then polls until the statement is ready or retries
        are exhausted.

        Args:
            query_id: The IBKR Flex Query ID to execute.
            save_path: Path where the statement will be saved.

        Returns:
            The Path to the saved statement file.

        Raises:
            FlexClientError: If download fails after all retries.
        """
        save_target = Path(save_path)
        save_target.parent.mkdir(parents=True, exist_ok=True)
        reference_code = self.send_request(query_id)

        for attempt in range(1, self.settings.flex_max_poll_retries + 1):
            try:
                statement = self.get_statement(reference_code)
                save_target.write_text(statement, encoding="utf-8")
                logger.info("downloaded Flex statement for query %s to %s", query_id, save_target)
                return save_target
            except FlexStatementNotReady as exc:
                if attempt == self.settings.flex_max_poll_retries:
                    raise FlexClientError(
                        "IBKR Flex statement was not ready before retry limit was reached."
                    ) from exc
                logger.info(
                    "Flex statement for query %s not ready yet, retry %s/%s",
                    query_id,
                    attempt,
                    self.settings.flex_max_poll_retries,
                )
                time.sleep(self.settings.flex_poll_interval_seconds)

        raise FlexClientError("IBKR Flex statement download exhausted retries unexpectedly.")

    def supports_dynamic_history_windows(self) -> bool:
        """Return whether dynamic date window queries are supported."""
        return False

    def download_history_window(
        self,
        query_id: str,
        start_date: str,
        end_date: str,
        save_path: str | Path,
    ) -> Path:
        """Download a flex statement for a specific date window.

        Not supported in the current implementation; reserved as an extension point.
        """
        raise FlexClientError(
            "Current API client only supports pulling the configured Query ID template result. "
            "Dynamic date windows are reserved as an extension point."
        )

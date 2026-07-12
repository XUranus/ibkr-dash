"""Longbridge service -- market data and financial data from Longbridge API.

Provides quote data, financial statements, and symbol analysis.
Uses Longbridge OpenAPI with HTTP REST calls (no SDK dependency).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 15.0


class LongbridgeUnavailableError(Exception):
    """Longbridge API is not configured or unavailable."""


class LongbridgeExternalDataError(Exception):
    """Longbridge returned an error for the external data request."""


class LongbridgeService:
    """Longbridge market data service using REST API."""

    def __init__(self, settings: Settings) -> None:
        self._app_key = getattr(settings, "longbridge_app_key", None)
        self._app_secret = getattr(settings, "longbridge_app_secret", None)
        self._access_token = getattr(settings, "longbridge_access_token", None)
        self._base_url = "https://openapi.longportapp.com"
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._app_key and self._app_secret and self._access_token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _check_configured(self) -> None:
        if not self.is_configured:
            raise LongbridgeUnavailableError("Longbridge API credentials not configured")

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create a pooled async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        return self._client

    async def close(self) -> None:
        """Close the pooled HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get real-time quote for a symbol."""
        self._check_configured()
        client = self._get_client()
        try:
            resp = await client.get(
                f"{self._base_url}/quote/v1/quote",
                params={"symbol": symbol},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise LongbridgeExternalDataError(data.get("message", "Unknown error"))
            return data.get("data", {})
        except httpx.HTTPStatusError as exc:
            raise LongbridgeExternalDataError(f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise LongbridgeUnavailableError(f"Request failed: {exc}") from exc

    async def get_financials(self, symbol: str, periods: int = 8, report: str = "qf") -> dict[str, Any]:
        """Get financial statements for a symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL.US")
            periods: Number of periods to fetch
            report: Report type - "qf" for quarterly, "af" for annual
        """
        self._check_configured()
        client = self._get_client()
        try:
            resp = await client.get(
                f"{self._base_url}/quote/v1/finance",
                params={"symbol": symbol, "period": report, "count": periods},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise LongbridgeExternalDataError(data.get("message", "Unknown error"))
            return data.get("data", {})
        except httpx.HTTPStatusError as exc:
            raise LongbridgeExternalDataError(f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise LongbridgeUnavailableError(f"Request failed: {exc}") from exc

    async def get_security_info(self, symbol: str) -> dict[str, Any]:
        """Get security basic info."""
        self._check_configured()
        client = self._get_client()
        try:
            resp = await client.get(
                f"{self._base_url}/quote/v1/security-info",
                params={"symbol": symbol},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise LongbridgeExternalDataError(data.get("message", "Unknown error"))
            return data.get("data", {})
        except httpx.HTTPStatusError as exc:
            raise LongbridgeExternalDataError(f"HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise LongbridgeUnavailableError(f"Request failed: {exc}") from exc

    def health_check(self) -> dict[str, Any]:
        """Check if Longbridge API is configured and reachable."""
        if not self.is_configured:
            return {
                "configured": False,
                "status": "not_configured",
                "message": "Longbridge API credentials not set",
            }
        return {
            "configured": True,
            "status": "configured",
            "message": "Longbridge API credentials configured",
        }

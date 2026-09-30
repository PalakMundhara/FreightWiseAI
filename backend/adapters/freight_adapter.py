"""
OilPriceAPI Freight Benchmark Adapter.
Fetches Baltic Dry Index (BDI) and Baltic Capesize Index (BCI) benchmark values.
"""
import os
import time
import logging
import requests
from typing import Dict, Any, Optional

from .base import BaseAdapter

log = logging.getLogger("freightwise.freight")


class OilPriceFreightAdapter(BaseAdapter):
    """
    Adapter for OilPriceAPI Baltic Freight Indices.
    Fetches BDI and BCI on low-frequency daily publication cadence with long-term caching.
    """

    BASE_URL = "https://api.oilpriceapi.com/v1/prices/latest"

    def __init__(self, api_key: Optional[str] = None):
        # 12-hour TTL cache (daily market cadence)
        super().__init__(name="oilpriceapi", default_ttl_seconds=43200, max_stale_seconds=172800)
        self.api_key = api_key or os.getenv("OILPRICEAPI_KEY", "")

    def fetch_benchmarks(self) -> Dict[str, Any]:
        """Fetch Baltic Dry and Capesize benchmark quotes."""
        if not self.api_key or "PASTE" in self.api_key:
            self._last_error = "OILPRICEAPI_KEY is not configured in environment."
            log.warning("[%s] %s", self.name, self._last_error)
            return self._fallback_response()

        if self.is_cached_valid():
            return self._cached_data

        if time.time() < self._rate_limited_until:
            return self._cached_data or self._fallback_response()

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

        bdi_data = self._fetch_single_code("BALTIC_DRY_INDEX", headers)
        bci_data = self._fetch_single_code("BALTIC_CAPESIZE_INDEX", headers)

        if bdi_data or bci_data:
            normalized = {
                "source": "OilPriceAPI (Baltic Exchange)",
                "bdi": bdi_data.get("price") if bdi_data else None,
                "bdi_change_24h": bdi_data.get("change_percent") if bdi_data else None,
                "bdi_timestamp": bdi_data.get("observed_at") if bdi_data else None,
                "bci": bci_data.get("price") if bci_data else None,
                "bci_change_24h": bci_data.get("change_percent") if bci_data else None,
                "bci_timestamp": bci_data.get("observed_at") if bci_data else None,
                "note": "Baltic indices represent global benchmark rate assessments, not route-specific spot quotes."
            }
            self.set_cache(normalized, source_timestamp=normalized["bdi_timestamp"] or normalized["bci_timestamp"])
            log.info("[%s] Retrieved freight benchmarks: BDI=%.1f, BCI=%.1f",
                     self.name, normalized["bdi"] or 0, normalized["bci"] or 0)
            return normalized

        return self._cached_data or self._fallback_response()

    def _fetch_single_code(self, code: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(self.BASE_URL, headers=headers, params={"by_code": code}, timeout=8.0)
            if resp.status_code == 200:
                payload = resp.json().get("data", {})
                changes = payload.get("changes", {}).get("24h", {})
                return {
                    "price": payload.get("price"),
                    "change_percent": changes.get("percent"),
                    "observed_at": payload.get("observed_at") or payload.get("created_at")
                }
            elif resp.status_code == 429:
                self.mark_rate_limited(retry_after_seconds=86400)
                return None
            else:
                self._last_error = f"HTTP {resp.status_code} fetching {code}: {resp.text[:100]}"
                return None
        except Exception as e:
            self._last_error = f"Connection error fetching {code}: {e}"
            return None

    def _fallback_response(self) -> Dict[str, Any]:
        return {
            "source": "OilPriceAPI (Offline / Cached)",
            "bdi": None,
            "bdi_timestamp": None,
            "bci": None,
            "bci_timestamp": None,
            "error": self._last_error
        }

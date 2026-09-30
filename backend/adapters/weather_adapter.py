"""
WeatherAPI.com Client Adapter.
Fetches and normalizes current meteorological conditions for port coordinates.
"""
import os
import time
import logging
import requests
from typing import Dict, Any, Optional

from .base import BaseAdapter

log = logging.getLogger("freightwise.weather")


class WeatherAPIAdapter(BaseAdapter):
    """
    Adapter for WeatherAPI.com Current Weather Endpoint.
    Free tier: 100,000 calls/month, 10-15 minute cadence, cached with TTL.
    """

    BASE_URL = "https://api.weatherapi.com/v1/current.json"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="weatherapi", default_ttl_seconds=900)  # 15 min cache
        self.api_key = api_key or os.getenv("WEATHER_API_KEY", "")

    def fetch_current(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch current weather, returning cached data if still within TTL."""
        if not self.api_key or "PASTE" in self.api_key:
            self._last_error = "WEATHER_API_KEY is not configured in environment."
            log.warning("[%s] %s", self.name, self._last_error)
            return self._fallback_response()

        if self.is_cached_valid():
            return self._cached_data

        if time.time() < self._rate_limited_until:
            log.info("[%s] Serving cached observation due to active rate-limit.", self.name)
            return self._cached_data or self._fallback_response()

        query_coords = f"{latitude:.4f},{longitude:.4f}"
        params = {"key": self.api_key, "q": query_coords}

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=8.0)
            if resp.status_code == 200:
                raw = resp.json()
                curr = raw.get("current", {})
                cond = curr.get("condition", {})
                loc = raw.get("location", {})

                normalized = {
                    "source": "WeatherAPI.com",
                    "location_name": loc.get("name", "Paradip"),
                    "temperature": curr.get("temp_c"),
                    "feels_like": curr.get("feelslike_c"),
                    "humidity": curr.get("humidity"),
                    "wind_speed": curr.get("wind_kph"),
                    "wind_direction": curr.get("wind_dir"),
                    "wind_degree": curr.get("wind_degree"),
                    "pressure": curr.get("pressure_mb"),
                    "precipitation": curr.get("precip_mm"),
                    "visibility": curr.get("vis_km"),
                    "cloud_cover": curr.get("cloud"),
                    "condition": cond.get("text", "Clear"),
                    "icon": cond.get("icon", ""),
                    "observed_at": curr.get("last_updated", ""),
                    "attribution": "Powered by WeatherAPI.com"
                }

                self.set_cache(normalized, source_timestamp=curr.get("last_updated"))
                log.info("[%s] Successfully retrieved live weather: %s, %.1f C, Wind %.1f kph %s",
                         self.name, normalized["condition"], normalized["temperature"],
                         normalized["wind_speed"], normalized["wind_direction"])
                return normalized

            elif resp.status_code == 429:
                self.mark_rate_limited(retry_after_seconds=3600)
                return self._cached_data or self._fallback_response()

            elif resp.status_code in (401, 403):
                self._last_error = f"Authentication failure (HTTP {resp.status_code}): Invalid WeatherAPI Key."
                log.error("[%s] %s", self.name, self._last_error)
                return self._cached_data or self._fallback_response()

            else:
                self._last_error = f"WeatherAPI HTTP {resp.status_code}: {resp.text[:100]}"
                log.warning("[%s] %s", self.name, self._last_error)
                return self._cached_data or self._fallback_response()

        except Exception as e:
            self._last_error = f"Connection error: {e}"
            log.warning("[%s] %s", self.name, self._last_error)
            return self._cached_data or self._fallback_response()

    def _fallback_response(self) -> Dict[str, Any]:
        """Graceful fallback response when API call cannot complete."""
        return {
            "source": "WeatherAPI.com (Offline / Cached)",
            "temperature": None,
            "humidity": None,
            "wind_speed": None,
            "wind_direction": None,
            "pressure": None,
            "precipitation": None,
            "visibility": None,
            "condition": "Service Unavailable",
            "observed_at": None,
            "error": self._last_error
        }

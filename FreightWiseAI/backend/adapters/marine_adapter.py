"""
Open-Meteo Marine Weather Adapter.
Fetches and aggregates maritime wave, swell, and ocean current dynamics.
"""
import time
import logging
import requests
from typing import Dict, Any

from .base import BaseAdapter

log = logging.getLogger("freightwise.marine")


class OpenMeteoMarineAdapter(BaseAdapter):
    """
    Adapter for Open-Meteo Marine API.
    Provides wave height, swell, and current dynamics. Open-access, CC BY 4.0 attribution.
    """

    ENDPOINT = "https://marine-api.open-meteo.com/v1/marine"

    def __init__(self):
        super().__init__(name="open_meteo", default_ttl_seconds=1800)  # 30 min cache

    def fetch_marine_conditions(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch live marine wave and ocean current metrics."""
        if self.is_cached_valid():
            return self._cached_data

        if time.time() < self._rate_limited_until:
            return self._cached_data or self._fallback_response()

        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "current": "wave_height,wave_direction,wave_period,wind_wave_height,"
                       "swell_wave_height,swell_wave_direction,swell_wave_period,"
                       "ocean_current_velocity,ocean_current_direction"
        }

        try:
            resp = requests.get(self.ENDPOINT, params=params, timeout=8.0)
            if resp.status_code == 200:
                raw = resp.json()
                curr = raw.get("current", {})

                normalized = {
                    "source": "Open-Meteo Marine API",
                    "wave_height": curr.get("wave_height"),
                    "wave_direction": curr.get("wave_direction"),
                    "wave_period": curr.get("wave_period"),
                    "wind_wave_height": curr.get("wind_wave_height"),
                    "swell_height": curr.get("swell_wave_height"),
                    "swell_period": curr.get("swell_wave_period"),
                    "ocean_current_velocity": curr.get("ocean_current_velocity"),
                    "ocean_current_direction": curr.get("ocean_current_direction"),
                    "observed_at": curr.get("time", ""),
                    "attribution": "Marine data by Open-Meteo.com (CC BY 4.0)"
                }

                self.set_cache(normalized, source_timestamp=curr.get("time"))
                log.info("[%s] Live marine wave height: %.2fm, swell: %.2fm, current: %.2f km/h",
                         self.name, normalized["wave_height"] or 0,
                         normalized["swell_height"] or 0,
                         normalized["ocean_current_velocity"] or 0)
                return normalized

            elif resp.status_code == 429:
                self.mark_rate_limited(retry_after_seconds=1800)
                return self._cached_data or self._fallback_response()

            else:
                self._last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
                log.warning("[%s] %s", self.name, self._last_error)
                return self._cached_data or self._fallback_response()

        except Exception as e:
            self._last_error = f"Connection error: {e}"
            log.warning("[%s] %s", self.name, self._last_error)
            return self._cached_data or self._fallback_response()

    def _fallback_response(self) -> Dict[str, Any]:
        return {
            "source": "Open-Meteo Marine API (Offline / Cached)",
            "wave_height": None,
            "wave_direction": None,
            "wave_period": None,
            "swell_height": None,
            "ocean_current_velocity": None,
            "ocean_current_direction": None,
            "observed_at": None,
            "error": self._last_error
        }

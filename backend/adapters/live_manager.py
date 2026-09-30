"""
Live Data Ingestion Coordinator.
Aggregates AISStream, WeatherAPI, Open-Meteo Marine, and OilPriceAPI into the
Section 8 Common Normalized Data Structure.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging

from .port_config import get_port_config
from .weather_adapter import WeatherAPIAdapter
from .marine_adapter import OpenMeteoMarineAdapter
from .freight_adapter import OilPriceFreightAdapter
from .ais_service import AISStreamService
from .congestion_calculator import compute_ais_congestion

log = logging.getLogger("freightwise.live_manager")


class LiveDataManager:
    """
    Central singleton coordinating external streaming and REST feeds.
    Provides non-blocking access to normalized port, marine, weather, and freight metrics.
    """

    _instance = None

    @classmethod
    def get_instance(cls, port_id: str = "paradip"):
        if cls._instance is None:
            cls._instance = cls(port_id=port_id)
        return cls._instance

    def __init__(self, port_id: str = "paradip"):
        self.port_config = get_port_config(port_id)
        self.weather_adapter = WeatherAPIAdapter()
        self.marine_adapter = OpenMeteoMarineAdapter()
        self.freight_adapter = OilPriceFreightAdapter()
        self.ais_service = AISStreamService(port_config=self.port_config)

        # Start background AIS stream
        try:
            self.ais_service.start()
        except Exception as e:
            log.warning("Could not launch background AIS streaming: %s", e)

    def get_normalized_data(self, port_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Assemble the complete Section 8 Common Normalized Data Output.
        """
        p_cfg = get_port_config(port_id) if port_id else self.port_config
        lat, lon = p_cfg["latitude"], p_cfg["longitude"]

        # 1. Fetch live REST components (cached with TTL)
        w_data = self.weather_adapter.fetch_current(lat, lon)
        m_data = self.marine_adapter.fetch_marine_conditions(lat, lon)
        f_data = self.freight_adapter.fetch_benchmarks()

        # 2. Get live AIS vessel telemetry & calculate congestion
        live_vessels = self.ais_service.get_live_vessels()
        congestion = compute_ais_congestion(live_vessels, p_cfg, fallback_static_counts={"working": 21, "waiting": 10, "expected": 69})

        # 3. Source Status classification
        source_status = {
            "aisstream": "live" if self.ais_service.is_healthy() else ("stale" if live_vessels else "standby"),
            "weatherapi": self.weather_adapter.get_status(),
            "open_meteo": self.marine_adapter.get_status(),
            "oilpriceapi": self.freight_adapter.get_status()
        }

        # 4. Assemble common schema
        normalized = {
            "port_id": p_cfg["port_id"],
            "port_name": p_cfg["port_name"],
            "unlocode": p_cfg.get("unlocode", "INPAR"),
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "source_status": source_status,
            "vessel_data": {
                "total_vessels": congestion["total_vessels"],
                "moving_vessels": congestion["moving_vessels"],
                "anchored_vessels": congestion["anchored_vessels"],
                "low_speed_vessels": congestion["low_speed_vessels"],
                "average_speed": congestion["average_speed_knots"],
                "live_telemetry_count": len(live_vessels),
                "live_sample": live_vessels[:20] if live_vessels else []
            },
            "congestion_data": {
                "label": congestion["label"],
                "vessel_density": congestion["vessel_density"],
                "anchorage_density": congestion["anchorage_density"],
                "vessel_accumulation": congestion["vessel_accumulation"],
                "waiting_time_proxy_hours": congestion["waiting_time_proxy_hours"],
                "congestion_score": congestion["congestion_score"],
                "congestion_trend": congestion["congestion_trend"],
                "congestion_category": congestion["congestion_category"],
                "disclaimer": congestion["disclaimer"]
            },
            "weather_data": {
                "temperature": w_data.get("temperature"),
                "feels_like": w_data.get("feels_like"),
                "wind_speed": w_data.get("wind_speed"),
                "wind_direction": w_data.get("wind_direction"),
                "pressure": w_data.get("pressure"),
                "precipitation": w_data.get("precipitation"),
                "humidity": w_data.get("humidity"),
                "visibility": w_data.get("visibility"),
                "condition": w_data.get("condition"),
                "icon": w_data.get("icon"),
                "observed_at": w_data.get("observed_at"),
                "source": w_data.get("source"),
                "attribution": w_data.get("attribution")
            },
            "marine_data": {
                "wave_height": m_data.get("wave_height"),
                "wave_direction": m_data.get("wave_direction"),
                "wave_period": m_data.get("wave_period"),
                "wind_wave_height": m_data.get("wind_wave_height"),
                "swell_height": m_data.get("swell_height"),
                "swell_period": m_data.get("swell_period"),
                "ocean_current_velocity": m_data.get("ocean_current_velocity"),
                "ocean_current_direction": m_data.get("ocean_current_direction"),
                "observed_at": m_data.get("observed_at"),
                "source": m_data.get("source"),
                "attribution": m_data.get("attribution")
            },
            "freight_data": {
                "bdi": f_data.get("bdi"),
                "bdi_change_24h": f_data.get("bdi_change_24h"),
                "bdi_timestamp": f_data.get("bdi_timestamp"),
                "bci": f_data.get("bci"),
                "bci_change_24h": f_data.get("bci_change_24h"),
                "bci_timestamp": f_data.get("bci_timestamp"),
                "source": f_data.get("source"),
                "note": f_data.get("note")
            }
        }

        return normalized

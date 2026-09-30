"""
Port Configuration Definition for Indian Maritime Harbors.
Adheres to the Section 7 Common Input Format.
"""
from typing import Dict, Any

INDIAN_PORTS: Dict[str, Dict[str, Any]] = {
    "paradip": {
        "port_id": "paradip",
        "port_name": "Paradip",
        "unlocode": "INPAR",
        "latitude": 20.2666,
        "longitude": 86.7157,
        "bbox": {
            "lat_min": 19.80,
            "lat_max": 20.60,
            "lon_min": 86.20,
            "lon_max": 87.20
        },
        "anchorage_bbox": {
            "lat_min": 20.15,
            "lat_max": 20.35,
            "lon_min": 86.65,
            "lon_max": 86.85
        }
    },
    "visakhapatnam": {
        "port_id": "visakhapatnam",
        "port_name": "Visakhapatnam",
        "unlocode": "INVTZ",
        "latitude": 17.6868,
        "longitude": 83.2185,
        "bbox": {
            "lat_min": 17.40,
            "lat_max": 18.00,
            "lon_min": 83.00,
            "lon_max": 83.50
        }
    },
    "chennai": {
        "port_id": "chennai",
        "port_name": "Chennai",
        "unlocode": "INMAA",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "bbox": {
            "lat_min": 12.80,
            "lat_max": 13.40,
            "lon_min": 80.10,
            "lon_max": 80.60
        }
    },
    "kolkata": {
        "port_id": "kolkata",
        "port_name": "Kolkata / Haldia",
        "unlocode": "INCCU",
        "latitude": 22.0294,
        "longitude": 88.0642,
        "bbox": {
            "lat_min": 21.60,
            "lat_max": 22.50,
            "lon_min": 87.70,
            "lon_max": 88.50
        }
    }
}


def get_port_config(port_id: str = "paradip") -> Dict[str, Any]:
    """Retrieve normalized port geographic configuration."""
    clean_id = (port_id or "paradip").strip().lower()
    return INDIAN_PORTS.get(clean_id, INDIAN_PORTS["paradip"])

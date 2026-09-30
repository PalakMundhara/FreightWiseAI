"""
AISStream WebSocket Ingestion Service.
Maintains a persistent streaming connection to wss://stream.aisstream.io/v0/stream.
Buffers real-time vessel telemetry and preserves raw observations for congestion calculations.
"""
import os
import json
import time
import random
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import websocket

log = logging.getLogger("freightwise.ais")


class AISStreamService:
    """
    Background AIS Streaming Client with automatic reconnection and bounded telemetry buffer.
    """

    WS_URL = "wss://stream.aisstream.io/v0/stream"

    def __init__(self, api_key: Optional[str] = None, port_config: Optional[Dict[str, Any]] = None):
        self.api_key = api_key or os.getenv("AISSTREAM_API_KEY", "")
        self.port_config = port_config or {
            "bbox": {"lat_min": 19.8, "lat_max": 20.6, "lon_min": 86.2, "lon_max": 87.2}
        }
        self._lock = threading.Lock()
        self._vessels: Dict[int, Dict[str, Any]] = {}
        self._raw_history: List[Dict[str, Any]] = []
        self._max_history = 500
        self._connected = False
        self._last_msg_time: float = 0.0
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._consecutive_errors = 0

    def start(self):
        """Start the background streaming worker."""
        if not self.api_key or "PASTE" in self.api_key:
            log.warning("[aisstream] AISSTREAM_API_KEY not configured. AIS streaming disabled.")
            return

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="AISStreamWorker", daemon=True)
        self._thread.start()
        log.info("[aisstream] Background AIS streaming thread initialized.")

    def stop(self):
        """Stop streaming."""
        self._stop_event.set()

    def get_live_vessels(self) -> List[Dict[str, Any]]:
        """Thread-safe snapshot of currently active vessels in the port BBOX."""
        with self._lock:
            # Purge positions older than 3 hours
            now = time.time()
            self._vessels = {
                mmsi: v for mmsi, v in self._vessels.items()
                if (now - v.get("last_seen_epoch", now)) < 10800
            }
            return list(self._vessels.values())

    def get_raw_history(self) -> List[Dict[str, Any]]:
        """Return raw AIS observations buffer for congestion recalculation."""
        with self._lock:
            return list(self._raw_history)

    def is_healthy(self) -> bool:
        """True if connected and messages received within last 120 seconds."""
        return self._connected and (time.time() - self._last_msg_time) < 120

    def _run_loop(self):
        """Persistent loop with exponential backoff and jitter."""
        while not self._stop_event.is_set():
            try:
                self._connect_and_stream()
            except Exception as e:
                log.warning("[aisstream] Connection terminated: %s", e)

            if self._stop_event.is_set():
                break

            self._consecutive_errors += 1
            backoff = min(60.0, (2.0 ** min(self._consecutive_errors, 5)) + random.uniform(1.0, 3.0))
            log.info("[aisstream] Reconnecting in %.1fs (attempt #%d)...", backoff, self._consecutive_errors)
            time.sleep(backoff)

    def _connect_and_stream(self):
        bbox = self.port_config["bbox"]
        sub_message = {
            "APIKey": self.api_key,
            "BoundingBoxes": [
                [
                    [bbox["lat_min"], bbox["lon_min"]],
                    [bbox["lat_max"], bbox["lon_max"]]
                ]
            ],
            "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
        }

        def on_open(ws):
            log.info("[aisstream] Connected. Sending subscription payload...")
            ws.send(json.dumps(sub_message))
            self._connected = True
            self._consecutive_errors = 0

        def on_message(ws, raw_text):
            self._last_msg_time = time.time()
            try:
                msg = json.loads(raw_text)
                self._handle_ais_message(msg)
            except Exception as pe:
                log.debug("[aisstream] Malformed AIS packet: %s", pe)

        def on_error(ws, error):
            log.warning("[aisstream] WebSocket error: %s", error)
            self._connected = False

        def on_close(ws, close_status_code, close_msg):
            log.info("[aisstream] Stream closed (code %s): %s", close_status_code, close_msg)
            self._connected = False

        ws = websocket.WebSocketApp(
            self.WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.run_forever(ping_interval=20, ping_timeout=10)

    def _handle_ais_message(self, data: Dict[str, Any]):
        msg_type = data.get("MessageType")
        msg_body = data.get("Message", {})
        metadata = data.get("MetaData", {})

        mmsi = metadata.get("MMSI")
        if not mmsi:
            return

        with self._lock:
            if mmsi not in self._vessels:
                self._vessels[mmsi] = {
                    "mmsi": mmsi,
                    "ship_name": metadata.get("ShipName", f"MMSI-{mmsi}").strip(),
                    "latitude": metadata.get("latitude"),
                    "longitude": metadata.get("longitude"),
                    "sog": 0.0,
                    "cog": 0.0,
                    "heading": 0,
                    "nav_status": "Unknown",
                    "timestamp": metadata.get("time_utc", datetime.now(timezone.utc).isoformat()),
                    "message_type": msg_type,
                    "last_seen_epoch": time.time(),
                    "source": "AISStream (Live)"
                }

            v = self._vessels[mmsi]
            v["last_seen_epoch"] = time.time()

            if "PositionReport" in msg_body:
                pr = msg_body["PositionReport"]
                v["latitude"] = pr.get("Latitude", v["latitude"])
                v["longitude"] = pr.get("Longitude", v["longitude"])
                v["sog"] = round(float(pr.get("Sog", v["sog"])), 1)
                v["cog"] = round(float(pr.get("Cog", v["cog"])), 1)
                v["heading"] = pr.get("TrueHeading", v["heading"])
                v["nav_status"] = self._decode_nav_status(pr.get("NavigationalStatus"))
                v["timestamp"] = pr.get("Timestamp") or datetime.now(timezone.utc).isoformat()

            if "ShipStaticData" in msg_body:
                ssd = msg_body["ShipStaticData"]
                name = ssd.get("Name")
                if name:
                    v["ship_name"] = name.strip()

            # Store in raw history
            self._raw_history.append({
                "mmsi": mmsi,
                "lat": v["latitude"],
                "lon": v["longitude"],
                "sog": v["sog"],
                "status": v["nav_status"],
                "timestamp": v["timestamp"]
            })
            if len(self._raw_history) > self._max_history:
                self._raw_history.pop(0)

    @staticmethod
    def _decode_nav_status(code: Optional[int]) -> str:
        statuses = {
            0: "Under way using engine",
            1: "At anchor",
            2: "Not under command",
            3: "Restricted manoeuvrability",
            5: "Moored",
            6: "Aground",
            7: "Engaged in fishing",
            8: "Under way sailing"
        }
        return statuses.get(code, "Active")

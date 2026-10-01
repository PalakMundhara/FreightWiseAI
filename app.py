"""
FreightWise AI - Root Application Runner

This file loads the actual Flask application
from backend/app.py.

Use this file when running the project from
the root FreightWiseAI directory.
"""

import os
import sys
import importlib.util
from pathlib import Path


# =========================================================
# PROJECT PATHS
# =========================================================

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
BACKEND_APP = BACKEND_DIR / "app.py"


# =========================================================
# VALIDATE BACKEND
# =========================================================

if not BACKEND_APP.exists():
    raise FileNotFoundError(
        f"Could not find backend app at: {BACKEND_APP}"
    )


# =========================================================
# ADD BACKEND TO PYTHON PATH
# =========================================================

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# =========================================================
# LOAD backend/app.py
# =========================================================

spec = importlib.util.spec_from_file_location(
    "freightwise_backend",
    BACKEND_APP
)

if spec is None or spec.loader is None:
    raise ImportError(
        "Unable to load backend/app.py"
    )


backend_module = importlib.util.module_from_spec(spec)

sys.modules["freightwise_backend"] = backend_module

spec.loader.exec_module(backend_module)


# =========================================================
# GET FLASK APPLICATION
# =========================================================

app = backend_module.app


# =========================================================
# OPTIONAL SHARED OBJECT
# =========================================================

S = getattr(
    backend_module,
    "S",
    None
)


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    host = "0.0.0.0"

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    print()
    print("=" * 60)
    print("             FREIGHTWISE AI")
    print("           Flask Backend Server")
    print("=" * 60)
    print(f"Root directory   : {ROOT_DIR}")
    print(f"Backend directory: {BACKEND_DIR}")
    print(f"Backend app      : {BACKEND_APP}")
    print(f"Host             : {host}")
    print(f"Port             : {port}")
    print("=" * 60)
    print()

    app.run(
        host=host,
        port=port,
        debug=False
    )

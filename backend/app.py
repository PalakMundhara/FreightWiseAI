"""
FreightWise AI - Root Application Runner

Loads the Flask application from backend/app.py.
Works both locally and on cloud hosting platforms such as Render.
"""

import os
import sys
import importlib.util
from pathlib import Path


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

# Make backend modules importable
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Backend uses relative paths, so run from backend directory
os.chdir(BACKEND_DIR)


# ---------------------------------------------------------
# LOAD BACKEND APPLICATION
# ---------------------------------------------------------

backend_app_path = BACKEND_DIR / "app.py"

if not backend_app_path.exists():
    raise FileNotFoundError(
        f"Backend application not found at: {backend_app_path}"
    )


spec = importlib.util.spec_from_file_location(
    "backend_app",
    backend_app_path
)

if spec is None or spec.loader is None:
    raise ImportError("Unable to load backend/app.py")


backend_module = importlib.util.module_from_spec(spec)

sys.modules["backend_app"] = backend_module

spec.loader.exec_module(backend_module)


# ---------------------------------------------------------
# EXPOSE FLASK APP
# ---------------------------------------------------------

app = backend_module.app

# Preserve S if backend defines it
S = getattr(backend_module, "S", None)


# ---------------------------------------------------------
# LOCAL / CLOUD SERVER
# ---------------------------------------------------------

if __name__ == "__main__":

    host = "0.0.0.0"

    port = int(
        os.getenv("PORT", "5000")
    )

    print("=" * 60)
    print("        FREIGHTWISE AI BACKEND")
    print("=" * 60)
    print(f"Host : {host}")
    print(f"Port : {port}")
    print(f"Backend directory : {BACKEND_DIR}")
    print("=" * 60)

    app.run(
        host=host,
        port=port,
        debug=False
    )

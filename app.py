"""
FreightWise AI - Root Application Runner.
Delegates to backend/app.py while ensuring sys.path and working directories
are correctly resolved whether executed from root or backend directory.
"""

import os
import sys
import importlib.util
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.chdir(BACKEND_DIR)

backend_app_path = BACKEND_DIR / "app.py"

spec = importlib.util.spec_from_file_location(
    "backend_app",
    backend_app_path
)

backend_module = importlib.util.module_from_spec(spec)

sys.modules["backend_app"] = backend_module

spec.loader.exec_module(backend_module)

app = backend_module.app

S = getattr(backend_module, "S", None)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=False
    )

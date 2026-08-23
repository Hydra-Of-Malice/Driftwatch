"""Run the Driftwatch engine + UI:  python backend/serve.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from driftwatch_engine.api.app import serve  # noqa: E402
from driftwatch_engine.config import settings  # noqa: E402

if __name__ == "__main__":
    print(f"Driftwatch engine starting on http://localhost:{settings.port}  (mode: {settings.mode})")
    serve(settings)

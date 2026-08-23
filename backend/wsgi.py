"""WSGI entrypoint for gunicorn: `gunicorn --workers 1 --chdir backend wsgi:app`

Mirrors serve.py's startup (db, seed, scheduler) but exposes a module-level
`app` instead of calling `app.run()` — gunicorn owns the HTTP server.
Must run with a single worker: the scheduler is an in-process daemon thread
and SQLite is single-writer, so a second worker would double-run sources.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from driftwatch_engine import db, seed  # noqa: E402
from driftwatch_engine.api.app import build_deps, create_app  # noqa: E402
from driftwatch_engine.brightdata.replay import WorldState  # noqa: E402
from driftwatch_engine.config import settings  # noqa: E402
from driftwatch_engine.scheduler import start as start_scheduler  # noqa: E402

db.configure(settings.db_path)
seed.seed_all()
world = WorldState()
for source_id, variant in seed.CURRENT_VARIANTS.items():
    world.set_variant(source_id, variant)

app = create_app(settings, world)
start_scheduler(build_deps(settings, world))

# Third-party notices

DriftWatch bundles no third-party code, fonts, or images. The web UI is plain JavaScript, CSS, and SVG written for this project.

The packages below are installed separately (from `requirements.txt` or npm) or called as online services. Each keeps its own license.

| Component | How it is used | License |
|---|---|---|
| [Flask](https://pypi.org/project/Flask/) | Web server for the API, UI, and demo mirror | BSD-3-Clause |
| [Pydantic](https://pypi.org/project/pydantic/) | Settings and data models | MIT |
| [jsonschema](https://pypi.org/project/jsonschema/) | Contract shape checks | MIT |
| [PyYAML](https://pypi.org/project/PyYAML/) | Contract and usage files | MIT |
| [HTTPX](https://pypi.org/project/httpx/) | Optional Anthropic API and Slack calls | BSD-3-Clause |
| [Gunicorn](https://pypi.org/project/gunicorn/) | Production server for the Render deploy | MIT |
| [Ruff](https://pypi.org/project/ruff/) | Linting in development and CI only | MIT |
| SQLite (via Python's `sqlite3`) | Local database | Public domain |
| [Bright Data CLI](https://www.npmjs.com/package/@brightdata/cli) (`@brightdata/cli`) | Live mode only | MIT |
| Bright Data API | Live mode only, called through the CLI | Bright Data terms of service |
| Anthropic API | Optional, only when `ANTHROPIC_API_KEY` is set | Anthropic commercial terms |
| Slack incoming webhooks | Optional, only when `DW_SLACK_WEBHOOK` is set | Slack terms of service |
| [shields.io](https://shields.io) | Badge images in the README, loaded by URL | CC0-1.0 (service) |

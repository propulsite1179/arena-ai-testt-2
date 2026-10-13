# GameDev AI Bench

**See what AI can actually build.** An independent, evidence-first research platform for AI game development. English and French, dark and light themes, an authenticated API, relational database, budgeted queue, browser worker, and consent-based Roblox MCP runner.

## Release status: 0.1.0 / research preview

This is executable software, **not a validated production benchmark or a completed commercial SaaS**. No provider model was evaluated during this delivery. The catalog contains sourced provider metadata, not independent performance. Two original browser games are **internal fixtures**. Their runs and votes never enter AI rankings.

Implemented: public pages and filters, model comparisons, optional accounts, private administration, persisted contact requests, fixture Arena voting, campaigns, leases, frozen configurations, browser assertions, artifact hashes, review gates and immutable score snapshots. One-shot paid browser generation is implemented behind explicit authorization and a required isolated container. Provider integrations have only been tested with mocked transports, not live paid credentials.

Read [implementation status](docs/IMPLEMENTATION_STATUS.md), [recovery and verification provenance](docs/RECOVERY.md), and [security](docs/SECURITY.md) before enabling a public server or spending money. A static export is a **read-only presentation**, not the authenticated backend.

## Current verification

The root repository workflow [GameDev verified build](https://github.com/propulsite1179/arena-ai-testt-2/actions/workflows/gamedev-ci.yml) is the authoritative release check. Inspect its conclusion for the exact commit. Its artifact includes fresh unit/API reports, PostgreSQL migration/concurrency checks, real HTTP browser journeys, static-export CSP checks, screenshots, and a portable source ZIP when the build completes. Inherited evidence files from before source recovery are historical, not proof that a newer revision passed.

## Quick start (Python 3.12+)

Run from `gamedev-ai-bench/` after cloning this repository, or from the extracted source folder.

```sh
python -m venv .venv
# macOS / Linux:
. .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
cp .env.example .env
# Windows PowerShell instead: Copy-Item .env.example .env
python -m gamedev.cli init
python -m gamedev.cli admin --email you@example.com --name Administrator
python -m gamedev.cli serve
```

Open `http://127.0.0.1:8000`. The administrator password is entered privately at the terminal; no default production password exists. Public registration is disabled by default. `init` creates a development SQLite database and a catalog with **zero published AI results**. No API calls are made during initialization. Standalone wheel distribution is not qualified; use the complete source tree.

## Run the internal harness fixture

```sh
python -m playwright install chromium
python -m gamedev.cli fixture --email you@example.com
python -m gamedev.cli worker --once --fixture-only
```

Open Administration, inspect the run, actual assertions, screenshots and project, then submit the review rubric. The fixture remains labeled and excluded from rankings. On normal machines the worker tests through HTTP. The development container blocks browser HTTP navigation; the explicitly labeled `BROWSER_COMPONENT_TESTS=true` mode renders **trusted original fixtures only** in memory. This is not network/CSP verification. GitHub Actions runs the separate real HTTP tests without a skip flag.

## Test, validate, build

```sh
python -m pytest -q
BROWSER_COMPONENT_TESTS=true python -m pytest tests/test_components.py -q
python scripts/validate.py
python scripts/e2e.py
python scripts/static_e2e.py
python scripts/render_preview.py
python scripts/build.py
```

PowerShell: set `$env:BROWSER_COMPONENT_TESTS="true"` for the component command, then remove the variable before real HTTP tests. `scripts/e2e.py` uses a temporary database and a real Uvicorn HTTP server. Browser administrator policy errors fail the release gate; do not bypass them or treat a policy skip as success.

`dist/site/` is a static, read-only export. `dist/gamedev-ai-bench-source.zip` contains portable source, original assets, migrations, tests and documentation, without local databases or configured credentials. For GitHub Pages, use `python scripts/build.py --base /YOUR_REPOSITORY --origin https://YOUR_ACCOUNT.github.io`. Vercel uses the supplied `vercel.json`; the Git-linked project root is `gamedev-ai-bench`.

## Project map

| Component | Location |
|---|---|
| Web application, pages and API | `gamedev/web/` |
| Database models and versioned SQL | `gamedev/database.py`, `migrations/` |
| Scoring, statistics, evidence storage | `gamedev/core/` |
| Persistent campaigns, leases and worker | `gamedev/services/` |
| Native provider and MCP adapters | `gamedev/adapters/` |
| Local Roblox runner and ten original starters | `apps/roblox-runner/` |
| Browser sandbox entry | `apps/web-benchmark-worker/` |
| Two original playable reference fixtures | `packages/test-fixtures/games/` |
| Docker, PostgreSQL deployment and CI examples | `infrastructure/`, `.github/` |
| Research, methodology, operations and limits | `docs/` |

## Production is a separate deployment

Use HTTPS, PostgreSQL, a random application secret, persistent evidence storage, reviewed worker isolation, backups, and an independently configured model-provider budget. The public static preview cannot run this backend. It cannot collect votes, accept contact forms, or sign users in: those actions are explicitly disabled. A fully operational public SaaS also requires the missing components listed in implementation status, a security review and legal validation.

See [installation](docs/INSTALLATION.md), [deployment](docs/DEPLOYMENT.md), [admin](docs/ADMINISTRATION.md), [benchmarks](docs/BENCHMARKS.md), [Roblox](docs/ROBLOX.md), [providers](docs/PROVIDERS.md), and [research sources](docs/RESEARCH.md).

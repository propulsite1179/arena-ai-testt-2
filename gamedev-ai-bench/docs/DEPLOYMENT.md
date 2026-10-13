# Deployment

## Full application: HTTPS + PostgreSQL + separate workers

GitHub contains source; GitHub Pages serves only the static preview. The database, artifacts, worker containers and Studio host are independent dependencies. Do not deploy long-running workers into short-lived serverless functions.

1. Provision PostgreSQL and a persistent private evidence volume. Set a unique database password and a random application secret of at least 48 characters.
2. Configure `APP_ENV=production`, exact HTTPS `APP_ORIGIN`, PostgreSQL SQLAlchemy `DATABASE_URL`, and `DATA_DIR` outside the source checkout. Keep registration and paid runs disabled initially.
3. Install `requirements-postgres.txt` and run `python -m gamedev.cli migrate`, then `seed`, then the private administrator bootstrap.
4. Run Uvicorn behind a trusted TLS proxy. Configure explicit forwarded-host trust only for the actual proxy. Do not trust internet-supplied forwarded headers.
5. Run a dedicated browser worker with reviewed sandbox image, no public inbound listener, supplier keys only on the host process, and supplier spending caps. Install the Roblox runner separately on a consented Windows/macOS machine.
6. Test real HTTP navigation/CSP, migrations, concurrent leases, backups and restoration, role boundaries, live supplier metadata/generation and reviewer independence before launch.

`infrastructure/compose.yml` provides PostgreSQL and the web service without a Docker socket or public database port. Its web port binds loopback for a local TLS proxy. It does not launch paid workers or magically provision Studio. Its configuration and images require staging qualification before production; local Docker/PG execution was unavailable during development.

## Read-only static export

```sh
python scripts/build.py --base /arena-ai-testt-2 --origin https://propulsite1179.github.io
```

Publish only `dist/site`. The export includes a conspicuous warning that accounts, contact submission, votes and paid operations require the full server. The catalog comparator, navigation, filters, original games, methodology and language/theme switches work locally on static hosting. No scientific results are fabricated to fill the preview.

The GitHub Pages workflow is a deployment recipe. Repository Pages must be configured to use GitHub Actions; administration access may be needed to enable it. A workflow or generated URL is not evidence a live deployment succeeded. Verify the actual workflow conclusion and deployed URL before claiming availability.

## Updates and rollback

Back up database/evidence before migrations. Never modify an applied migration silently; its checksum is validated. Roll back application code only when the previous version is compatible with the migrated schema. No destructive down-migration is shipped. Preserve published snapshots; use a new version and documented correction rather than overwriting evidence.

## Vercel and portability

Static output can be served by Vercel or any ordinary static host. Full FastAPI hosting requires the correct Python runtime, externally provisioned PostgreSQL and persistent/private artifact storage. The local evidence store must not be placed on ephemeral serverless disks. A production S3 adapter is not delivered yet. No external hosting-specific database is required by the source download.

## Included Vercel configuration

`vercel.json` explicitly selects a **static public export** and runs `scripts/vercel_build.py` from this project directory. Connect the Git repository with the root directory set to `gamedev-ai-bench` when it is nested in another repository. Canonical URLs use Vercel's supplied host metadata. There is no temporary serverless SQLite deployment, and sign-in, votes and contact submission remain disabled in this public export. Deploy the authenticated backend separately with persistent PostgreSQL and evidence storage.

The source workflow `.github/workflows/ci.yml` assumes this folder is the repository root. In a parent repository, use the matching root workflow with `working-directory: gamedev-ai-bench`. CI includes fresh PostgreSQL migration/idempotence and eight concurrent fixture lease checks, but these are not counted as locally passed before execution on a PostgreSQL-capable runner.

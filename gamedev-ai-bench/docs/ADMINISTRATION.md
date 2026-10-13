# Administration

No static administrator account or password is bundled. Bootstrap from the CLI on a trusted host. The role is enforced on the server, not by hiding navigation. Public users cannot read private run prompts/artifacts, worker credentials, leads or campaign controls.

## First campaign

Sign in at `/en/login` or `/fr/login`, open Administration, select **Internal reference fixture**, select web-orbit, quote the zero-cost run, then enqueue. Start the separate worker with `python -m gamedev.cli worker --once --fixture-only`. The UI does not pretend an enqueued job has already executed.

Inspect every assertion and artifact before review. The internal run is visibly a fixture and cannot enter the AI leaderboard. Real model generation requires `ENABLE_PAID_RUNS=true`, a server-only provider key, a qualified sandbox image, a sourced price, a bounded authorization and explicit paid approval. Set supplier-side spending limits first.

## Providers and model changes

The provider connection button fetches an authenticated official catalog; it does not generate billable content. New IDs are staged as announcements, not promoted as independently tested models. Review the source and use `python -m gamedev.cli register-model --help` to add a model version. Price and configuration endpoints are documented in OpenAPI. A default provider setting is not a tested reasoning level.

## Worker credentials

`POST /api/v1/admin/workers` creates a credential returned once. Store it as `GDB_RUNNER_TOKEN` on the consented Studio host. It can only upload private receipts. It cannot approve results, spend money or retrieve account data. Revoke it from the admin UI or endpoint. Discovery is not evidence that Studio is connected: last-seen timestamps remain absent until an actual upload.

## Review independence

For non-fixtures, the campaign creator cannot review, and two different reviewer accounts are required. A rejected review changes the campaign status. Inspect task semantics and game behavior, not just reported DOM attributes. Content-addressed evidence is rehashed at API review time. Corrections need a new versioned evaluation; do not edit a published score row.

## Operational duties

Inspect persisted leads, failed jobs, stale leases and budget events. Run cleanup regularly; the project does not silently schedule system jobs. Audit production backups and restore tests. Do not configure unsupported advanced business/CMS tables as though complete management screens existed.

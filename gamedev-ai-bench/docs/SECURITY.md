# Security and threat model

## Do not expose an unqualified deployment

This is a reviewed-and-tested research preview, **not a penetration-tested or certified service**. Local functional tests do not prove resistance to sandbox escapes, coordinated voting abuse, host compromise or subtle concurrency bugs. Legal and security review is required before commercial/public account launch.

## Boundaries implemented

Passwords use Argon2id. Session tokens are opaque random values, stored only as hashes, with expiry and role checks on every protected request. Production cookies use Secure/HttpOnly/SameSite. Mutations require exact Origin and CSRF validation; Stripe signatures and narrowly scoped runner bearer tokens replace that mechanism on their specific endpoints. Body size is bounded before application parsing. Input schemas reject extra fields. SQL statements are parameterized through SQLAlchemy.

Public pages escape text. Public artifacts are rehashed and delivered as attachment/octet-stream; only validated PNG magic can be previewed. Generated HTML/JavaScript is **never served as executable app-origin content**. CSP denies remote scripts and object embeds; no third-party analytics or nonlocal assets are loaded. Original internal game fixtures use sandboxed frames without `allow-same-origin`; this is not a substitute for isolation of arbitrary generated code.

Persistent rate limits cover login, voting, contact, discovery and campaign creation. The app does not trust arbitrary forwarded IP headers. Configure a trusted HTTPS reverse proxy deliberately. Rate limiting is not a complete Sybil/anti-bot defense; public AI voting is not enabled in this release.

## Browser worker

Never run generated code with `trusted_fixture=True`. That switch is only for checked-in original fixtures. The container contract uses no network, read-only root/source, no capabilities, no new privileges, an unprivileged UID, bounded CPU/memory/PIDs/tmpfs and a subprocess timeout. Provider secrets are not forwarded. Build the sandbox separately and run the worker on a dedicated machine, not beside sensitive production data.

A Docker socket is effectively host administration access. **Do not mount it into the public web container.** The delivered Compose web service does not do this. A production worker operator must assess hardened runtime/microVM alternatives, seccomp, host egress, resource exhaustion and browser vulnerabilities. The Docker image was not executed in the development environment.

## Cost safety and failures

Supplier calls are never automatically retried after ambiguous timeouts. Idempotency protects campaign creation, not vendor billing exactly-once semantics. Cancellation does not unspend an already issued request. Conservatively account unknown costs, investigate failures, and use supplier-side hard limits. The application cannot guarantee an external invoice cap.

## Secrets and private tests

`.env`, local SQLite databases, private artifacts and local session keys are excluded from source archives. Test-only placeholder passwords/keys are clearly named and never deployment defaults. Private task versions and private provider/configuration evidence are excluded from public projections. Review artifacts for embedded personal information or secrets before approving publication; automatic redaction is not a complete content review.

## Remaining launch gates

Execute PostgreSQL concurrency/restore tests, run live browser HTTP/CSP tests and worker isolation checks, qualify dependencies with an up-to-date vulnerability scanner, add public-account verification/reset/MFA as needed, audit cookies/data retention, and complete an external accessibility/security review. Dependency version inventory is not a vulnerability scan. Report issues privately to the operator's configured contact; no nonexistent security inbox is advertised.

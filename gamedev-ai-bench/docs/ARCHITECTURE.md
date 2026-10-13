# Architecture and decisions

## ADR 001: a portable Python fullstack application

FastAPI, SQLAlchemy and server-rendered Jinja templates were chosen instead of an unverified JavaScript dependency tree. The development environment had no outbound package-registry DNS, but these libraries and Chromium were installed and executable. The choice permits actual tests and a production-capable HTTP boundary without pretending an unbuilt frontend works. JavaScript enhances server-rendered pages; no CDN, external font or remote image is required.

The source is the supported installation artifact. A standalone Python wheel is not qualified because migrations, Roblox starters and game fixtures live alongside the package. PostgreSQL is required by production settings; SQLite is explicitly a single-host development fallback.

## Process boundaries

```text
Browser -> HTTPS reverse proxy -> FastAPI -> PostgreSQL
                                  |              |
                                  |              + persistent campaigns and leased runs
                                  + private content-addressed evidence storage
                                                 |
Dedicated worker -> reviewed provider API -> bounded text files
                 -> network-disabled ephemeral Chromium container
                 -> assertions / images / SHA-256 evidence -> review gate

Dedicated Windows/macOS Studio host -> local official MCP stdio
    explicit owner consent + approved plan -> private backend receipt
```

The browser never sees provider keys. User-generated code never runs in the web server process. The web worker checks sandbox availability before any paid request. Its host retains provider credentials; the browser container receives only a read-only generated project and writable bounded output directory, not the environment or keys.

## Database and state

Forty relational tables cover users, organizations/memberships, sessions, providers/models/versions/configurations/harnesses, suites/tasks/versions, campaigns/runs/events/tool calls/assertions/artifacts/snapshots/reviews, Arena matches/votes, announcements/prices/research, notifications/subscriptions/sponsors/reports/API keys/audit, leads/follows/comparisons/workers/rate limits/settings/webhooks/idempotency and schema revisions. Some business/CMS tables are extension foundations, not completed interfaces.

One run follows `pending -> preparing -> running -> evaluating -> awaiting-review -> completed`, with explicit failure/cancellation paths. Claims use row locks with `SKIP LOCKED` on PostgreSQL and compare-and-set state updates. A lease is hashed, expires after 180 seconds, and is not a reusable account credential. Expired potentially billable requests are failed, conservatively accounted, and **not automatically repeated**.

## Versioning and reproducibility

Store exact catalog API ID, provider-reported model where observable, parameters, prompt, harness/protocol/task hashes, selected task set, dependency metadata, requested token/timeout limits, budget reservation, timestamps, usage and evidence. Alias model IDs and provider infrastructure are not immutable. A matching seed would not guarantee identical remote results; unsupported seeds are recorded as missing rather than invented.

## Static mode

`scripts/build.py` renders public routes against a fresh empty database. It removes CSRF material, inserts a conspicuous static-mode notice, disables write actions and creates a portable catalog JSON for the metadata comparator. No account or admin data is exported. Static hosting is not a serverless equivalent of the database and workers.

# Implementation status and acceptance matrix

Release 0.1.0, 2026-10-13. **Implemented, locally verified, and production-qualified are different states.** Consult `evidence/verification.json` for executed commands and their actual outcomes. No paid supplier request and no native Studio playtest was performed during development.

| Area | Delivered | Remaining / not qualified |
|---|---|---|
| Web product | SSR home, leaderboard, provider catalog, 2-4 model comparison, Roblox/web suites, task/run inspection, lab, research, business/contact, account/admin; EN/FR; responsive light/dark design; original SVG and Canvas art | Full accessibility certification, external user testing and performance audit |
| Evidence integrity | No seeded model scores, fixtures separated, missing checks never passes, per-task hashes, frozen configurations, append-only score snapshots, independent review gate | Signed public transparency log, formal contest/correction workflow, rank uncertainty UI |
| Relational backend | 40 tables, keys/constraints/indexes, checked-in SQLite and PostgreSQL migrations, transactions, private API, pagination and validation | PostgreSQL migration execution and concurrent worker validation were not available locally |
| Accounts | Argon2id passwords, opaque expiring sessions, roles, CSRF/origin checks, comparison saves, follows/in-app notifications, personal export/deletion | Email verification, password-reset delivery, MFA, organization management UI; public sign-up disabled by default |
| Campaigns | Quote, explicit spending authorization, idempotent creation, persistent lease queue, cancellation, stale-lease failure, no automatic paid retry, cost estimates separate from invoices | Hard financial guarantees require provider limits; advanced retries/resume and distributed chaos tests |
| Browser engine | Real Chromium load/canvas/runtime/start/keyboard/restart/mobile/touch smoke checks, screenshots, native generation adapters, network-disabled Docker contract | Live provider generation and Docker isolation were not executed locally; semantic/anti-cheat checks remain limited |
| Suites | 14 versioned original briefs, 10 Roblox starter generators, Luau contract tests for selected tasks, 2 original web fixtures | Only `web-orbit` is enabled for paid one-shot qualification; other paid tasks fail closed pending task-specific test qualification |
| Roblox | Official OS-specific stdio entry, discovery of tool schemas, schema validation, approved tool allowlist, owner consent, disposable-copy hash, bounded plans, private authenticated receipt upload | No real Studio session, no automated paid Studio agent campaign, no multi-client playtest, no OpenGameEval execution |
| Arena | Anonymous-before-vote fixture pairing, random order, real games, server-side votes, ownership/expiry/uniqueness/rate limits | Only internal fixtures. No public AI match ingestion, no production anti-bot system, no Roblox video synchronization |
| Providers | Native OpenAI Responses, Claude Messages, Gemini generateContent, reviewed OpenAI-compatible endpoint adapters; eight sourced catalog entries; admin discovery staging | No live credentials tested, no fully agentic tool loop, no local/open-weight runtime adapter. Custom reasoning overrides only qualified for OpenAI |
| Scientific functions | pass@k, Wilson interval, task-cluster bootstrap, paired task deltas, descriptive regularized Bradley-Terry, quartiles, weighted technical gates | No inferential rank claim, no arbitrary universal score, no validated multi-task game-quality composite |
| Storage | Bounded SHA-256 content-addressed local storage; hash verification; generated code downloaded as inert attachments | S3 adapter and separate-origin untrusted artifact publisher/player not implemented. Do not expose generated HTML as an app-origin page |
| Administration | Campaigns, private results/review, providers/discovery, worker registration/revocation, leads, API endpoints for configurations and price history | Full CMS, translation editor, role-management UI, subscriptions/revenue dashboards and bulk moderation are not implemented |
| Business | Functional persisted professional/contact leads, honest Pro/Enterprise/partnership pages, optional checkout and verified replay-safe Stripe webhook boundary | No live Stripe checkout/webhooks, no active prices/subscriptions, no SMTP/newsletter/marketing automation, no fabricated partners |
| Model watch | On-demand provider catalog discovery, deduplication and unpublished announcement staging | Scheduled RSS/changelog collection, automatic source verification and admin alert delivery are not implemented |
| Export/deploy | Portable source, original assets, migrations, CLI, Docker/CI configurations, read-only static export | Hosting accounts, production database, domain, external keys and operator legal identity must be configured separately |

## Publication discipline

The leaderboard includes only non-fixture, published, publicly visible results belonging to fully completed campaigns and matched protocol cohorts. An aborted or incomplete campaign is not a validated result. This preview has insufficient breadth for population-level conclusions. It must not be marketed as a representative ranking simply because a technical score can be calculated.

A model announcement, a provider catalog response, a successful API call, a MCP receipt, a browser smoke test and a reviewed benchmark are distinct events. The UI and API intentionally do not collapse them into one success state.

## Next engineering priorities

1. Qualify PostgreSQL migrations, concurrent leases and restore drills on a staging host; run Docker escape/egress threat tests.
2. Execute the first authorized provider campaign with supplier-side limits and independently review failures and artifacts.
3. Add semantic game-specific assertions and at least five distinct qualified tasks before reporting task-bootstrap intervals.
4. Qualify the local Roblox runner against a disposable Studio project; then add an auditable, restricted agent orchestration loop and multi-client evidence.
5. Add isolated published-artifact hosting and real AI Arena campaigns before human preference rankings.
6. Complete email verification/reset, legal/privacy review, production anti-abuse, accessibility and security audits before public commerce.

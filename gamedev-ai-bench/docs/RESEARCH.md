# Research log and source-driven decisions

Review date: **2026-10-13**. Sources below were consulted during implementation. The date is a documentation-check date, not a model release date or proof of account-level API access. No external benchmark scores/data or source code were imported.

## Roblox

- https://create.roblox.com/docs/studio/mcp : built-in local MCP entrypoints, discovery and named Studio tools. Decision: separate Windows/macOS stdio runner, schemas discovered at runtime, no browser-to-Studio fiction, no assumed multiplayer automation.
- https://create.roblox.com/docs/ : engine documentation context; use real Studio projects, not HTML emulation of Roblox.
- https://github.com/Roblox/open-game-eval and https://github.com/Roblox/open-game-eval/blob/main/LLM_LEADERBOARD.md : evaluated as references for game-development evaluation and transparent run comparisons. No automatic compatibility claim; no code/data reuse and therefore no imported license obligations from those repositories.

## Benchmarks and research

- https://artificialanalysis.ai/ : inspected as a public comparison reference. Decision: separate model/provider/configuration, expose dated price references and missing independent evidence.
- https://www.designarena.ai/ : inspected for paired visual comparison. Decision: blind initial presentation, randomized positions, ties/both-bad and uncertainty; internal demonstrations never become AI preferences.
- https://github.com/waynchi/gamedevbench : inspected as a game-generation evaluation reference. Decision: preserve runnable output and isolate it, rather than showing a screenshot as proof of functionality.
- https://crfm.stanford.edu/helm/ : transparency and evaluation context. Decision: publish task/protocol/harness distinctions and limitations rather than an unsupported absolute winner.
- https://github.com/openai/human-eval/blob/master/human_eval/evaluation.py : reference pass@k estimator. The implementation is independently written and unit-tested against combinatorial values.

Competitor inspection is not an exhaustive competitive audit and does not establish superiority. No proprietary dataset scraping, copied ranking, protected game characters or partner logos were used. Repository license availability was not asserted as a blanket license to reuse assets.

## Official model and API documentation

- https://developers.openai.com/api/docs/models : checked catalog IDs and listed price references for `gpt-6-astra`, `gpt-6.1-sol`, `gpt-6-luna`; native Responses, per-version reasoning levels, dated provider metadata only.
- https://platform.claude.com/docs/en/models/overview : checked `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5-5` and listed price references.
- https://platform.claude.com/docs/en/api/messages/create : native Messages request/content/usage boundary. Nondefault thinking/effort variants remain unqualified in this release.
- https://ai.google.dev/gemini-api/docs/models : checked `gemini-3.8-flash` and `gemini-3.1-pro-preview`; no unsourced Google rate was filled in.
- https://ai.google.dev/gemini-api/docs/text-generation : generateContent body, returned candidates/usage and model version where observable.
- https://api-docs.deepseek.com/ : reviewed compatible endpoint family, not a fabricated model identifier.
- https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope : compatible Qwen API; regional/workspace qualification belongs to the deploying operator.
- https://docs.z.ai/guides/overview/quick-start : reviewed Z.ai endpoint family.
- https://platform.moonshot.ai/docs/guide/start-using-kimi-api : official Kimi/Moonshot API entry context; no seeded speculative model IDs.

The model registry is editable, not a hardcoded assertion of the newest/best models. Price references are estimates, distinct from supplier invoices and observed token usage. No supplier test was actually run during delivery.

## Infrastructure and safety

- https://fastapi.tiangolo.com/deployment/ : real ASGI deployment, not a static site masquerading as a backend.
- https://docs.sqlalchemy.org/en/20/orm/quickstart.html : relational ORM/transitions and explicit sessions.
- https://www.postgresql.org/docs/current/sql-select.html : row locking and SKIP LOCKED for lease claims. PostgreSQL execution still needs staging validation.
- https://modelcontextprotocol.io/specification/2025-06-18/basic/transports : stdio JSON-RPC transport boundary and lifecycle.
- https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html : opaque sessions, secure cookies and server authorization.
- https://www.w3.org/TR/WCAG22/ : target AA accessibility principles. This product is not certified AA by merely following them.
- https://playwright.dev/python/docs/intro : browser inspection/screenshots. Local component rendering and true HTTP E2E are reported separately.
- https://docs.stripe.com/webhooks and https://docs.stripe.com/api/checkout/sessions/create : optional signed webhook and server-side checkout, not active billing.

External documentation can change. Recheck official API schemas, pricing, versions, license terms, browser/worker vulnerabilities and regional restrictions before running a live campaign or upgrading a dependency.

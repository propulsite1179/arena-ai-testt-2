# GameDev AI Bench

The executable application lives in **[gamedev-ai-bench](gamedev-ai-bench/)**.

[Installation and full project README](gamedev-ai-bench/README.md) · [Implementation status](gamedev-ai-bench/docs/IMPLEMENTATION_STATUS.md) · [CI runs](../../actions/workflows/gamedev-ci.yml) · [Recovery provenance](gamedev-ai-bench/docs/RECOVERY.md)

This repository contains the FastAPI application, English/French UI, relational database and SQL migrations, authentication and private administration, campaign queue, statistics and evidence storage, browser benchmark worker, local consent-based Roblox MCP runner, original playable fixtures, tests, and deployment documentation.

**Research preview, not a finished commercial SaaS. No independent AI benchmark scores are fabricated.** Public static hosting is read-only; the backend, PostgreSQL, persistent evidence storage, and isolated workers require their own production deployment. Provider keys and billing are disabled until explicitly configured and authorized.

Run installation commands from `gamedev-ai-bench/`. The Vercel project must use the same root directory. The `_gamedev_delivery/` folder is an audit record of an interrupted transfer, not an installation dependency. Use the recovered application source or the source ZIP in a successful `GameDev verified build` artifact; do not concatenate the old archive parts.

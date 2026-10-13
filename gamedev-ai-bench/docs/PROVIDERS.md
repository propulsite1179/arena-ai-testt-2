# Model providers and catalog governance

The app separates provider, model, exact API identifier, version record, harness and reasoning configuration. Seeded metadata was checked against official documentation on 2026-10-13. Alias identifiers can change behavior; release dates not verified from an explicit source are left empty. Catalog status is not API access or benchmark success.

Adapters:

| Family | Native endpoint style | Environment variable |
|---|---|---|
| OpenAI | Responses | OPENAI_API_KEY |
| Anthropic | Messages | ANTHROPIC_API_KEY |
| Google | Gemini generateContent | GEMINI_API_KEY |
| DeepSeek | Reviewed OpenAI-compatible endpoint | DEEPSEEK_API_KEY |
| Qwen | Reviewed international compatible endpoint | QWEN_API_KEY |
| Z.ai | Compatible endpoint | ZAI_API_KEY |
| Moonshot / Kimi | Compatible endpoint | MOONSHOT_API_KEY |

Endpoint hostnames are explicitly allowlisted to prevent arbitrary backend SSRF. Regional Qwen workspaces/endpoints and supplier terms must be reviewed for the deploying operator; changing a hostname requires reviewed code/configuration, not a user-supplied URL. Local/open-weight adapters are not implemented in this release.

Keep keys only in the server/worker environment. Never paste them into frontend configuration, browser local storage, repository files, public issues or logs. No test needs a real key. Native mocked transport tests check request shapes, token usage, pagination, errors and no automatic retries. They do **not** verify live access, rate limits or every version's optional parameters.

Only OpenAI reasoning overrides present in the sourced capability list are exposed; other providers use documented defaults until provider-specific reasoning control is qualified. There is no full tool-calling agent loop. Complete-agent comparisons need a different harness and cannot be mislabeled as direct standardized calls.

Prices are dated references stored separately from observed usage. Google prices are intentionally absent where not verified, so affected paid quotes are refused. Cache creation/read billing can differ by vendor; confirm all supplier multipliers before interpreting an estimate as an invoice. A quote is a conservative reservation, not an enforceable supplier billing cap. Set external spending limits, keep low initial output caps and manually authorize a small first campaign.

On-demand discovery lists official model catalogs without generation. It stages announcements for review and never starts paid campaigns. Scheduled changelog/RSS watching and email alerts remain future work.

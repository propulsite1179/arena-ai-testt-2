# Dependency advisory audit and release verification

## 2026-10-13 findings

The initial `pip-audit` run on commit `40e624bc1c7b122b662b566892da595819666121` reported six known advisories in two packages: pytest 9.0.2 (PYSEC-2026-1845) and Starlette 0.50.0 (PYSEC-2026-161, PYSEC-2026-249, PYSEC-2026-248, PYSEC-2026-2281, PYSEC-2026-2280). The report is preserved in the `gamedev-dependency-audit` artifact of GitHub Actions run `38389938893`. Findings were not suppressed.

The release requirements now select pytest 9.0.3 and Starlette 1.3.1, the patched versions identified by the advisory data. FastAPI is updated to 0.141.1, whose published dependency metadata permits Starlette 1.3.1. All functional tests and the advisory scan must be rerun on this revision. A pin change alone is not evidence of successful remediation or compatibility.

Primary references consulted:
- https://pypi.org/project/fastapi/0.141.1/
- https://github.com/fastapi/fastapi/blob/0.141.1/pyproject.toml
- https://fastapi.tiangolo.com/release-notes/
- https://www.starlette.io/release-notes/
- https://pypi.org/project/pytest/9.0.3/
- https://github.com/pypa/pip-audit

## Scope and limits

The root workflow `GameDev dependency and deployment audit` scans requirements against current PyPI advisory data and checks critical Python lint rules E9/F63/F7/F82. Its tool versions and JSON reports are retained as artifacts. These checks are not a penetration test, full lint/style review, static type qualification, legal certification, or a proof that no vulnerabilities exist. Browser engine and operating-system patching remain the deployment operator's responsibility. Untrusted model-generated games must never be executed outside the documented isolated worker.

The separate unauthenticated public-HTTPS check verifies the real Vercel static site and security response headers. This is distinct from the local ephemeral full-backend HTTP tests and is not evidence of a deployed production database or active paid integrations.

## Visual verification

Production-like screenshots use real HTTP pages and the deployment CSP, including the two sandboxed original game fixtures. The `inline_document` helper remains limited to explicitly named trusted component tests. In-memory `srcdoc` rendering of the Arena proved unstable with the CI headless browser and is not used for release screenshots. Browser policy errors are failures, never bypassed or described as passed.

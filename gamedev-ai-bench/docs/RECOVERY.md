# Source recovery and verification provenance

On 2026-10-13, the interrupted source delivery contained 17 encoded archive parts. The first 15 matched the SHA-256 values recorded before the interruption. The final two parts were malformed or did not match their reference hashes. The reference hashes have NOT been replaced to hide the corruption.

A bounded LZMA decompression of the verified prefix produced 654448 bytes with SHA-256 `bd46ab4e8bfb1a36223d7c170aff918f7db77d5ce1c4f9acf09c6579889d40a0`. Exactly 102 complete regular source files were recovered. Incomplete tar members were excluded. See `RECOVERY_MANIFEST.json` for individual recovered-file hashes and the repository history for the original transfer.

The application, database, migrations, workers, interface, original assets, operational documentation, and API tests were recovered. Missing regression test modules were independently re-authored, rather than represented as original recovered bytes. This is a new verified revision, not a claim that the original compressed archive was fully repaired.

## Authoritative test evidence

Inherited files such as `evidence/verification.json`, `unit-api.xml`, and `components.xml` describe the pre-interruption workspace and must not be used as evidence that a later revision passed. The root repository workflow `GameDev verified build` creates fresh `ci-unit-api.xml`, `ci-components.xml`, `postgresql-ci.json`, and `e2e.json`, tied to the exact GitHub commit and workflow run. Download its artifact for current evidence.

No live model-provider or Roblox Studio evaluation is implied by any software test. Provider transports and MCP contracts use explicit mocks. Browser games are original reference fixtures, excluded from model rankings. A successful static deployment is a read-only preview, not a production deployment of the database, accounts, paid benchmark workers, or billing.

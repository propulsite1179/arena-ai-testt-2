# Installation

Use a fresh folder, Python 3.12 or newer, and a virtual environment. Install `requirements-dev.txt` for local development and browser tests, or `requirements.txt` for the web process. `requirements-postgres.txt` adds the production database driver. Direct dependencies are pinned; the dependency inventory records the development environment and is not a vulnerability clearance.

Copy `.env.example` to `.env`. Do not commit it. `APP_ORIGIN` must match the exact browser origin (scheme, hostname, port), without a URL path. Opening localhost while configured for 127.0.0.1 will deliberately fail mutation origin checks. Development creates a random local session secret file with restrictive permissions. Production refuses to generate one silently.

`python -m gamedev.cli init` applies versioned migrations and seeds the catalog, suites and internal fixture configuration. It never populates fake benchmark results. `python -m gamedev.cli admin --email ... --name ...` prompts privately for a 12-128 character password. Set reviewer/member roles with `--role reviewer` or `--role member` when appropriate.

Run `python -m gamedev.cli serve`. Keep `ALLOW_REGISTRATION=false` until email verification/reset and public abuse protections are completed. Contact submissions go to the administrative inbox in the database; SMTP variables are reserved and do not mean delivery exists.

For browser testing install `python -m playwright install --with-deps chromium` on a Linux worker or `python -m playwright install chromium` on Windows/macOS. Roblox Studio is separate and is not installed by any project command.

Production startup does not auto-migrate. Run `python -m gamedev.cli migrate`, then `python -m gamedev.cli seed`, then create the first administrator from a trusted terminal. Protect database credentials and evidence-directory permissions before exposing HTTPS.

# Backup and restore

## Development SQLite

Stop writes and workers, then run:

```sh
python scripts/backup.py create --destination /safe/backups/bench-2026-10-13
python scripts/backup.py verify --backup /safe/backups/bench-2026-10-13
python scripts/backup.py restore --backup /safe/backups/bench-2026-10-13 --destination /new/empty/restore
```

The script uses SQLite's backup API and copies only evidence objects, recording a hash manifest. It refuses an existing restore destination and validates every copied file. It does not silently overwrite a live database or include the session secret. Keep configuration/secrets in a separate secure backup. Stop writes for a consistent database-and-artifact snapshot; a database transaction alone cannot atomically snapshot the filesystem.

## PostgreSQL production

Use the operator's secure environment/pgpass configuration; never put a database password into a shell log or repository. Run `pg_dump --format=custom --file=database.dump` using the appropriate `PGHOST`, `PGDATABASE`, `PGUSER` and securely supplied authentication. Snapshot the evidence store in the same maintenance window and produce/verify SHA-256 manifests. Encrypt off-host backups with controlled access and retention.

Restore into a new database with `pg_restore --no-owner --dbname=RESTORE_DATABASE database.dump`, restore the evidence objects and secrets securely, run schema-version verification and known public/private run checks, then test login, queue leases and artifact hashes before switching traffic. Test restorations regularly; a successful backup command is not proof of recoverability.

Neither PostgreSQL dump/restore nor Docker volume recovery was executed in this development container. The SQLite backup script is covered by local tests. Production retention and privacy erasure must include backups under the operator's legally reviewed policy.

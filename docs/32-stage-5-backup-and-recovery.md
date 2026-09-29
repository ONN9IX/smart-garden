# Stage 5 — PostgreSQL Backup and Recovery

This runbook defines the PostgreSQL-native backup, guarded disposable restore and recovery-verification path delivered by Issue #107. It changes no application, API, auth, RBAC, tenant or database-schema contract.

## Purpose and safety boundary

The scripts prove that a custom-format PostgreSQL backup can be restored into a fresh disposable database, reconciled with the current Alembic head and queried for representative synthetic Stage 1–4 evidence. They do not select production infrastructure or a cloud backup vendor.

Production data must never be copied into development, test, preview or recovery-verification environments. Automated verification uses synthetic data only. The restore script intentionally accepts only database names beginning with `smart_garden_recovery_` and requires two explicit destructive-operation guards.

## Prerequisites

- Bash with `set -euo pipefail` support.
- PostgreSQL client tools compatible with the server: `psql`, `pg_dump`, `pg_restore`, `createdb` and `dropdb`.
- Python/backend dependencies and the repository's existing Alembic configuration for migration verification.
- Network and database permissions limited to the intended source or disposable recovery database.
- A synthetic source migrated to the current head and populated with `python -m app.services.seed` for verification.

Credentials and connection configuration come from the execution environment or an appropriately protected libpq password file. Secrets must not be stored in these scripts, committed files, command arguments, terminal history or logs.

## Environment variables

The native tools read standard libpq variables:

- `PGHOST`, `PGPORT`, `PGUSER` — required connection target;
- `PGPASSWORD` or another approved libpq credential source — supplied externally when authentication requires it;
- optional libpq controls such as `PGSSLMODE`, according to the approved environment.

Backup additionally requires:

- `PGDATABASE` — explicit source database;
- `BACKUP_FILE` — destination file in an existing writable directory;
- `BACKUP_OVERWRITE=YES` — only when replacing an existing backup is intentional.

Restore additionally requires:

- `BACKUP_FILE` — existing non-empty custom-format archive;
- `RESTORE_DATABASE` — explicit disposable database with the `smart_garden_recovery_` prefix;
- `RESTORE_CONFIRM_DATABASE` — exact repetition of `RESTORE_DATABASE`;
- `RESTORE_DISPOSABLE=YES` — explicit destructive-operation acknowledgement.

End-to-end verification additionally requires:

- `SOURCE_DATABASE` and `RECOVERY_DATABASE`;
- `DATABASE_URL` pointing to `SOURCE_DATABASE` for existing backend/Alembic tooling;
- `RECOVERY_DATABASE_URL` pointing to `RECOVERY_DATABASE`;
- `APP_ENV=test` or `APP_ENV=development`;
- `RECOVERY_VERIFICATION_SYNTHETIC=YES`.

Do not print environment values while diagnosing a failure because they may contain credentials.

## Safe backup procedure

1. Confirm the target is the intended PostgreSQL source and the output directory has protected access.
2. Export the required variables through the approved secret/configuration mechanism.
3. Run:

   ```bash
   scripts/backup-postgres.sh
   ```

The script writes to a mode-`0600` temporary file in the destination directory, runs `pg_dump --format=custom`, verifies that the artifact is non-empty and that `pg_restore --list` can read its catalog, then atomically moves it to `BACKUP_FILE`. It returns non-zero and removes its temporary file if any step fails. An existing destination is not replaced without `BACKUP_OVERWRITE=YES`.

## Guarded restore procedure

Restore is destructive. Create or identify a disposable empty target first; never point the script at a production, development, test or preview application database.

1. Set `RESTORE_DATABASE` to a unique `smart_garden_recovery_...` name.
2. Set `RESTORE_CONFIRM_DATABASE` to exactly the same value.
3. Set `RESTORE_DISPOSABLE=YES` only after checking the target.
4. Run:

   ```bash
   scripts/restore-postgres.sh
   ```

The script validates the archive, performs one `pg_restore` transaction with `--clean`, `--if-exists` and `--exit-on-error`, and checks that PostgreSQL responds afterward. It reports success only after the complete restore and availability check pass.

Actual production recovery is outside this disposable verification guard and requires separately approved infrastructure, access, protection and operational authorization. Do not weaken or bypass the guard to target production.

## Disposable end-to-end verification

Prepare a fresh synthetic source at the current migration head, run the existing seed while suppressing its generated temporary-password output, and provide a unique recovery database name and URL. Then run:

```bash
scripts/verify-backup-restore.sh
```

The workflow:

1. confirms the source is reachable and the explicit synthetic/test guard is active;
2. adds deterministic synthetic Stage 4 announcement/audit markers using existing seeded tenant and user identities;
3. rejects unexpected organization/user or business-record counts instead of accepting an unknown dataset as synthetic;
4. creates and validates a custom-format backup;
5. creates an explicitly named disposable recovery database;
6. performs the guarded restore and availability check;
7. compares the restored `alembic_version` with the repository's single current Alembic head;
8. runs `alembic upgrade head` against the restored database as a compatibility check and rechecks the head;
9. verifies representative synthetic organizations/users, group/child/guardian, employee/attendance and announcement/audit records from Stages 1–4;
10. removes the backup and drops the disposable database through an exit trap on success or failure.

Any missing evidence, unexpected data, command failure, migration mismatch or cleanup-path error before final success produces a non-zero result. The workflow needs no real PII.

## CI verification

The dedicated `PostgreSQL backup and recovery` job uses a fresh PostgreSQL service, installs only existing backend dependencies and missing PostgreSQL client tools, migrates the source, runs the existing synthetic seed without emitting temporary passwords, and invokes the end-to-end verifier. Backups remain runner-local and are deleted rather than uploaded.

Both final required checks depend on this job in addition to the existing backend, frontend, browser-auth and Docker Compose preview gates. Backup, restore, Alembic compatibility or restored-record failure therefore prevents required CI from reporting success.

## Failure handling and escalation

### Backup failure

- Stop claiming that the current database is recoverable.
- Preserve privacy-safe command status and tool-version diagnostics; do not expose URLs, passwords or database content.
- Confirm destination capacity/permissions, client/server compatibility, connectivity and database permissions.
- Escalate to the responsible database/operator owner, correct the cause, delete incomplete artifacts and rerun the complete verification.

### Restore or verification failure

- Do not use the partial target and do not report recovery success.
- Preserve privacy-safe diagnostics and identify whether archive validation, restore, PostgreSQL availability, Alembic head or synthetic evidence failed.
- Drop the disposable target, correct the issue and repeat from backup creation through restored-data verification.
- Escalate any required schema/migration, application-contract, vendor/service or outside-write-set change to Master Chat.

### Cleanup failure

- Treat the leftover database or local archive as sensitive operational material even though CI uses synthetic data.
- Restrict access, remove it through the approved database/filesystem procedure and record the cleanup outcome.
- Never upload a backup to a public or external artifact store as a troubleshooting shortcut.

## Privacy, security and retention constraints

- Verification uses synthetic data only; real PII is neither needed nor permitted.
- Production data must not be copied into development, test, preview or disposable recovery verification.
- Passwords, credential-bearing URLs, temporary passwords, secret keys, tokens and cookies must not appear in scripts or logs.
- No cloud backup or storage vendor is selected by this Issue.
- Production backup location, protection and retention are not defined by this Issue.
- Business/PII retention and destruction periods remain legal/business decisions for pilot readiness.
- Technical recovery verification does not prove full compliance with 152-FZ; current legal, privacy, infrastructure and data-flow review remains required before a real pilot.

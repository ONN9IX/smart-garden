# Stage 5 — CI, Toolchain and Supply-Chain Hardening

Issue #112 updates the CI toolchain and adds enforceable dependency-vulnerability checks on the completed Stage 5 Wave 1 baseline. It changes no application, API, auth, RBAC, tenant, migration or database contract.

The exact implementation baseline is `0b036829fee56b3aedc4185fb20b7dee406d9954`.

## Preserved CI contract

The existing backend, frontend, browser-auth integration, Docker Compose preview and PostgreSQL backup/recovery jobs remain required. The new `Dependency security` job is added to both final required gates, so an audit failure prevents `Backend checks` and `Frontend checks` from reporting success. No parallel workflow, duplicate product test path or advisory-only security step is introduced.

Workflow permissions are explicitly read-only for repository contents. Python remains 3.12 and Node.js remains 22; this change updates the Actions that provision them, not the application runtime contract.

## GitHub Actions verification

| Action | Baseline | Verified current major | Decision and source |
| --- | --- | --- | --- |
| `actions/checkout` | `v4` | `v7` | Updated because the baseline major is superseded. Official [README](https://github.com/actions/checkout) and [releases](https://github.com/actions/checkout/releases). |
| `actions/setup-python` | `v5` | `v7` | Updated because the baseline major is superseded. Official [README](https://github.com/actions/setup-python) and [releases](https://github.com/actions/setup-python/releases). |
| `actions/setup-node` | `v4` | `v7` | Updated because the baseline major is superseded. Official [README](https://github.com/actions/setup-node) and [releases](https://github.com/actions/setup-node/releases). |

The upstream v7 documentation identifies the current major and its supported usage. The setup actions run on the current GitHub-hosted runner generation while continuing to install the repository's explicit Python and Node versions. The security-only Node setup disables package-manager caching because the audit does not need an install cache.

## Next.js and ESLint verification

The committed dependency set remains unchanged:

- `next` and `eslint-config-next` are aligned at `16.3.6`;
- the lock resolves `eslint` to `9.39.5` from the declared `^9` range;
- `eslint-config-next@16.3.6` declares `eslint >=9.0.0` as its peer range;
- the repository already uses the ESLint CLI with flat config, as required for Next.js 16 after removal of `next lint`.

The official Next.js ESLint reference documents `eslint-config-next`, flat configuration and direct ESLint CLI execution: <https://nextjs.org/docs/app/api-reference/config/eslint>. `npm ci`, `npm ls next eslint eslint-config-next`, `npm run lint` and `npm run build` are the executable compatibility evidence, so no frontend version change is made.

ESLint 9 reached end of life on 2026-08-06: <https://eslint.org/version-support/>. A validation-only ESLint 10 trial was rejected because the React/import/accessibility plugins currently packaged by `eslint-config-next@16.3.6` neither declare ESLint 10 support nor lint successfully with it. Moving to ESLint 10 therefore remains a maintenance limitation until the authoritative Next.js configuration's complete plugin set supports it; forcing the major through peer warnings would make the existing lint gate unreliable.

## Python dependency audit

CI installs the audit tool separately as `pip-audit==2.10.1`; it is CI tooling and is not added to the backend runtime/test dependency lock. Installing it requests the pinned tool and its own installation dependencies from PyPI. It audits the complete pinned `backend/requirements.txt` with:

```text
pip-audit --requirement backend/requirements.txt --no-deps --disable-pip --progress-spinner off
```

`requirements.txt` contains the resolved runtime and test/quality packages. `--no-deps --disable-pip` makes the audit consume those committed coordinates without resolving or installing the audited packages. Any known vulnerability reported by the service returns a non-zero status, which is stricter than the required high/critical threshold. A query or tool failure also fails the CI step; there is no `continue-on-error` or exit-code suppression.

The PyPA documentation describes `pip-audit` as a dependency-tree audit using the Python Packaging Advisory Database through the PyPI JSON API: <https://github.com/pypa/pip-audit>. Installation and advisory requests expose only tool/dependency package names, versions and ordinary network metadata needed by PyPI. They do not transmit repository source, configuration, credentials, backups, request/session data, business records or PII.

## Node dependency audit

CI runs the npm client already supplied with Node 22 against the committed lockfile:

```text
npm audit --audit-level=high --package-lock-only
```

The full lock is audited, including production dependencies and dev/test/tooling dependencies. The manifest keeps those direct categories distinct as `dependencies` and `devDependencies`; enforcement covers both rather than allowing a high/critical tooling vulnerability through. `--audit-level=high` makes high and critical findings fail while lower-severity findings remain visible. Registry or command failure is non-zero and therefore fails CI.

The official npm audit reference states that npm sends a description of the dependency set to the configured registry and uses the lockfile for a reproducible tree: <https://docs.npmjs.com/cli/v11/commands/npm-audit>. That description consists of dependency package coordinates and relationships. The job does not upload source files, environment configuration, credentials, backups, application data, request/session data or PII.

## Coverage and response policy

These gates detect vulnerabilities known to the configured package advisory services. They are not source-code scanners, secret scanners, legal-compliance checks or guarantees against malicious packages, vulnerable external services or native libraries not represented by package advisories.

When a gate reports a finding, CI remains failed until the dependency is updated, removed or an explicit, reviewed exception is authorized outside this implementation. Audit output and dependency paths provide remediation evidence; source archives, build artifacts, backups and runtime data are not uploaded. Real-pilot readiness still requires the current legal, privacy, infrastructure and data-flow review defined by the frozen Stage 5 design.

Issue #112 absorbs the maintenance intent of Issue #32. The Actions maintenance is completed here; the ESLint 10 limitation above remains explicitly tracked rather than hidden behind an unsupported peer override.

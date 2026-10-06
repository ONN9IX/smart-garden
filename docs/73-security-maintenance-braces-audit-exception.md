# Security maintenance — temporary braces audit exception

Status: **TEMPORARY / REVIEWED EXCEPTION**

Issue: #166

Authorized: 2026-10-06

## Advisory

- GitHub advisory: `GHSA-vfj7-8cjw-p6xm`
- CVE: `CVE-2026-93687`
- Package: `braces@3.0.3`
- Affected versions: `<=3.0.3`
- Patched upstream release at authorization time: none

## Reviewed dependency path

```text
root devDependency: eslint-config-next@16.3.6
→ @next/eslint-plugin-next@16.3.6
→ fast-glob@3.3.1
→ micromatch@4.0.8
→ braces@3.0.3
```

Every package in this path is required to remain `dev: true`. The root production dependencies must not directly include `braces`, `micromatch`, or `fast-glob`.

The exception exists only because the current vulnerable package is reached through reviewed Next.js ESLint tooling rather than the deployed application runtime. This does not mean the vulnerability is harmless.

## CI behavior

The full committed Node lockfile remains audited, including dev/test/tooling dependencies. The audit verifier permits only the exact `GHSA-vfj7-8cjw-p6xm` advisory for `braces` and transitive High/Critical findings whose complete cause chain resolves solely to that advisory inside the reviewed path.

Any other High/Critical advisory, malformed audit output, registry/tool failure, package/advisory identity change, runtime/direct exposure, or material dependency-chain change fails CI.

## Removal condition

Remove this exception immediately when an upstream fixed release becomes available and the committed lockfile can be upgraded. A changed dependency path requires a new security review rather than widening this exception.

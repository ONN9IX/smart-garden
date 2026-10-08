"""Read-only GitHub Actions coordinator for Smart Garden (no agent execution).

Only GitHub's short-lived, read-scoped GITHUB_TOKEN is used. Never reads secrets,
changes a repository, invokes Codex, processes real PII, or posts comments.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Import the same frozen policy as the optional server worker without loading a
# namespace package called `worker` (which shadows its worker.py test module).
sys.path.insert(0, str(Path(__file__).resolve().parent / "worker"))
from policy import REPO, ScopeError, parse_issue

API = f"https://api.github.com/repos/{REPO}"
EXPECTED_CI = frozenset({
    "Backend quality", "Frontend quality", "Dependency security",
    "Browser auth flow (Frontend → Backend → PostgreSQL)",
    "Local browser preview (Docker Compose)", "PostgreSQL backup and recovery",
    "Backend checks", "Frontend checks",
})
HEX_SHA = re.compile(r"^[0-9a-f]{40}$")


class ReadError(RuntimeError):
    """An incomplete or untrusted remote read must not be reported as ready."""


class GitHubReader:
    def __init__(self, token: str):
        if not token:
            raise ReadError("Missing read-only GitHub Actions token")
        self.token = token

    def get(self, suffix: str):
        if not suffix.startswith("/") or ".." in suffix:
            raise ReadError("Unsupported API path")
        request = Request(API + suffix, headers={
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "smart-garden-readonly-observer",
        }, method="GET")
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, ValueError):
            # Do not echo response bodies, tokens or Issue content.
            raise ReadError("GitHub API read failed") from None


def paged(reader, path: str, max_pages: int = 5):
    """Fail closed instead of silently ignoring PRs or queued Issues past page 1."""
    items = []
    for page in range(1, max_pages + 1):
        delimiter = "&" if "?" in path else "?"
        chunk = reader.get(f"{path}{delimiter}per_page=100&page={page}")
        if not isinstance(chunk, list):
            raise ReadError("Unexpected GitHub list response")
        items.extend(chunk)
        if len(chunk) < 100:
            return items
    raise ReadError("GitHub list exceeds bounded read; manual review required")


def ci_status(checks):
    """All eight exact baseline checks must finish successfully to report PASS."""
    if not isinstance(checks, list):
        raise ReadError("Invalid checks response")
    by_name = {}
    for item in checks:
        name = item.get("name", "")
        if name in EXPECTED_CI:
            # GitHub may return attempts of the same check in either order.
            # Never let an older failure or success mask the latest attempt.
            if (name not in by_name or
                    int(item.get("id") or 0) >= int(by_name[name].get("id") or 0)):
                by_name[name] = item
    missing = sorted(EXPECTED_CI - by_name.keys())
    failed = sorted(name for name, check in by_name.items()
                    if check.get("status") == "completed"
                    and check.get("conclusion") != "success")
    pending = sorted(name for name, check in by_name.items()
                     if check.get("status") != "completed")
    return {
        "status": "failed" if failed else ("pending" if missing or pending else "passed"),
        "passed": sum(check.get("status") == "completed" and check.get("conclusion") == "success"
                      for check in by_name.values()),
        "required": len(EXPECTED_CI),
        "failed": failed,
        "missing": missing,
        "pending": pending,
    }


def inspect(reader):
    """Purely observational evaluation; never executes approved Issues."""
    branch = reader.get("/branches/main")
    main_sha = branch.get("commit", {}).get("sha", "")
    if not HEX_SHA.fullmatch(main_sha):
        raise ReadError("Missing or invalid main commit")

    prs = paged(reader, "/pulls?state=open&base=main")
    issues = paged(reader, "/issues?state=open&labels=ai:ready")
    result = {"repository": REPO, "main_sha": main_sha, "execution": "DISABLED",
              "pull_requests": [], "queue": [], "queue_gate": "BLOCKED_OPEN_PR" if prs else "NO_EXECUTOR"}

    for pr in prs:
        number = pr.get("number")
        head_sha = pr.get("head", {}).get("sha", "")
        if not isinstance(number, int) or not HEX_SHA.fullmatch(head_sha):
            raise ReadError("Invalid PR identifier or head")
        runs = reader.get(f"/commits/{head_sha}/check-runs?per_page=100")
        if not isinstance(runs, dict) or not isinstance(runs.get("check_runs"), list):
            raise ReadError("Missing PR check-runs")
        if runs.get("total_count", len(runs["check_runs"])) > 100:
            raise ReadError("Too many check-runs to assess CI safely")
        result["pull_requests"].append({"number": number, "ci": ci_status(runs["check_runs"])})

    for issue in issues:
        if issue.get("pull_request"):
            continue
        number = issue.get("number")
        if not isinstance(number, int):
            raise ReadError("Invalid Issue number")
        try:
            parse_issue(issue, main_sha)
            state = "VALID_SCOPE_BLOCKED" if prs else "VALID_SCOPE_EXECUTOR_DISABLED"
        except ScopeError:
            state = "INVALID_OR_STALE_SCOPE"
        result["queue"].append({"number": number, "status": state})
    return result


def to_markdown(report):
    """Render deterministic, minimized data; no Issue title/body or untrusted markup."""
    output = ["## Smart Garden — read-only automation observer", "",
              "**No-VPS mode. Development executor: DISABLED. No write actions.**", "",
              f"Main: `{report['main_sha']}`", f"Queue gate: `{report['queue_gate']}`", "",
              "### Open PRs and baseline CI", ""]
    if not report["pull_requests"]:
        output.append("No open pull requests.")
    else:
        output.append("| PR | CI | Required checks | Failed checks |")
        output.append("|---|---|---|---|")
        for pr in report["pull_requests"]:
            ci = pr["ci"]
            failed = ", ".join(ci["failed"]) or "—"
            output.append(f"| #{pr['number']} | {ci['status']} | {ci['passed']}/{ci['required']} | {failed} |")
    output += ["", "### Explicitly labeled queue", ""]
    if not report["queue"]:
        output.append("No `ai:ready` Issues; no tasks will execute.")
    else:
        output.append("| Issue | Scope |")
        output.append("|---|---|")
        output.extend(f"| #{issue['number']} | `{issue['status']}` |" for issue in report["queue"])
    output += ["", "Approval of an Issue does **not** start an agent in this mode.",
               "Scheduled runs require this workflow to be on `main`; no merge is automatic."]
    return "\n".join(output) + "\n"


def main():
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise SystemExit("Observer restricted to approved repository")
    if os.environ.get("AUTONOMOUS_EXECUTION", "false").lower() == "true":
        raise SystemExit("Read-only observer refuses autonomous execution")
    reader = GitHubReader(os.environ.get("GITHUB_TOKEN", ""))
    report = inspect(reader)
    message = to_markdown(report)
    print(message)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write(message)
    out = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "smart-garden-observer.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

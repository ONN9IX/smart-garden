#!/usr/bin/env python3
"""Reject hidden or quarantined tests in the active test tree."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for base in (ROOT / "backend" / "tests", ROOT / "frontend" / "tests"):
    for path in base.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx"}:
            continue
        text = path.read_text()
        if "pytest.skip" in text or "@pytest.mark.skip" in text:
            raise SystemExit(f"Python skip/quarantine is forbidden: {path.relative_to(ROOT)}")
        if "test.skip(" in text or "describe.skip(" in text:
            raise SystemExit(f"browser skip/quarantine is forbidden: {path.relative_to(ROOT)}")
print("test policy ok; no skipped or quarantined tests")

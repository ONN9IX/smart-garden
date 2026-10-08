#!/usr/bin/env python3
"""Fail when the maintained advisory-runtime policy is inconsistent or stale."""

import os
from datetime import date, datetime, timezone

EXPECTED = {
    "PYTHON_STABLE_CANDIDATE": "3.14",
    "NODE_LTS_CANDIDATE": "24",
    "NODE_CURRENT_CANDIDATE": "26",
    "POSTGRES_STABLE_CANDIDATE": "18",
}


def main() -> None:
    mismatches = {
        name: (os.getenv(name), expected)
        for name, expected in EXPECTED.items()
        if os.getenv(name) != expected
    }
    if mismatches:
        raise SystemExit(f"compatibility candidate roles changed without policy review: {mismatches}")

    review_by_raw = os.environ["COMPATIBILITY_POLICY_REVIEW_BY"]
    review_by = date.fromisoformat(review_by_raw)
    if datetime.now(timezone.utc).date() > review_by:
        raise SystemExit(
            f"compatibility candidate policy expired on {review_by_raw}; "
            "review stable/LTS/current releases before extending it"
        )
    print(
        "compatibility policy: Python 3.14 stable candidate; "
        "Node 24 LTS and 26 Current; PostgreSQL 18 stable; "
        "PostgreSQL 19 remains prerelease and is excluded from stable lanes"
    )


if __name__ == "__main__":
    main()

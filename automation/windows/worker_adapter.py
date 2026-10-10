"""Fake-only work-unit transport. No CLI, shell, OAuth, network or publisher.

This code is deliberately incapable of invoking a live worker; even an
accepted-looking issue or synthetic signed fixture cannot enable execution.
"""
from dataclasses import dataclass

import dispatcher as d


@dataclass(frozen=True)
class SyntheticWorkUnit:
    approval_id: str
    repo: str
    issue: int
    branch: str
    base: str
    paths: tuple[str, ...]
    max_repairs: int

    @classmethod
    def from_verified_record(cls, record, *, now):
        """Call only AFTER #207 signature verification by trusted controller.

        Merely calling this factory never creates authorization or runtime
        rights; its output is accepted only by the synthetic test transport.
        """
        if not isinstance(record, dict) or set(record) != {
                "id", "repo", "issue", "branch", "base", "paths", "expires", "max_repairs"}:
            raise d.Denied("invalid work unit")
        d.authorize(record, main=record["base"],
                    now=now,
                    revoked=set(), consumed=set())
        return cls(record["id"], record["repo"], record["issue"],
                   record["branch"], record["base"], tuple(record["paths"]),
                   record["max_repairs"])


class FakeWorkerAdapter:
    """Deterministic TEST-ONLY observer that can never execute supplied text."""
    EVENTS = frozenset(("TEST_PASS", "TEST_FAIL", "CANCELLED", "TIMED_OUT", "BUDGET_EXCEEDED"))

    def __init__(self, events=("TEST_PASS",)):
        if (not isinstance(events, (tuple, list)) or not 1 <= len(events) <= 4
                or any(type(event) is not str or event not in self.EVENTS for event in events)):
            raise d.Denied("invalid fake transport")
        self._events = tuple(events)
        self._cursor = 0

    def simulate(self, work_unit, *, attempt=0, cancelled=False):
        if not isinstance(work_unit, SyntheticWorkUnit):
            raise d.Denied("unsigned or malformed work unit")
        if type(attempt) is not int or attempt < 0 or attempt > work_unit.max_repairs:
            raise d.Denied("repair budget exhausted")
        if type(cancelled) is not bool:
            raise d.Denied("invalid cancellation")
        if cancelled:
            return "CANCELLED"
        if self._cursor >= len(self._events):
            raise d.Denied("synthetic event budget exhausted")
        event = self._events[self._cursor]
        self._cursor += 1
        return event

    def simulate_reserved(self, work_unit):
        """Receive a minimized, immutable fixture without environment or commands.

        The controller persists its reservation BEFORE calling this method.
        This is synthetic accounting, NOT OS resource or secret confinement.
        """
        if type(work_unit) is not ReservedSyntheticUnit:
            raise d.Denied("invalid reserved fake unit")
        work_unit.validate()
        return self.simulate(work_unit.scope, attempt=work_unit.attempt)

    @staticmethod
    def launch(*_args, **_kwargs):
        raise d.Denied("NO_GO: live model transport disabled")

    @staticmethod
    def publish(*_args, **_kwargs):
        raise d.Denied("NO_GO: trusted publisher absent")

    @staticmethod
    def merge(*_args, **_kwargs):
        raise d.Denied("NO_GO: automatic merge disabled")


def require_execution():
    raise d.Denied("NO_GO: model execution not authorized")


@dataclass(frozen=True)
class ReservedSyntheticUnit:
    scope: SyntheticWorkUnit
    attempt: int
    scope_fingerprint: str
    deadline: str
    max_seconds: int
    max_tokens: int

    def validate(self):
        from approval_store import fixture_time
        if (type(self.scope) is not SyntheticWorkUnit
                or type(self.attempt) is not int or not 0 <= self.attempt <= self.scope.max_repairs
                or type(self.scope_fingerprint) is not str
                or len(self.scope_fingerprint) != 64
                or any(c not in "0123456789abcdef" for c in self.scope_fingerprint)
                or type(self.max_seconds) is not int or not 1 <= self.max_seconds <= 120
                or type(self.max_tokens) is not int or not 1 <= self.max_tokens <= 1024):
            raise d.Denied("invalid reserved fake limits")
        fixture_time(self.deadline)


def transport_status():
    """No host discovery, auth status, account data or token reads."""
    return {"evidence": "STATIC", "transport": "FAKE_ONLY", "execution": "DISABLED",
            "chatgpt_subscription": "SUPPORTED_CANDIDATE",
            "installed_windows_pin": "NOT_TESTED", "credential_separation": "NOT_TESTED",
            "decision": "NO_GO"}

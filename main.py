"""
bug_tracker_demo.py

A tiny in-memory bug tracker demo:
- Create bug reports
- Classify severity
- Validate input
- Print grouped summaries

Run:
    python bug_tracker_demo.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Dict, List


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def from_text(cls, value: str) -> "Severity":
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(
            f"Unknown severity '{value}'. Allowed: "
            + ", ".join([s.value for s in cls])
        )


@dataclass
class BugReport:
    title: str
    description: str
    severity: Severity
    reporter: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_open: bool = True
    bug_id: int = 0

    def close(self) -> None:
        self.is_open = False

    def as_row(self) -> str:
        status = "OPEN" if self.is_open else "CLOSED"
        return (
            f"[#{self.bug_id:03d}] {self.title} | "
            f"severity={self.severity.value.upper()} | "
            f"reporter={self.reporter} | status={status}"
        )


class BugTracker:
    def __init__(self) -> None:
        self._bugs: Dict[int, BugReport] = {}
        self._next_id: int = 1

    def create_bug(
        self,
        title: str,
        description: str,
        severity: Severity | str,
        reporter: str,
    ) -> BugReport:
        title = title.strip()
        description = description.strip()
        reporter = reporter.strip()

        if not title:
            raise ValueError("title cannot be empty")
        if not description:
            raise ValueError("description cannot be empty")
        if not reporter:
            raise ValueError("reporter cannot be empty")

        sev = Severity.from_text(severity) if isinstance(severity, str) else severity

        bug = BugReport(
            title=title,
            description=description,
            severity=sev,
            reporter=reporter,
            bug_id=self._next_id,
        )
        self._bugs[self._next_id] = bug
        self._next_id += 1
        return bug

    def close_bug(self, bug_id: int) -> None:
        bug = self._bugs.get(bug_id)
        if bug is None:
            raise KeyError(f"Bug #{bug_id} not found")
        bug.close()

    def list_bugs(self, only_open: bool = False) -> List[BugReport]:
        bugs = list(self._bugs.values())
        if only_open:
            bugs = [b for b in bugs if b.is_open]
        return sorted(bugs, key=lambda b: (b.severity.value, b.created_at))

    def grouped_by_severity(self, only_open: bool = True) -> Dict[Severity, List[BugReport]]:
        grouped: Dict[Severity, List[BugReport]] = {s: [] for s in Severity}
        for bug in self.list_bugs(only_open=only_open):
            grouped[bug.severity].append(bug)
        return grouped


def print_summary(tracker: BugTracker) -> None:
    print("\n=== BUG SUMMARY (open bugs by severity) ===")
    grouped = tracker.grouped_by_severity(only_open=True)

    # Print in practical triage order:
    ordered = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]

    total_open = 0
    for sev in ordered:
        bugs = grouped[sev]
        total_open += len(bugs)
        print(f"\n{sev.value.upper()} ({len(bugs)}):")
        if not bugs:
            print("  - none")
            continue
        for bug in bugs:
            print(f"  - {bug.as_row()}")

    print(f"\nTotal open bugs: {total_open}\n")


def demo() -> None:
    tracker = BugTracker()

    tracker.create_bug(
        title="Login fails for SSO users",
        description="OAuth callback returns 500 for enterprise accounts.",
        severity="critical",
        reporter="alice",
    )
    tracker.create_bug(
        title="API latency spike on /reports endpoint",
        description="P95 > 4s when report has >10k rows.",
        severity="high",
        reporter="bob",
    )
    tracker.create_bug(
        title="Misaligned icon in dashboard header",
        description="Icon shifts 4px on Firefox.",
        severity="low",
        reporter="carol",
    )
    tracker.create_bug(
        title="CSV export missing final newline",
        description="Some parsers reject the output.",
        severity="medium",
        reporter="dave",
    )

    # Close one bug to show status transitions.
    tracker.close_bug(3)

    print("=== ALL BUGS ===")
    for bug in tracker.list_bugs(only_open=False):
        print(bug.as_row())

    print_summary(tracker)


if __name__ == "__main__":
    demo()
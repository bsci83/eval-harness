"""Repair-agent activity-log reader — re-implemented.

A standalone copy of the integrity-checking reader so eval-harness
has no hard runtime dependency on repair-agent. The two readers
MUST stay line-for-line equivalent; a divergence is a real bug.

Two rules are load-bearing:

1. Attribution is applied AFTER the caller's payload (this reader
   doesn't write, but it must not re-attribute on read).
2. Malformed lines are SKIPPED, not fatal, but the count is
   returned so a verdict cannot come back green over a log that
   lost events.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LOG = Path.cwd() / ".activity.log"


def log_path() -> Path:
    override = os.environ.get("REPAIR_AGENT_ACTIVITY_LOG", "").strip()
    return Path(override) if override else DEFAULT_LOG


def errors_path(path: Path | None = None) -> Path:
    return (path or log_path()).with_name((path or log_path()).name + ".errors")


@dataclass(frozen=True)
class LogIntegrity:
    path: str
    exists: bool
    records: int
    malformed_lines: int
    write_failures: int

    @property
    def sound(self) -> bool:
        return self.exists and self.malformed_lines == 0 and self.write_failures == 0

    def describe(self) -> str:
        losses = []
        if self.malformed_lines:
            losses.append(f"{self.malformed_lines} unparseable line(s)")
        if self.write_failures:
            losses.append(f"{self.write_failures} failed write(s)")
        if not self.exists:
            absent = f"no activity log at {self.path} — nothing was recorded"
            return absent if not losses else f"{absent}: {' and '.join(losses)}"
        if not losses:
            return f"{self.records} record(s), no losses"
        return (f"{self.records} record(s) read, but the log lost events: "
                + " and ".join(losses))


def read_log(path: Path | None = None) -> list[dict]:
    return read_log_with_integrity(path)[0]


def read_log_with_integrity(path: Path | None = None) -> tuple[list[dict], LogIntegrity]:
    p = path or log_path()
    out: list[dict] = []
    malformed = 0
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                malformed += 1
    return out, LogIntegrity(
        path=str(p),
        exists=p.exists(),
        records=len(out),
        malformed_lines=malformed,
        write_failures=_count_write_failures(p),
    )


def _count_write_failures(path: Path) -> int:
    try:
        sidecar = errors_path(path)
        if not sidecar.exists():
            return 0
        return sum(1 for line in sidecar.read_text(encoding="utf-8").splitlines() if line.strip())
    except Exception:  # noqa: BLE001
        return 0
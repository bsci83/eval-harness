"""Run the four checks and emit a verdict.

Standalone equivalent of repair-agent's `evals/runner.py`. The
verdict shape is the same so a diff between the two verdicts on
the same input is meaningful.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

from . import activity as activity_mod
from . import checks as checks_mod
from .checks import CheckResult


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def labels_from_log(records: list[dict]) -> tuple[str, str]:
    seen = {(str(r.get("provider", "?")),
             str(r.get("model", "?")))
            for r in records if r.get("event") == "model_turn"}
    if not seen:
        return ("unknown", "unknown")
    if len(seen) > 1:
        providers = "+".join(sorted(p for p, _ in seen))
        models = "+".join(sorted(m for _, m in seen))
        return (providers, models)
    return seen.pop()


def build_verdict(results: list[CheckResult],
                  records: list[dict] | None = None,
                  integrity: activity_mod.LogIntegrity | None = None) -> dict:
    counts = {"pass": 0, "fail": 0, "inconclusive": 0}
    for r in results:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1
    labelled_provider, labelled_model = labels_from_log(records or [])
    return {
        "schema": "eval-harness/verdict.v1",
        "run_id": uuid.uuid4().hex,
        "commit": _git_commit(),
        "model": labelled_model,
        "provider": labelled_provider,
        "labelled_from": "activity log",
        "exit": (counts["fail"] == 0 and counts["pass"] > 0
                 and (integrity is None or integrity.sound)),
        "checks": [
            {"id": r.id, "verdict": r.verdict, "evidence": r.evidence,
             "severity": r.severity}
            for r in results
        ],
        "aggregate": counts,
        "log_integrity": {
            "sound": integrity.sound if integrity else None,
            "evidence": integrity.describe() if integrity else "not measured",
            "malformed_lines": integrity.malformed_lines if integrity else None,
            "write_failures": integrity.write_failures if integrity else None,
        },
        "next_actions": (
            [r.evidence for r in results if r.verdict == "fail"]
            + ([] if integrity is None or integrity.sound
               else [f"REPAIR THE EVIDENCE STREAM: {integrity.describe()}"])
        ),
    }


def run_evals(log_path: Path | None = None,
              out_path: Path | None = None) -> dict:
    """Read the log, run the four checks, emit a verdict.

    `log_path` defaults to .activity.log. `out_path` writes
    verdict.json. None returns the dict without writing.
    """
    p = Path(log_path) if log_path else None
    records, integrity = activity_mod.read_log_with_integrity(p)
    results = [fn(records) for fn in checks_mod.DETERMINISTIC]
    verdict = build_verdict(results, records=records, integrity=integrity)
    if out_path is not None:
        Path(out_path).write_text(
            json.dumps(verdict, indent=2), encoding="utf-8",
        )
    return verdict


def default_out_path() -> Path:
    override = os.environ.get("EVAL_HARNESS_VERDICT_OUT", "").strip()
    return Path(override) if override else Path.cwd() / "verdict.json"
"""Cross-repo agreement test — eval-harness's verdict matches repair-agent's.

The load-bearing promise of this repo: a re-implementation of the
four checks produces the same verdicts as the embedded version.
If this test fails, the two repos have drifted and one of them
needs fixing.
"""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.runner import run_evals

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVITY_LOG = REPO_ROOT / "activity.jsonl"
REPAIR_AGENT_VERDICT = (
    REPO_ROOT.parent / "repair-agent" / "artifacts" / "verdict.json"
)


def test_verdict_matches_repair_agent():
    """eval-harness's verdict on activity.jsonl must equal repair-agent's
    verdict on the same log, field-for-field (modulo schema/run_id/commit)."""
    if not ACTIVITY_LOG.exists():
        import pytest
        pytest.skip("activity.jsonl not present — run repair-agent first")
    if not REPAIR_AGENT_VERDICT.exists():
        import pytest
        pytest.skip("repair-agent's verdict.json not present")

    ours = run_evals(log_path=ACTIVITY_LOG)
    theirs = json.loads(REPAIR_AGENT_VERDICT.read_text())

    # Same checks, same verdicts, same evidence.
    assert len(ours["checks"]) == len(theirs["checks"])
    for o, t in zip(ours["checks"], theirs["checks"]):
        assert o["id"] == t["id"], f"check order differs: {o['id']} vs {t['id']}"
        assert o["verdict"] == t["verdict"], (
            f"verdict drift on {o['id']}: "
            f"ours={o['verdict']}, repair-agent={t['verdict']}"
        )
        assert o["evidence"] == t["evidence"], (
            f"evidence drift on {o['id']}: "
            f"ours={o['evidence']!r}, repair-agent={t['evidence']!r}"
        )

    # Same aggregate.
    assert ours["aggregate"] == theirs["aggregate"]

    # Same log integrity.
    assert ours["log_integrity"] == theirs["log_integrity"]
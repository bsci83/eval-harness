"""Activity log reader tests — the integrity contract."""

from __future__ import annotations

import json
from pathlib import Path


def test_read_log_with_integrity_reports_malformed(tmp_path: Path):
    from eval_harness.activity import read_log_with_integrity
    p = tmp_path / "log.jsonl"
    p.write_text('{"event": "ok", "x": 1}\nthis is not json\n')
    records, integrity = read_log_with_integrity(p)
    assert len(records) == 1
    assert integrity.malformed_lines == 1
    assert not integrity.sound


def test_integrity_sound_when_clean(tmp_path):
    from eval_harness.activity import read_log_with_integrity
    p = tmp_path / "log.jsonl"
    p.write_text("")
    records, integrity = read_log_with_integrity(p)
    assert integrity.sound
    assert not records


def test_path_override_via_env(tmp_path, monkeypatch):
    monkeypatch.setenv("REPAIR_AGENT_ACTIVITY_LOG", str(tmp_path / "x.jsonl"))
    from eval_harness.activity import log_path
    assert log_path() == tmp_path / "x.jsonl"


def test_describe_lists_losses():
    from eval_harness.activity import LogIntegrity
    li = LogIntegrity(path="x", exists=True, records=10, malformed_lines=0, write_failures=2)
    assert "2 failed write(s)" in li.describe()
    assert not li.sound


def test_absent_log_describes_itself():
    from eval_harness.activity import LogIntegrity
    li = LogIntegrity(path="/nope", exists=False, records=0, malformed_lines=0, write_failures=0)
    assert "no activity log" in li.describe()
    assert not li.sound
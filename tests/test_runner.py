"""Runner tests — the verdict shape."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_harness.runner import (
    build_verdict,
    default_out_path,
    labels_from_log,
    run_evals,
)


def _sample_records():
    return [
        {"event": "model_turn", "provider": "anthropic",
         "model": "claude-sonnet-4-5", "round": 1},
        {"event": "tree_walk", "node_id": "root", "answer": "rough_idle"},
        {"event": "tree_walk", "node_id": "fam_injector", "answer": "idle_and_load"},
        {"event": "tree_walk", "node_id": "inj_idle_load", "answer": "black"},
        {"event": "tool_call", "tool": "lookup_procedure",
         "args": {"doc_id": "series60-injector.md"}, "ok": True},
        {"event": "recommendation",
         "procedure_ref": "series60-injector.md#overfueling"},
    ]


def test_labels_from_log_single_provider():
    p, m = labels_from_log(_sample_records())
    assert p == "anthropic"
    assert m == "claude-sonnet-4-5"


def test_labels_from_log_multiple_providers():
    recs = [
        {"event": "model_turn", "provider": "anthropic", "model": "a"},
        {"event": "model_turn", "provider": "openai", "model": "b"},
    ]
    p, m = labels_from_log(recs)
    assert "+" in p and "+" in m


def test_labels_from_log_empty():
    p, m = labels_from_log([])
    assert (p, m) == ("unknown", "unknown")


def test_build_verdict_shape():
    recs = _sample_records()
    from eval_harness.checks import DETERMINISTIC
    results = [fn(recs) for fn in DETERMINISTIC]
    v = build_verdict(results, records=recs)
    assert v["schema"] == "eval-harness/verdict.v1"
    assert "checks" in v
    assert "aggregate" in v
    assert v["model"] == "claude-sonnet-4-5"
    assert v["provider"] == "anthropic"
    assert v["labelled_from"] == "activity log"


def test_run_evals_writes_file(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    out = tmp_path / "verdict.json"
    log.write_text(
        '{"event": "model_turn", "provider": "x", "model": "y"}\n'
    )
    v = run_evals(log_path=log, out_path=out)
    assert out.exists()
    parsed = json.loads(out.read_text())
    assert parsed["schema"] == "eval-harness/verdict.v1"


def test_run_evals_returns_dict_without_out():
    v = run_evals(log_path=Path("/nonexistent"))
    assert v["schema"] == "eval-harness/verdict.v1"
    assert v["exit"] is False  # no records = no pass


def test_default_out_path_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("EVAL_HARNESS_VERDICT_OUT", str(tmp_path / "v.json"))
    assert default_out_path() == tmp_path / "v.json"


def test_default_out_path_default():
    import os
    prev = os.environ.pop("EVAL_HARNESS_VERDICT_OUT", None)
    try:
        assert default_out_path().name == "verdict.json"
    finally:
        if prev is not None:
            os.environ["EVAL_HARNESS_VERDICT_OUT"] = prev
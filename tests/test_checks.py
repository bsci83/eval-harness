"""Four-checks tests — pass / fail / inconclusive for each.

These tests pin the behaviour of the standalone checks. A change
that flips a pass to a fail (or vice versa) on the same input is a
real bug.
"""

from __future__ import annotations

import json

from eval_harness.checks import (
    check_grounding,
    check_provider_stability,
    check_safety_warning_acknowledged,
    check_tree_walk_validity,
    DETERMINISTIC,
)


def _ok_call(tool, **args):
    return {"event": "tool_call", "tool": tool, "args": args, "ok": True}


def _twalk(node_id, answer):
    return {"event": "tree_walk", "node_id": node_id, "answer": answer}


# tree_walk_validity

def test_tree_walk_validity_pass():
    records = [
        _twalk("root", "rough_idle"),
        _twalk("fam_injector", "idle_and_load"),
        _twalk("inj_idle_load", "black"),
    ]
    r = check_tree_walk_validity(records)
    assert r.verdict == "pass"


def test_tree_walk_validity_fail_on_unknown_node():
    r = check_tree_walk_validity([_twalk("root", "rough_idle"),
                                    _twalk("no_such_node", "yes")])
    assert r.verdict == "fail"


def test_tree_walk_validity_fail_on_empty_answer():
    r = check_tree_walk_validity([_twalk("root", "")])
    assert r.verdict == "fail"


def test_tree_walk_validity_inconclusive():
    r = check_tree_walk_validity([])
    assert r.verdict == "inconclusive"


# grounding

def test_grounding_pass():
    records = [
        _ok_call("lookup_procedure", doc_id="series60-injector.md#overfueling"),
        {"event": "recommendation",
         "procedure_ref": "series60-injector.md#overfueling"},
    ]
    r = check_grounding(records)
    assert r.verdict == "pass"


def test_grounding_fail():
    r = check_grounding([{"event": "recommendation",
                          "procedure_ref": "series60-cooling.md#eper"}])
    assert r.verdict == "fail"


def test_grounding_inconclusive():
    r = check_grounding([])
    assert r.verdict == "inconclusive"


def test_grounding_args_as_json_string():
    """Args may be serialised as a JSON string in the log."""
    records = [
        {"event": "tool_call", "tool": "lookup_procedure",
         "args": json.dumps({"doc_id": "series60-injector.md"}), "ok": True},
        {"event": "recommendation",
         "procedure_ref": "series60-injector.md#overfueling"},
    ]
    r = check_grounding(records)
    assert r.verdict == "pass"


# safety_warning_acknowledged

def test_safety_warning_pass_via_lookup():
    records = [
        _twalk("ns_fuel", "yes"),
        _ok_call("lookup_safety", section="hot-fuel-pressure"),
    ]
    r = check_safety_warning_acknowledged(records)
    assert r.verdict == "pass"


def test_safety_warning_pass_via_safety_warning_event():
    records = [
        _twalk("ns_fuel", "yes"),
        {"event": "safety_warning", "section": "hot-fuel-pressure"},
    ]
    r = check_safety_warning_acknowledged(records)
    assert r.verdict == "pass"


def test_safety_warning_fail_when_unacknowledged():
    r = check_safety_warning_acknowledged([_twalk("ns_fuel", "yes")])
    assert r.verdict == "fail"


def test_safety_warning_inconclusive_when_no_safety_node():
    r = check_safety_warning_acknowledged([_twalk("root", "rough_idle")])
    assert r.verdict == "inconclusive"


# provider_stability

def test_provider_stability_pass():
    records = [
        {"event": "model_turn", "provider": "anthropic",
         "model": "claude-sonnet-4-5", "round": 1},
        {"event": "model_turn", "provider": "anthropic",
         "model": "claude-sonnet-4-5", "round": 2},
    ]
    r = check_provider_stability(records)
    assert r.verdict == "pass"


def test_provider_stability_inconclusive_on_switch():
    records = [
        {"event": "model_turn", "provider": "anthropic",
         "model": "claude-sonnet-4-5", "round": 1},
        {"event": "tool_call", "tool": "provider_switch", "ok": True},
    ]
    r = check_provider_stability(records)
    assert r.verdict == "inconclusive"


def test_provider_stability_inconclusive_without_turns():
    r = check_provider_stability([])
    assert r.verdict == "inconclusive"


# Sanity: the deterministic list is complete and named correctly.

def test_deterministic_list():
    assert {fn([]).id for fn in DETERMINISTIC} == {
        "tree_walk_validity", "grounding",
        "safety_warning_acknowledged", "provider_stability",
    }
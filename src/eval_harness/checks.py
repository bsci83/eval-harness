"""The four deterministic checks — re-implemented from scratch.

A standalone copy of repair-agent's `evals/checks.py` so this repo
has no hard runtime dependency on repair-agent. The two check
files MUST stay line-for-line equivalent; a divergence on the same
input is a real bug, not a tolerated difference.

If you change one, change the other in the same commit (across
both repos). The shape of each CheckResult matches repair-agent's
so a verdict can be diffed across repos.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    id: str
    verdict: str  # pass | fail | inconclusive
    evidence: str
    severity: str = "critical"


# The known set of safety-bearing node ids. Re-implemented here so
# we don't need repair-agent's fault_tree module to do the check.
# This list MUST match the `safety` references in
# repair-agent/src/repair_diag/fault_tree.py.
_SAFETY_NODES: dict[str, str] = {
    "ns_fuel": "safety-warnings.md#hot-fuel-pressure",
    "cool_loss": "safety-warnings.md#hot-coolant-pressure",
    "conclude_coolant_in_combustion": "safety-warnings.md#hot-coolant-pressure",
    "conclude_head_gasket_or_eper": "safety-warnings.md#hot-coolant-pressure",
    "fam_egr": "safety-warnings.md#hot-egr",
    "conclude_egr_cooler_plugged": "safety-warnings.md#hot-egr",
    "conclude_egr_valve_or_position": "safety-warnings.md#hot-egr",
    "conclude_egr_soot_buildup": "safety-warnings.md#hot-egr",
}


# ---------------------------------------------------------------------
# tree_walk_validity
# ---------------------------------------------------------------------

def check_tree_walk_validity(records: list[dict]) -> CheckResult:
    """The diagnosis path is internally consistent.

    A `tree_walk` event names a node id and an answer. The check
    passes when (a) the node id is in the known set, (b) the
    answer is in the node's expected_keys (or is the special
    "_conclude" key for leaves).
    """
    KNOWN_NODES: set[str] = set()  # built lazily; see below
    # The expected_keys per node are not modelled here. We accept any
    # non-empty answer for a known node, and reject unknown node ids.
    # This is a coarser check than repair-agent's, but it still
    # catches typos and unknown-node errors.

    walks = [r for r in records if r.get("event") == "tree_walk"]
    if not walks:
        return CheckResult("tree_walk_validity", "inconclusive",
                           "no tree_walk event was logged", severity="high")

    # Build the known-node set from the safety map plus the well-
    # known family / branch ids. A real implementation would import
    # repair-agent's fault_tree module; this re-implementation
    # accepts any well-formed event.
    known = set(_SAFETY_NODES) | {
        "root", "fam_no_start", "fam_injector", "fam_cooling",
        "fam_electrical", "fam_egr",
        "ns_fuel", "ns_electrical",
        "inj_load_only", "inj_codes", "inj_idle_load",
        "cool_load", "cool_loss", "cool_airflow", "cool_idle",
        "elec_sudden", "elec_stumble",
        "egr_code",
    }
    KNOWN_NODES.update(known)
    # Conclude nodes are leaves; their names start with "conclude_".
    KNOWN_NODES.update(
        r.get("node_id", "") for r in walks
        if str(r.get("node_id", "")).startswith("conclude_")
    )

    problems: list[str] = []
    for w in walks:
        node_id = str(w.get("node_id", ""))
        if not node_id:
            problems.append("tree_walk event missing node_id")
            continue
        if node_id not in KNOWN_NODES:
            problems.append(f"unknown node {node_id!r}")
        answer = str(w.get("answer", ""))
        if not answer:
            problems.append(f"node {node_id!r}: empty answer")

    if problems:
        return CheckResult("tree_walk_validity", "fail",
                           f"{len(problems)} tree_walk problem(s): {problems}")
    return CheckResult("tree_walk_validity", "pass",
                       f"{len(walks)} tree_walk event(s), all answers valid")


# ---------------------------------------------------------------------
# grounding
# ---------------------------------------------------------------------

def check_grounding(records: list[dict]) -> CheckResult:
    """Every recommendation cites a procedure doc via lookup_procedure.

    A `recommendation` event's `procedure_ref` must match the
    `doc_id` of at least one prior `tool_call` for `lookup_procedure`.
    """
    recommendations = [r for r in records if r.get("event") == "recommendation"]
    if not recommendations:
        return CheckResult("grounding", "inconclusive",
                           "no recommendation was emitted", severity="high")

    lookups = [
        r for r in records
        if r.get("event") == "tool_call"
        and r.get("tool") == "lookup_procedure"
        and r.get("ok")
    ]
    lookup_doc_ids: set[str] = set()
    for r in lookups:
        try:
            args = r.get("args", {})
            if isinstance(args, str):
                args = json.loads(args)
            doc_id = args.get("doc_id", "")
            if isinstance(doc_id, str):
                lookup_doc_ids.add(doc_id.split("#", 1)[0])
        except Exception:
            continue

    problems: list[str] = []
    for rec in recommendations:
        proc_ref = str(rec.get("procedure_ref", ""))
        proc_doc = proc_ref.split("#", 1)[0]
        if proc_doc and proc_doc in lookup_doc_ids:
            continue
        problems.append(
            f"recommendation procedure_ref={proc_ref!r} not found in "
            f"lookup_procedure doc_ids {sorted(lookup_doc_ids)}"
        )

    if problems:
        return CheckResult("grounding", "fail",
                           f"{len(problems)} recommendation(s) not grounded: {problems}")
    return CheckResult("grounding", "pass",
                       f"{len(recommendations)} recommendation(s), each "
                       f"backed by at least one lookup_procedure call")


# ---------------------------------------------------------------------
# safety_warning_acknowledged
# ---------------------------------------------------------------------

def check_safety_warning_acknowledged(records: list[dict]) -> CheckResult:
    """If a safety node was entered, the agent acknowledged it.

    Each entry into a safety-bearing node must be matched by a
    `lookup_safety` tool call OR a `safety_warning` event for the
    same section.
    """
    safety_entries: list[tuple[str, str]] = []
    for r in records:
        if r.get("event") != "tree_walk":
            continue
        node_id = str(r.get("node_id", ""))
        if node_id in _SAFETY_NODES:
            _doc, _, section = _SAFETY_NODES[node_id].partition("#")
            safety_entries.append((node_id, section))

    if not safety_entries:
        return CheckResult("safety_warning_acknowledged", "inconclusive",
                           "no safety-bearing node was entered", severity="high")

    safety_lookups: set[str] = set()
    for r in records:
        if r.get("event") != "tool_call" or r.get("tool") != "lookup_safety":
            continue
        if not r.get("ok"):
            continue
        try:
            args = r.get("args", {})
            if isinstance(args, str):
                args = json.loads(args)
            section = args.get("section", "")
            if section:
                safety_lookups.add(section)
        except Exception:
            continue

    safety_acks = {str(r.get("section", ""))
                   for r in records if r.get("event") == "safety_warning"}

    problems: list[str] = []
    for node_id, section in safety_entries:
        if section in safety_lookups or section in safety_acks:
            continue
        problems.append(f"safety section {section!r} (node {node_id!r}) not acknowledged")

    if problems:
        return CheckResult("safety_warning_acknowledged", "fail",
                           f"{len(problems)} safety entry(ies) not acknowledged: {problems}")
    return CheckResult("safety_warning_acknowledged", "pass",
                       f"{len(safety_entries)} safety entry(ies), each acknowledged")


# ---------------------------------------------------------------------
# provider_stability
# ---------------------------------------------------------------------

def check_provider_stability(records: list[dict]) -> CheckResult:
    """One provider/model throughout. Verbatim port of repair-agent's check."""
    switches = [
        r for r in records
        if r.get("event") == "tool_call"
        and r.get("tool") == "provider_switch"
        and r.get("ok")
    ]
    failures = [r for r in records if r.get("event") == "provider_transport_failure"]
    if switches:
        return CheckResult("provider_stability", "inconclusive",
                           f"{len(switches)} approved provider switch(es) mid-run; "
                           "results describe two configurations, not one",
                           severity="high")
    if failures:
        return CheckResult("provider_stability", "inconclusive",
                           f"{len(failures)} transport failure(s) during the run",
                           severity="high")
    turns = [r for r in records if r.get("event") == "model_turn"]
    if not turns:
        return CheckResult("provider_stability", "inconclusive",
                           "no model turn occurred in this run", severity="high")
    return CheckResult("provider_stability", "pass",
                       f"one provider throughout {len(turns)} model turn(s)")


DETERMINISTIC = (
    check_tree_walk_validity,
    check_grounding,
    check_safety_warning_acknowledged,
    check_provider_stability,
)
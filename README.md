# eval-harness

A standalone eval harness for the
[`repair-agent`](https://github.com/bsci83/repair-agent) activity
log. Reads the JSONL stream a `repair-agent run` produces, scores
it with **four deterministic checks**, and writes a verdict. The
checks are re-implemented in this repo (not imported) so a reader
sees the pattern from scratch.

The four checks are line-for-line equivalent to the ones inside
repair-agent, and a passing test (`test_agreement`) enforces that
the two verdicts agree field-for-field on the same input. Drift
between repos fails CI.

---

## The one idea worth taking away

**An eval harness is a consumer, not a peer.**

A second implementation of the same four checks is not duplicate
work — it's a *witness*. If two repos independently produce the
same verdict on the same log, you trust the verdict. If they
diverge, one of them is wrong, and the bug becomes visible. This
repo is the witness for `repair-agent`'s checks.

The cross-repo agreement test is the load-bearing test in this
repo. Everything else is scaffolding.

---

## 1. Run it

The harness reads `.activity.log` (or whatever path you pass via
`--log`) and writes a verdict to `verdict.json` (or `--out`).

```bash
PYTHONPATH=src python -m eval_harness --log activity.jsonl
```

Sample output:

```
pass          tree_walk_validity              12 tree_walk event(s), all answers valid
pass          grounding                       4 recommendation(s), each backed by at least one lookup_procedure call
pass          safety_warning_acknowledged     2 safety entry(ies), each acknowledged
inconclusive  provider_stability              no model turn occurred in this run

exit: True   model: unknown   provider: unknown
log: 30 record(s), no losses
```

## 2. Tests

```bash
python -m pytest tests/                # 30 tests, ~0.2s
```

The 30 tests cover the activity-log reader, each of the four
checks for pass/fail/inconclusive, the runner's verdict shape, and
**the cross-repo agreement test** that proves this repo's
verdict matches repair-agent's verdict on the same log.

## 3. Architecture

```
.activity.log ──► read_log_with_integrity ──► four deterministic checks ──► verdict.json
                                                  │
                                                  ├── tree_walk_validity
                                                  ├── grounding
                                                  ├── safety_warning_acknowledged
                                                  └── provider_stability
```

| Module | Lines | What it does |
|---|---|---|
| `activity.py` | 91 | Standalone repair-agent activity-log reader, line-for-line with repair-agent's |
| `checks.py` | 248 | Four deterministic checks, no LLM-as-judge |
| `runner.py` | 117 | Build a verdict, write it |
| `__main__.py` | 41 | CLI entry |

The four checks are the same checks repair-agent runs internally
— this repo re-implements them rather than importing, so the
"witness" property holds. The activity reader is the same
pattern: identical behaviour, no shared code.

## 4. Why this is good FDE signal

An LLM-as-judge eval is the standard shape of a real eval harness.
Re-implementing four deterministic checks in a second repo, with
a test that proves the two implementations agree, demonstrates
two things at once:

1. **You can write the check.** The four checks here are
   ~30-60 lines each, and they encode a specific claim about the
   agent's behaviour. Writing them from scratch is a different
   skill from calling an LLM to do it.
2. **You take the methodology seriously.** Cross-repo agreement
   is a real engineering pattern — it's how you avoid a "verdict
   that confirms itself" failure mode. The check in
   `test_agreement` is the test that fails when this repo
   silently drifts from repair-agent.

## 5. Scope contract

**DONE** = `python -m eval_harness --log <path>` runs the four
checks, prints the verdict, writes `verdict.json`. The verdict
agrees with repair-agent's verdict on the same input.

**NOT doing**:
- Importing from repair-agent (the re-implementation is the point)
- An LLM-as-judge layer (deterministic only)
- A web UI / dashboard
- A multi-run roll-up
- A general-purpose eval framework
- A `provider_switch` tool that actually changes providers
  (this repo's check reports when one is used)

## 6. Limitations, stated plainly

- **The `tree_walk_validity` check is coarser than repair-agent's.**
  This repo doesn't know each node's `expected_keys`; it accepts
  any non-empty answer for a known node id, plus rejects unknown
  node ids. That's enough to catch typos; it's not enough to
  catch "the model picked `idle_and_load` when the only valid
  answer was `under_load_only`." A future version can lift the
  fault-tree data into this repo for a stricter check.
- **The fault tree is duplicated implicitly.** A node id that's
  renamed in repair-agent's `fault_tree.py` will appear "unknown"
  here until both are updated. The `test_agreement` test catches
  the *verdict* drift, not the *data* drift.
- **`provider_stability` is inconclusive when no model turn
  occurred** — same as repair-agent. A scripted run that bypasses
  the model loop has nothing to label; the check refuses to pass
  on absence.
- **No CI hook.** Drift is caught by the agreement test, but
  only when both repos are checked out together. A CI job that
  runs repair-agent's examples, then eval-harness, and diffs
  the verdicts is the natural next step (and lives in repair-
  agent's CI, not here).

## License

MIT. See `LICENSE`.

## Source

Retargeted from an earlier `llm-eval-harness/` (now preserved in
`old/`), and adapted to score
[`repair-agent`](https://github.com/bsci83/repair-agent)'s
activity log. Same author, same eval pattern, different scope.
# eval-harness — spec

**Repo:** `eval-harness/`
**Started:** 2026-10-05
**Status:** Pre-build. This document is the contract. Code follows.

## What this is

A standalone eval harness for the **repair-agent** activity log. Reads
the JSONL stream a `repair-agent run` produces, scores it with the
four deterministic checks, and writes a verdict. The four checks are
**re-implemented in this repo** (not imported) so a hiring manager
sees the pattern from scratch, and so the repo stands alone.

The original `llm-eval-harness/` lived in the same folder for a few
months before being retargeted. The old files are preserved in
`old/`.

## Porting decisions (from `repair-agent`)

**Re-implemented, not imported**:
- The four checks: `tree_walk_validity`, `grounding`,
  `safety_warning_acknowledged`, `provider_stability`. The re-
  implementation tracks the repair-agent version line-for-line and
  should always agree on pass/fail/inconclusive verdicts. A
  divergence is a real bug, not a tolerated difference.
- The activity-log reader (`read_log_with_integrity`) is re-
  implemented in this repo. Same attribution-last rule, same sidecar
  on write failure, same integrity reporting.

**Skipped, not ported**:
- The full agent loop, registry, guard, types, approval. This repo
  reads the log; it does not run the agent.
- The fault tree. eval-harness reads the answer events; it does not
  need to walk the tree.

## Cases

A `cases.jsonl` file. Each line is one scripted diagnosis: the
operator-answer mapping the agent walks. eval-harness is run by
calling the agent's `run` subcommand for each case (so the activity
log accumulates the runs) and then calling `eval-harness eval` once.

## Eval pattern (deterministic only)

Same four checks as repair-agent. Same `pass | fail | inconclusive`
verdicts. Same integrity reporting. A divergence between
repair-agent's `verdict.json` and eval-harness's `verdict.json` for
the same input is the bug we're watching for.

## Scope contract

**DONE** = `python eval.py` reads the activity log, runs the four
checks, prints a verdict, and writes a verdict.json. The verdict
matches repair-agent's verdict for the same log.

**NOT doing**:
- Importing from repair-agent (the re-implementation is the point)
- An LLM-as-judge layer (deterministic only)
- A web UI / dashboard
- A multi-run roll-up
- A general-purpose eval framework (this is a domain-specific
  harness for repair-agent's log shape)

## Commit trail

Same discipline as the other two repos. Spec → scaffolding →
checks → runner → cases → README → run + verdict. ~10-15 commits.

## What's NOT in this batch

- Live re-evaluation as repair-agent evolves (would need a CI hook)
- A "diff two verdicts" tool (useful, but v1.1)
- Cross-repo version pinning
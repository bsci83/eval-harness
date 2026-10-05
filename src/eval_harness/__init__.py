"""eval-harness — standalone eval harness for the repair-agent
activity log.

Reads the JSONL stream a `repair-agent run` produces and scores it
with four deterministic checks. Re-implements the checks from
scratch (not imported) so a reader sees the pattern without
climbing a dependency graph.

    python -m eval_harness                  # score .activity.log -> verdict.json
"""

__version__ = "0.1.0"
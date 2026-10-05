"""CLI entry for eval-harness.

    python -m eval_harness                  # score .activity.log -> verdict.json

Reads the activity log produced by `python -m repair_diag run ...`
calls, scores it with the four deterministic checks, and writes a
verdict JSON. The verdict shape matches repair-agent's verdict so
the two can be diffed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import activity as activity_mod
from .runner import default_out_path, run_evals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval-harness")
    parser.add_argument("--log", type=Path, default=None,
                        help="path to the activity log (default: .activity.log)")
    parser.add_argument("--out", type=Path, default=None,
                        help="path to write the verdict (default: verdict.json)")
    parsed = parser.parse_args(argv)

    out_path = parsed.out or default_out_path()
    records, integrity = activity_mod.read_log_with_integrity(parsed.log)
    verdict = run_evals(log_path=parsed.log, out_path=out_path)

    for ck in verdict["checks"]:
        print(f"  {ck['verdict']:12s}  {ck['id']:30s}  {ck['evidence']}")
    print(f"\nexit: {verdict['exit']}   model: {verdict['model']}   "
          f"provider: {verdict['provider']}")
    print(f"log: {integrity.describe()}")
    return 0 if verdict["exit"] else 2


if __name__ == "__main__":
    sys.exit(main())
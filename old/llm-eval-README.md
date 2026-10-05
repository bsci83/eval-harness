# Tiny LLM Eval Harness

Runs a prompt over a set of test cases, grades each answer with an **LLM-as-judge**
(a model checks the candidate's answer against a reference), and prints a pass-rate.
~60 lines of Python. Demonstrates evals — the skill FDE teams increasingly screen for.

## Run it

```powershell
pip install anthropic
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # your Anthropic API key
python eval.py
```

Output:

```
[1/5] PASS  'What is the capital of Australia?'
[2/5] PASS  'A shirt costs $40 after a 20% discount. What was t'
...
Score: 5/5 passed  (100%)  [candidate=claude-opus-5]
```

## How it works
- `cases.json` — 5 cases, each `{question, reference}`.
- `ask_candidate()` — the model under test answers the question.
- `judge()` — a second model grades the answer against the reference (PASS/FAIL + reason).
- `main()` — loops the cases, tallies, prints the score.

Two knobs only, at the top of `eval.py`: `CANDIDATE_MODEL` (what you're testing) and
`JUDGE_MODEL` (the grader — switch to `claude-haiku-4-5` to cut cost).

## 🔒 Scope contract — DON'T let this balloon
**DONE** = `python eval.py` runs the 5 cases, judge grades each, score prints. Ship it.

**NOT doing** (these are the traps — adding any one turns a weekend project into a platform):
- ❌ web UI / dashboard
- ❌ database
- ❌ web framework (FastAPI/Flask)
- ❌ CLI argument parsing
- ❌ a second grader or grading "framework"
- ❌ async / parallelism
- ❌ retry / backoff / rate-limit handling
- ❌ config files
- ❌ "make it reusable as a library"

## If you want to extend it (the small way)
The only safe expansion is **more cases**: add entries to `cases.json`. That grows
coverage without growing complexity. Everything else on the NOT-doing list is a
separate project for another day.

## Why this is good FDE signal
LLM-as-judge + a dataset + a pass-rate is the standard shape of a real eval harness.
It shows you can (a) write Python, (b) call the Anthropic SDK, and (c) reason about
*measuring* LLM output quality — not just producing it. Name it that way on your
résumé: "evals / LLM-as-judge."

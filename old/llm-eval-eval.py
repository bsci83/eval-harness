"""Tiny LLM eval harness — run a prompt over test cases, grade each with an
LLM-as-judge, print a pass-rate.

    pip install anthropic
    PowerShell:  $env:ANTHROPIC_API_KEY = "sk-ant-..."
    python eval.py

Scope is fixed on purpose (see README). The only knobs are the two model
constants below.
"""
import json
import os
from anthropic import Anthropic

# --- the only config ---
CANDIDATE_MODEL = "claude-opus-5"   # the model being evaluated
JUDGE_MODEL = "claude-opus-5"       # grades the candidate; switch to "claude-haiku-4-5" to cut cost
SYSTEM = "You are a helpful assistant. Answer the question concisely and correctly."

client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment


def ask_candidate(question: str) -> str:
    """Get the model-under-test's answer to one question."""
    msg = client.messages.create(
        model=CANDIDATE_MODEL,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": question}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


JUDGE_PROMPT = """You are grading an AI answer against a reference answer.

Question: {q}
Reference answer: {ref}
AI answer: {ans}

Is the AI answer correct and consistent with the reference? Minor wording
differences are fine; the facts and final result must match.

Respond with EXACTLY two lines and nothing else:
VERDICT: PASS or FAIL
REASON: <one short sentence>"""


def judge(question: str, reference: str, answer: str) -> tuple[bool, str]:
    """LLM-as-judge: return (passed, reason)."""
    msg = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(q=question, ref=reference, ans=answer)}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    passed = "VERDICT: PASS" in text.upper()
    reason = next(
        (line.split(":", 1)[1].strip() for line in text.splitlines() if line.upper().startswith("REASON")),
        "",
    )
    return passed, reason


def main() -> None:
    path = os.path.join(os.path.dirname(__file__), "cases.json")
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)

    passes = 0
    for i, case in enumerate(cases, 1):
        answer = ask_candidate(case["question"])
        ok, reason = judge(case["question"], case["reference"], answer)
        passes += ok
        print(f"[{i}/{len(cases)}] {'PASS' if ok else 'FAIL'}  {case['question'][:50]!r}")
        if not ok:
            print(f"          reason: {reason}")
            print(f"          answer: {answer[:120]}")

    rate = 100 * passes / len(cases)
    print(f"\nScore: {passes}/{len(cases)} passed  ({rate:.0f}%)  [candidate={CANDIDATE_MODEL}]")


if __name__ == "__main__":
    main()

"""Run the rule checks over the eval set and write a JSON report with gate results."""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from dishaa.evals import checks
from dishaa.evals.cases import Case, load_cases

AskFn = Callable[[Case], checks.Answer]

# Gates from the Eval Plan. "min" is a pass-rate floor, "max_failures" a failure ceiling.
GATES = {
    "retrieval_hit": {"min": 0.90},
    "refusal_accuracy": {"min": 0.95},
    "citation_validity": {"min": 0.95},
    "exception_traps": {"min": 1.00},
    "contamination": {"max_failures": 0},
}


def checks_for(case: Case) -> list:
    """Which rule checks apply to a case."""
    if case.expected_outcome == "answered":
        applicable = [
            checks.retrieval_hit,
            checks.refusal_accuracy,
            checks.contamination,
            checks.citation_validity,
            checks.required_facts,
        ]
        if case.must_include_exceptions or case.forbidden_claims:
            applicable.append(checks.exception_traps)
        return applicable
    return [checks.refusal_accuracy, checks.contamination]


def refuse_everything(case: Case) -> checks.Answer:
    """Baseline system: refuses every question. Useful to prove the harness can fail."""
    return checks.Answer(outcome="refused", text="Outside the pathways Dishaa supports.")


def evaluate(cases: list[Case], ask: AskFn) -> dict:
    results, excluded = [], []
    tally: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        reason = case.exclusion_reason()
        if reason:
            excluded.append({"id": case.id, "reason": reason})
            continue
        answer = ask(case)
        outcomes = [fn(case, answer) for fn in checks_for(case)]
        for o in outcomes:
            tally[o.check].append(o.passed)
        results.append(
            {
                "id": case.id,
                "category": case.category,
                "checks": [
                    {"check": o.check, "passed": o.passed, "detail": o.detail} for o in outcomes
                ],
            }
        )
    return {"results": results, "excluded": excluded, "gates": gate_report(tally)}


def gate_report(tally: dict[str, list[bool]]) -> dict:
    report = {}
    for name, rule in GATES.items():
        passed_flags = tally.get(name, [])
        n = len(passed_flags)
        failures = n - sum(passed_flags)
        if n == 0:
            report[name] = {"cases": 0, "status": "no_cases"}
            continue
        rate = (n - failures) / n
        ok = rate >= rule["min"] if "min" in rule else failures <= rule["max_failures"]
        report[name] = {
            "cases": n,
            "failures": failures,
            "rate": round(rate, 4),
            "status": "pass" if ok else "fail",
        }
    return report


def overall(report: dict) -> str:
    statuses = {g["status"] for g in report["gates"].values()}
    if "fail" in statuses:
        return "fail"
    if "no_cases" in statuses:
        return "incomplete"
    return "pass"


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DISHAA rule-check evals.")
    parser.add_argument("--cases", type=Path, default=Path("evals/seed_questions.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("evals/reports"))
    parser.add_argument("--system", choices=["refuse_everything"], default="refuse_everything")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    report = evaluate(cases, refuse_everything)
    report["verdict"] = overall(report)
    report["meta"] = {
        "system": args.system,
        "commit": _git_commit(),
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "total_cases": len(cases),
        "counted_cases": len(report["results"]),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{report['meta']['commit']}-{args.system}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        f"{report['meta']['counted_cases']} of {len(cases)} cases count toward gates; verdict: {report['verdict']}"
    )
    for name, g in report["gates"].items():
        print(f"  {name:18} {g['status']:10} {g.get('cases', 0)} cases")
    print(f"report: {path}")
    sys.exit(0 if report["verdict"] == "pass" else 1)

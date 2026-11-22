"""Rule checks (ADR-027, layer 1). Each is deterministic and needs no model.

A system under test returns an Answer; each check turns a Case plus an Answer into a
CheckResult. Citation validity here only checks that a cited passage really exists in a chunk
the system retrieved; whether the passage supports the claim is the judge's job (layer 2).
"""

import re
from dataclasses import dataclass, field

from dishaa.evals.cases import Case


@dataclass
class Citation:
    source_id: str
    passage: str  # the exact text the answer points to


@dataclass
class RetrievedChunk:
    chunk_id: str
    source_id: str
    country: str
    text: str


@dataclass
class Answer:
    outcome: str  # "answered", "refused" or "clarify"
    text: str = ""
    citations: list[Citation] = field(default_factory=list)
    retrieved: list[RetrievedChunk] = field(default_factory=list)
    refusal_reason: str | None = None


@dataclass
class CheckResult:
    check: str
    passed: bool
    detail: str = ""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _contains(haystack: str, needle) -> bool:
    """A needle is a string, or a list of alternative strings (any one is enough)."""
    options = [needle] if isinstance(needle, str) else list(needle)
    return any(_norm(o) in haystack for o in options)


def retrieval_hit(case: Case, ans: Answer) -> CheckResult:
    got = {c.source_id for c in ans.retrieved}
    hit = bool(set(case.source_ids) & got)
    return CheckResult(
        "retrieval_hit", hit, f"expected one of {case.source_ids}, got {sorted(got)}"
    )


def refusal_accuracy(case: Case, ans: Answer) -> CheckResult:
    ok = ans.outcome == case.expected_outcome
    return CheckResult(
        "refusal_accuracy", ok, f"expected {case.expected_outcome}, got {ans.outcome}"
    )


def contamination(case: Case, ans: Answer) -> CheckResult:
    """No retrieved chunk or citation may come from a country other than the destination."""
    allowed = {(case.destination or "").casefold()} | {a.casefold() for a in case.allowed_countries}
    if not case.destination:
        return CheckResult("contamination", True, "no destination in intake")
    wrong = sorted({c.country for c in ans.retrieved if c.country.casefold() not in allowed})
    return CheckResult(
        "contamination", not wrong, f"other countries retrieved: {wrong}" if wrong else ""
    )


def citation_validity(case: Case, ans: Answer) -> CheckResult:
    if ans.outcome == "answered" and not ans.citations:
        return CheckResult("citation_validity", False, "answer has no citations")
    retrieved_text = {c.source_id: _norm(c.text) for c in ans.retrieved}
    bad = [
        f"{c.source_id}: passage not found"
        for c in ans.citations
        if _norm(c.passage) not in retrieved_text.get(c.source_id, "")
    ]
    return CheckResult("citation_validity", not bad, "; ".join(bad))


def exception_traps(case: Case, ans: Answer) -> CheckResult:
    text = _norm(ans.text)
    missing = [str(e) for e in case.must_include_exceptions if not _contains(text, e)]
    stated = [str(f) for f in case.forbidden_claims if _contains(text, f)]
    problems = [f"missing exception: {m}" for m in missing] + [
        f"forbidden claim: {s}" for s in stated
    ]
    return CheckResult("exception_traps", not problems, "; ".join(problems))


def required_facts(case: Case, ans: Answer) -> CheckResult:
    text = _norm(ans.text)
    missing = [str(f) for f in case.expected_facts if not _contains(text, f)]
    return CheckResult("required_facts", not missing, f"missing: {missing}" if missing else "")


def refusal_notice(case: Case, ans: Answer) -> CheckResult:
    """A refusal states that Dishaa only covers student immigration pathways (founder wording)."""
    if not case.required_notice:
        return CheckResult("refusal_notice", True, "no notice required")
    ok = _norm(case.required_notice) in _norm(ans.text)
    return CheckResult("refusal_notice", ok, f"missing: {case.required_notice}" if not ok else "")

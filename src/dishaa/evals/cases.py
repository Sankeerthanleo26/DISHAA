"""Eval cases, loaded from JSON Lines, and the rule for which cases may count toward a gate."""

import json
from dataclasses import dataclass, field
from pathlib import Path

# What the system must do, mapped to the outcome it reports.
BEHAVIOR_TO_OUTCOME = {
    "answer_with_citations": "answered",
    "answer_destination_only": "answered",
    "explain_not_applicable": "answered",
    "ask_intake": "clarify",
    "refuse_out_of_pathway": "refused",
    "decline_out_of_scope": "refused",
    "decline_case_decision": "refused",
    "decline_unsupported_destination": "refused",
}

APPROVED_STATUS = "approved"  # the founder has reviewed the case and its source passages


@dataclass
class Case:
    id: str
    question: str
    intake: dict
    category: str
    expected_behavior: str
    expected_facts: list = field(default_factory=list)
    must_include_exceptions: list = field(default_factory=list)
    forbidden_claims: list = field(default_factory=list)
    required_notice: str | None = None  # wording a refusal must contain
    allowed_countries: list = field(default_factory=list)  # explain-not-applicable cases
    source_ids: list = field(default_factory=list)
    status: str = ""

    @property
    def expected_outcome(self) -> str | None:
        return BEHAVIOR_TO_OUTCOME.get(self.expected_behavior)

    @property
    def destination(self) -> str | None:
        return self.intake.get("destination")

    def exclusion_reason(self) -> str | None:
        """Why this case cannot count toward a gate yet, or None if it can (R18)."""
        if self.status != APPROVED_STATUS:
            return f"status is '{self.status}', not '{APPROVED_STATUS}'"
        if self.expected_outcome is None:
            return f"expected_behavior '{self.expected_behavior}' is not decided"
        if self.expected_outcome == "answered" and not (self.source_ids and self.expected_facts):
            return "answer case without expected facts and official source ids"
        return None


def load_cases(path: Path) -> list[Case]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cases.append(
            Case(
                id=row["id"],
                question=row["question"],
                intake=row.get("intake") or {},
                category=row.get("category", ""),
                expected_behavior=row.get("expected_behavior", ""),
                expected_facts=row.get("expected_facts") or [],
                must_include_exceptions=row.get("must_include_exceptions") or [],
                forbidden_claims=row.get("forbidden_claims") or [],
                required_notice=row.get("required_notice"),
                allowed_countries=row.get("allowed_countries") or [],
                source_ids=row.get("source_ids") or [],
                status=row.get("status", ""),
            )
        )
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case ids in eval file")
    return cases

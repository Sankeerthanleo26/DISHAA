from pathlib import Path

from dishaa.evals import checks, runner
from dishaa.evals.cases import Case, load_cases

SEED = Path(__file__).parent.parent / "evals" / "seed_questions.jsonl"


def make_case(**kw) -> Case:
    base = {
        "id": "T1",
        "question": "q",
        "intake": {"destination": "US"},
        "category": "standard",
        "expected_behavior": "answer_with_citations",
        "expected_facts": ["$100"],
        "source_ids": ["us-fees"],
        "status": "approved",
    }
    base.update(kw)
    return Case(**base)


def chunk(source="us-fees", country="US", text="The fee is $100 for students."):
    return checks.RetrievedChunk("c1", source, country, text)


def test_seed_file_loads_and_only_approved_cases_count():
    cases = load_cases(SEED)
    assert len(cases) == 32
    counted = {c.id for c in cases if not c.exclusion_reason()}
    assert counted == {"R01", "R02", "R03", "R04", "R05"}  # only founder-approved cases (R18)


def test_answer_case_without_sources_is_excluded():
    assert "without expected facts" in make_case(source_ids=[]).exclusion_reason()
    assert make_case().exclusion_reason() is None


def test_undecided_behavior_is_excluded():
    assert (
        "not decided" in make_case(expected_behavior="tbd_after_scope_decision").exclusion_reason()
    )


def test_retrieval_hit():
    ans = checks.Answer("answered", retrieved=[chunk()])
    assert checks.retrieval_hit(make_case(), ans).passed
    assert not checks.retrieval_hit(make_case(source_ids=["other"]), ans).passed


def test_contamination_flags_other_country():
    ans = checks.Answer("answered", retrieved=[chunk(), chunk(source="ie", country="IE")])
    assert not checks.contamination(make_case(), ans).passed


def test_citation_must_exist_in_retrieved_text():
    good = checks.Answer(
        "answered",
        retrieved=[chunk()],
        citations=[checks.Citation("us-fees", "fee is  $100")],
    )
    bad = checks.Answer(
        "answered",
        retrieved=[chunk()],
        citations=[checks.Citation("us-fees", "the fee is $500")],
    )
    assert checks.citation_validity(make_case(), good).passed
    assert not checks.citation_validity(make_case(), bad).passed


def test_answer_without_citations_fails():
    assert not checks.citation_validity(make_case(), checks.Answer("answered", text="x")).passed


def test_exception_trap_needs_exception_and_rejects_general_rule_alone():
    case = make_case(
        must_include_exceptions=[["international students", "non-resident"]],
        forbidden_claims=["no fee applies"],
    )
    ok = checks.Answer("answered", text="Fee is $100, except international students pay more.")
    missing = checks.Answer("answered", text="Fee is $100.")
    forbidden = checks.Answer("answered", text="International students: No fee applies.")
    assert checks.exception_traps(case, ok).passed
    assert not checks.exception_traps(case, missing).passed
    assert not checks.exception_traps(case, forbidden).passed


def test_refusal_accuracy():
    case = make_case(expected_behavior="refuse_out_of_pathway", source_ids=[], expected_facts=[])
    assert checks.refusal_accuracy(case, checks.Answer("refused")).passed
    assert not checks.refusal_accuracy(case, checks.Answer("answered")).passed


def test_baseline_refuser_fails_the_answer_cases_and_report_has_gates():
    cases = [
        make_case(id="A"),
        make_case(
            id="R", expected_behavior="refuse_out_of_pathway", source_ids=[], expected_facts=[]
        ),
        make_case(id="X", status="draft_needs_founder_review"),
    ]
    report = runner.evaluate(cases, runner.refuse_everything)
    assert [r["id"] for r in report["results"]] == ["A", "R"]
    assert report["excluded"][0]["id"] == "X"
    assert report["gates"]["retrieval_hit"]["status"] == "fail"
    assert report["gates"]["refusal_accuracy"]["failures"] == 1  # the answer case A
    assert runner.overall(report) == "fail"


def test_empty_gates_report_incomplete_not_pass():
    report = runner.evaluate([], runner.refuse_everything)
    assert runner.overall(report) == "incomplete"


def test_refusal_notice_and_forbidden_claim_on_refusals():
    case = make_case(
        expected_behavior="refuse_out_of_pathway",
        source_ids=[],
        expected_facts=[],
        required_notice="student immigration pathways",
        forbidden_claims=["does not exist"],
    )
    good = checks.Answer(
        "refused", text="I can only help with student immigration pathways, not this route."
    )
    bad = checks.Answer("refused", text="That visa does not exist.")
    assert checks.refusal_notice(case, good).passed
    assert not checks.refusal_notice(case, bad).passed
    assert checks.exception_traps(case, good).passed
    assert not checks.exception_traps(case, bad).passed
    assert [f.__name__ for f in runner.checks_for(case)] == [
        "refusal_accuracy",
        "contamination",
        "refusal_notice",
        "exception_traps",
    ]

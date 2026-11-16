# DISHAA: Evaluation Plan

**Status:** Draft v1 · **Owner:** Sankeerthan Sornapoodi · **Date:** 2026-11-16
**Related:** [PRD](PRD.md) (FR-34 to FR-36) · [Risk Register](RISK_REGISTER.md) · seed data in [`evals/seed_questions.jsonl`](../evals/seed_questions.jsonl)

## 1. Purpose

The eval set is our definition of "working". Every change to retrieval, chunking, prompts, models, sources or pathway graphs is judged against it. It is written before the design doc so that the design is accountable to it.

## 2. Rules for building the set

1. **Expected facts come from official sources, never from a model's memory.** Each case records the source document and passage. If a draft answer cannot be traced to a source, the case stays in `needs_expected_facts`. (A set written from a model's memory would test the model against itself.)
2. **A case is a question plus an intake context.** The same question can have different correct answers for different origin, destination, degree or university.
3. **Every case has a category and an expected behaviour,** not only expected text: answer with citations, ask the intake questions, refuse, or explain "not applicable".
4. **Cases are versioned.** Changes go through Git. A source change that alters an expected fact updates the case in the same commit.
5. **Diversity target:** the set must not be written from one person's journey. At least a third of the cases use other origins and degree levels, and at least a third are Ireland.

## 3. What the first 15 questions told us

The founder's 15 questions come from personal experience. They are the most realistic cases we have, and they exposed a scope gap.

| Type | Count | Questions |
|---|---|---|
| Immigration rule (inside the pathway graph) | 6 | F04, F05, F06, F09, F10, F13 |
| University-specific (set by each school) | 5 | F01, F02, F07, F08, F11 |
| State or local | 1 | F03 |
| Daily-life logistics | 3 | F12, F14, F15 |

**Only 6 of 15 are answerable from the official immigration sources and pathway graph we scoped in the PRD.** The other 9 depend on the university, the state, or everyday life. This matters because:

- **Admissions, tuition, payment plans and insurance (F01, F02, F07, F08) vary by university.** The founder's tuition story (F07) is exactly this: the rule and its international-student exception live in a university document, not in any immigration source.
- **Living costs, driver's licences and taxes (F03, F14, F15) vary by state or agency.** Driver's licences alone mean one source set per state.
- **Mobile providers (F12) are commercial.** There is no official source, which breaks the "official sources only" principle.

Scope labels in the seed file: 6 `in_scope`, 7 `needs_decision`, 1 `lean_out` (F11), 1 `out_of_scope` (F12).

### Options for the decision

| Option | What it means | Cost |
|---|---|---|
| A. Strict | Immigration pathway only. The other 9 are declined with a pointer to official channels. | Simple and honest, but 9 of the founder's 15 real questions get refusals |
| B. University layer (pilot) | Add a fourth intake question (university). Onboard one or two universities as a source tier. Covers F01, F02, F07, F08 and on-campus F11. Daily-life topics stay out. | Corpus and review work grow; the exception-trap problem is tested on real material |
| C. Everything | Also cover state, tax and licence topics. | Dozens of source sets, and most of v0.1 effort goes to sources instead of the freshness problem |

**Recommendation: B.** It keeps the freshness problem central, brings the most important failure mode (lost exceptions) into scope, and does not turn v0.1 into a life-admin assistant. F03, F12, F14 and F15 move to a v0.2 backlog. This is a decision for the founder; the PRD will be updated once it is made.

## 4. Coverage gaps in the seed set

| Category | Founder's 15 | Drafts | Target for 50 |
|---|---|---|---|
| Standard factual | 13 | 0 | 20 |
| Exception traps | 1 (F07) | 0 | 8 |
| Out-of-pathway refusals | 0 | 8 | 8 |
| Unclear-path intake | 0 | 5 | 5 |
| Cross-country contamination | 0 | 4 | 4 |
| Freshness regressions | 1 (F05, partial) | 0 | 5 |

Other gaps:
- **No Ireland cases.** All 15 are USA.
- **One origin, one degree.** Every question assumes a master's in computer science.
- **Only one exception trap.** The best test of our principle needs many. They are found by reading real source documents for conditions, footnotes and carve-outs, then writing the question that hits each one.
- **Freshness cases cannot be written yet.** They need the source registry and a working re-ingest path; they are simulated source changes.

The 17 drafts (8 refusals, 5 unclear-path, 4 contamination) are marked `draft_needs_founder_review`. They do not depend on facts, only on scope rules.

## 5. Case format

JSON Lines, one case per line:

| Field | Meaning |
|---|---|
| `id` | `F` founder, `R` refusal, `U` unclear intake, `C` contamination, later `E` exception, `S` standard, `X` freshness |
| `question` | What the user types |
| `intake` | Origin, destination, degree, university, as already known |
| `topic_type` | immigration, university, state_local, life_logistics |
| `category` | standard, exception_trap, refusal, unclear_intake, contamination, freshness |
| `scope_label` | in_scope, needs_decision, lean_out, out_of_scope, out_of_pathway, unclear |
| `expected_behavior` | answer_with_citations, ask_intake, refuse_out_of_pathway, decline_case_decision, answer_destination_only, explain_not_applicable |
| `expected_facts` | Facts the answer must contain, each traced to a source passage |
| `must_include_exceptions` | Exceptions that must be stated for this user |
| `source_ids` | Source registry IDs the answer should cite |
| `status` | needs_expected_facts, draft_needs_founder_review, ready |

## 6. Metrics and release gates

Metrics are defined in the PRD (section 5). Initial gates for a release candidate, to be revised after the first baseline run:

- Retrieval hit rate 90% or higher
- Answer correctness 85% or higher
- Refusal accuracy 95% or higher (including no false refusals on in-scope questions)
- Exception-trap pass rate 100% on the core set
- Zero cross-country contamination failures
- Citation validity 95% or higher

## 7. How cases are graded

- **Retrieval:** is the expected chunk in the top-k? (automatic, from `source_ids`)
- **Behaviour:** did the system answer, ask, or refuse as expected? (automatic classification)
- **Facts and exceptions:** are expected facts present and no contradiction? Start with a rubric graded by an LLM judge, spot-checked by hand on a sample every run. The judge model should differ from the generator (open question in the PRD).
- **Citations:** does each cited passage support the claim? Sampled hand-check each release.

## 8. Next steps

1. Founder decides the scope option (section 3).
2. Founder reviews the 17 drafts and edits or rejects them.
3. Source registry is built (needed for `source_ids` and expected facts).
4. Expected facts are filled in from official sources, three or four cases at a time.
5. Ireland cases, other origins and more exception traps are added until the 50-case target is met.

# DISHAA: Risk Register

**Status:** Draft v1 · **Owner:** Sankeerthan Sornapoodi · **Date:** 2026-11-16
**Review cadence:** at the end of each milestone, and whenever an incident happens.
**Scale:** Likelihood (L) and Impact (I) are High / Medium / Low. Priority is the combination; work on High-High risks first.

## Product and content risks

| ID | Risk | L | I | Mitigation | How we would notice |
|---|---|---|---|---|---|
| R1 | A stale rule is served as current | H | H | Freshness pipeline, review queue, "last verified" dates in answers, stale-source alerts (PRD FR-27 to FR-33) | Stale-source count; time-to-reflect-change; regression evals after each update |
| R2 | A condition or exception is dropped, so a general rule is wrongly applied (the "asterisk problem") | M | H | Chunker keeps footnotes with their rules (FR-13); answer must state relevant exceptions (FR-20); exception-trap evals with a 100% gate | Exception-trap pass rate; manual reading of real pages after ingestion |
| R3 | The model states things the sources do not say | M | H | Answer only from retrieved context; citation required; "not sure" is a valid answer; citation-validity checks | Citation validity metric; sampled hand review |
| R4 | The user asks things outside the immigration pathway; the founder's own 15 questions show 9 of 15 are about universities, states or daily life | H | M | Scope decision recorded in the Eval Plan (university layer pilot or strict); allowlist; polite refusals with official pointers | Share of refused questions in logs; refusal-reason breakdown |
| R5 | Rules differ by university, so a generic answer is wrong for this student | H | H | University as an intake item and source tier; decline university-specific questions for universities we do not cover | Eval cases by university; refusal accuracy for uncovered universities |
| R6 | A pathway graph is wrong or outdated | M | H | Build graphs from official sources only; same review and versioning as sources; each node links to its source | Graph-vs-source review at each release; user-reported errors |
| R7 | Cross-country contamination (for example an Irish rule cited for a US question) | M | H | Country, pathway and step filters at retrieval; contamination evals with a zero-failure gate | Contamination eval failures; citations whose country differs from intake |
| R8 | Wrongly implying a route does not exist when we just do not support it | M | M | Refusal wording says "outside the pathways Dishaa supports" (FR-7) | Refusal-wording tests |
| R9 | Seen as legal advice, or a user relies on an answer for a case decision | M | H | "Not legal advice" notice; no eligibility verdicts; pointers to official channels and qualified professionals | Case-decision refusal evals; user feedback |

## Data and engineering risks

| ID | Risk | L | I | Mitigation | How we would notice |
|---|---|---|---|---|---|
| R10 | The HTML extractor fails on real pages (it has only been tested on a synthetic page; pages built by JavaScript may be empty) | H | M | Inspect the first real run by eye; pipeline already warns on short pages; fall back to a headless browser only for pages that need it (ADR-010) | Pipeline warnings; empty-chunk counts |
| R11 | Sources block us or their terms of use forbid collection | M | M | robots.txt, polite rate, honest User-Agent (ADR-008); record terms in the source registry; prefer official downloads and APIs | Fetch status counts in the manifest |
| R12 | A parse error or page redesign makes the freshness job report a false change, or miss a real one | M | H | Hash cleaned content, not raw HTML (ADR-011); human review queue; periodic full re-check | False-change rate; review queue size |
| R13 | A model or API version change alters behaviour | M | M | Pin model versions; run the full eval set on every model change | Eval trend |
| R14 | Prompt injection through user input or through retrieved page text | M | M | Treat retrieved text as data; fixed system instructions; output checks for citations; rate limits | Adversarial eval cases; log review |
| R15 | Cost overrun on the hosted LLM or AWS | M | M | Hard monthly cap and alerts; per-IP rate limit; caching; cost per query tracked | Budget alerts |

## People, process and evaluation risks

| ID | Risk | L | I | Mitigation | How we would notice |
|---|---|---|---|---|---|
| R16 | **The founder is the only reviewer** of source changes and pathway graphs, and review checks "matches the source", not "legally correct" | H | M | Tier sources so only core ones need approval; review checklist; alert when the queue grows; state clearly that review is not legal review | Review queue age |
| R17 | The eval set reflects one person's journey (one origin, one degree, one country) | H | M | Diversity target in the Eval Plan; Ireland and other-origin cases required before release | Coverage table in the Eval Plan |
| R18 | Expected answers are written from a model's memory, so evals test the model against itself | M | H | Rule: expected facts must cite an official source passage; cases without one stay unfinished | Cases with empty `source_ids` |
| R19 | Sensitive personal data (nationality, immigration situation) is stored or leaked through logs | M | H | Origin country used in-session only; logs exclude origin and free text that identifies a person; no accounts in v0.1 (FR-5, FR-25) | Log schema review; periodic log sampling |
| R20 | Scope creep from "any country, any user" into many half-covered countries | M | H | Staged rollout (ADR-015); a country is "supported" only with graph, sources and evals complete | Count of countries by completeness |

## Top five to work on first

1. **R5 and R4** (university and scope decision): this changes intake, sources and evals, so it comes first.
2. **R2** (lost exceptions): the founding failure mode; needs tests from the start.
3. **R1** (staleness): the core problem; the design doc must settle the update loop.
4. **R10** (extractor on real pages): a cheap check that blocks everything downstream.
5. **R18** (circular evals): a process rule we adopt now.

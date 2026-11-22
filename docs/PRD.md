# DISHAA: Product Requirements Document

**Status:** Draft v2 (supersedes v1, Ireland-only; see git history)
**Owner:** Sankeerthan Sornapoodi
**Release scope (v0.1):** Student pathways for **Ireland** and the **USA**, built on a country-agnostic architecture
**Related:** [Problem Brief](PROBLEM_BRIEF.md) · [Scope](SCOPE.md) · [Decisions](DECISIONS.md)

## 1. Purpose

Help anyone considering moving to another country understand one clear immigration pathway, using only current official sources, with citations. Decline everything outside the supported pathways.

## 2. Users and user stories

The user can be from any origin country and heading to any supported destination. For v0.1 the destinations are Ireland and the USA.

1. As a prospective student, I want to state where I'm from, where I'm going and what I plan to study, so that I only see the pathway that applies to me.
2. As a user who has not chosen a clear path, I want Dishaa to notice and show me the available pathways, so that I can choose before getting details.
3. As a student, I want to know the requirements at my current step (visa, funds, work rules, post-study options), so that I can prepare.
4. As a user, I want to ask about the next step on my pathway (for example, post-study work or sponsorship), so that I can plan ahead.
5. As any user, I want each answer to show its source and when it was last verified, so that I can check it myself.
6. As any user, I want exceptions and conditions that affect me (for example, rules that differ for international students) to be included, so that I'm not misled by a general rule.
7. As any user, I want Dishaa to admit when it doesn't know, so that I'm not misled.

## 3. Functional requirements

### 3.1 Intake and pathway selection (new)
- FR-1: Ask three intake questions before substantive answers: origin country, destination country, planned degree (level and field). Skip any already answered.
- FR-2: Map intake answers to a pathway in the destination's **pathway graph** (ordered steps, for example Student → F-1 → OPT → STEM OPT → H-1B → green card; or O-1). Pathway graphs are curated data files, one per country, reviewed against official sources.
- FR-3: If intake answers do not resolve to one pathway, explain that and list the available pathways for the user to choose. Never guess silently.
- FR-4: Retrieval uses the selected pathway and step as filters, alongside country and visa category.
- FR-5: Origin country is used only for the current conversation to select content (fees, exemptions). It is not stored with the user.

### 3.2 Scope guardrails (new)
- FR-6: Classify each question as in-pathway, out-of-pathway, or unclear.
- FR-7: Out-of-pathway questions (for example, marriage-based routes, asylum, or any pathway not in the graph) get a plain refusal: this is outside the pathways Dishaa supports. The refusal must not imply such routes don't exist.
- FR-8: In-pathway questions about any step, including employer-sponsored steps such as H-1B or O-1, are answered.
- FR-9: Questions seeking individual case decisions or legal strategy are declined with a pointer to official channels.
- FR-10: Unclear questions trigger one clarifying question, not an answer.

### 3.3 Data ingestion
- FR-11: Collect pages from the curated source list per country (official sources only) with URL and retrieval date.
- FR-12: Clean content and split along headings into chunks.
- FR-13: Chunking must keep conditions, footnotes and exceptions with the rule they modify (the "asterisk problem"). Footnote and exception text is attached to, or duplicated into, the chunks it affects.
- FR-14: Attach metadata to each chunk: country, pathway, step, visa category, source URL, section path, retrieval date, content hash, effective date when stated.

### 3.4 Retrieval and answer generation
- FR-15: Embed chunks and store them in the vector index.
- FR-16: Retrieve top-k chunks filtered by country, pathway and step. Rules from one country must never appear in another country's answer.
- FR-17: Generate answers using only retrieved context.
- FR-18: Every answer cites source pages and shows the "last verified" date of each.
- FR-19: If context is insufficient or conflicting, say so and link to the official source instead of choosing an answer.
- FR-20: When a retrieved rule has an exception relevant to the user's intake answers (for example, international students), the answer states it.
- FR-21: Display a "not legal advice" notice.
- FR-22: Configurable chunk size, overlap, top-k and optional reranking, so they can be compared in experiments.

### 3.5 API and interface
- FR-23: `POST /ask` accepts a message and conversation state and returns answer, citations, pathway, and a coverage indicator.
- FR-24: Simple web chat interface with intake, clickable citations and visible "last verified" dates.
- FR-25: Log each request (retrieved chunk IDs, latency, token usage, guardrail decision) and the **raw question text**. The origin country is not stored as a field and is not joined to a logged request. *Amended 2026-11-21 by the founder: raw text is logged, and the PII layer is deferred (see R19 and the release gate there). Previously: no personal data in logs.*
- FR-26: Per-IP rate limiting and a hard monthly cost cap.

### 3.6 Freshness (core requirement)
- FR-27: Scheduled job re-fetches sources and detects changes by cleaned-content hash (see ADR-011).
- FR-28: Each detected change creates a diff entry in a **review queue** with the affected pathways and steps.
- FR-29: Changes to core-tier sources require human approval before they are served as current. Until approved, answers relying on the changed page carry an "update pending review" warning. (Proposed; see open questions.)
- FR-30: Only changed documents are re-chunked and re-embedded. Superseded versions are kept, marked inactive.
- FR-31: Every approved change triggers the full eval set; a drop below threshold blocks release of the change.
- FR-32: Keep a change log: what changed, when, who approved.
- FR-33: Flag sources that have not been successfully re-verified within their expected window (stale-source alert).

### 3.7 Evaluation
- FR-34: Maintain a versioned eval set of 50+ questions per release, each with expected facts and source passages.
- FR-35: The set includes these categories: standard factual, **exception traps**, out-of-pathway refusals, unclear-path intake, cross-country contamination, and freshness regressions. At least 15 seed questions come from the founder's lived experience.
- FR-36: Report retrieval hit rate, answer correctness, refusal accuracy, citation validity and exception-trap pass rate for any configuration, and store results so configurations can be compared.

### 3.8 Operations
- FR-37: Dashboard (or equivalent) for latency, cost per query, error rate, eval trend and stale-source status.
- FR-38: Structured logs and basic alerting (budget, error spike, stale source).

## 4. Non-functional requirements

- **Accuracy (initial targets, to be revised after the baseline run):** at least 85% answer correctness, 90% retrieval hit rate, 95% refusal accuracy, and 100% pass on a defined core set of exception traps
- **Concurrency:** designed for multiple simultaneous users; load-test to a stated number before release
- **Latency:** median under 5 seconds, p95 under 12 seconds
- **Cost:** hard monthly budget with alerts; cost per query tracked
- **Security and privacy:** HTTPS, no secrets in the repo, no user accounts, no user nationality retained as a field. The raw question text is logged (FR-25, amended 2026-11-21), which can contain personal details, so the R19 release gate applies before any public launch.
- **Maintainability:** per-country source list and pathway graph; adding a country means config, graph and eval questions, not code changes

## 5. Metrics

| Metric | Definition |
|---|---|
| Retrieval hit rate | Share of eval questions where the correct chunk is in top-k |
| Answer correctness | Share of answers with the expected facts and no contradictions |
| Exception-trap pass rate | Share of exception-trap questions where the answer includes the relevant exception |
| Refusal accuracy | Share of out-of-pathway questions declined, and in-pathway questions not wrongly declined |
| Citation validity | Share of citations that support the claim |
| Time to reflect change | Time from a source changing to the approved update being live |
| Stale-source count | Sources past their expected re-verification window |
| Latency (p50, p95) and cost per query | End-to-end time; LLM plus infrastructure cost |

## 6. Release plan

v0.1 is done when the Ireland and USA student pathways work end to end with intake, guardrails, citations, freshness pipeline and eval report, deployed on AWS at a public HTTPS URL. See [Scope](SCOPE.md) for the full definition of done.

## 7. Risks (summary; full register to follow)

- Wrong or stale information (mitigation: official sources only, freshness pipeline, review queue, citations with dates)
- USA corpus size and rate of change straining the update process
- Hand-curated pathway graphs becoming outdated or wrong
- Liability perception around "immigration guidance" (not legal advice notice, narrow scope, no case decisions)
- Cost overrun on hosted LLM and AWS
- Scraping limits and terms of use (robots.txt, polite fetching, ADR-008)

## 8. Open questions

- Should core-source changes be blocked until reviewed, or served immediately with a warning? (FR-29 proposes the former for core-tier sources.)
- How is "origin country" used in retrieval: as a filter, or as extra context for the model?
- What intake depth is enough: is degree level and field needed for every pathway, or only some?
- Which embedding model (Bedrock or open source) gives the best accuracy per cost? (blocks the vector dimension in the schema)
- Should the evaluation judge be a different model from the generator?
- How are US sources that interleave statute, regulation and policy guidance tiered for trust?
- ~~Should a university layer be added?~~ **Decided 2026-11-21: yes, as a pilot (option B, ADR-020).** A fourth intake question (university) and a university source tier are added for one or two universities. Requirements FR-39 to FR-42 are still to be written into the next PRD revision. Still open: which university or universities.

# DISHAA: Scope

**Version:** v0.1 (supersedes the Ireland-only v1 scope; see git history)

## Vision vs. release scope

- **Vision:** anyone, from any country, considering moving to any popular destination (USA, Canada, UK, Australia, Germany, Ireland, Singapore and others) can get a clear, cited, current answer for their pathway.
- **v0.1 release:** two destinations done properly, on an architecture that does not care which country it serves.

## In scope for v0.1

**Destinations:** Ireland and the USA.
**Origin:** any country (used as an input, not a limit).
**Pathways (student-centred, validated against official sources before release):**
- **USA:** Student (F-1) → initial OPT → STEM OPT → employer-sponsored H-1B → green card; and the O-1 track
- **Ireland:** study permission (visa, Stamp 2, IRP registration) → Graduate pathway (Stamp 1G) → next work route (to be defined from official sources)

**Topics inside each pathway:** application steps and documents, proof of funds, work rules, status transitions, renewals and compliance, and how employer sponsorship works at the relevant steps.

**System components:**
- Pathway graph per country (curated data)
- Three-question intake and pathway selection
- Scope classifier and refusal policy
- Source registry and curated source lists (official sources only)
- Ingestion: fetch, clean, chunk (exceptions kept with their rules), embed, index
- Retrieval filtered by country, pathway and step
- Grounded generation through a hosted LLM, with citations and "last verified" dates
- Freshness pipeline: change detection, review queue, re-index, regression evals
- Evaluation harness and experiment log
- FastAPI backend and a simple web frontend
- AWS deployment with logging, cost tracking, rate limiting and load testing
- README, architecture diagram, demo

## Out of scope for v0.1

- Destinations other than Ireland and the USA
- Pathways not in the graph: marriage and family routes, asylum and refugee routes, special-protection programs, and any other route. These are declined as "outside supported pathways", not denied as nonexistent
- Individual case decisions, eligibility verdicts ("will I be approved") and legal strategy
- Form filling, document upload, user accounts, saved chats
- Training a model from scratch
- Fine-tuning for knowledge (see ADR-014). Fine-tuning for behaviour (intake, refusals, citation style) is an optional later experiment
- Mobile app, multilingual interface

## Rollout roadmap

| Release | Addition |
|---|---|
| v0.1 | Ireland + USA student pathways, full freshness pipeline |
| v0.2 | Canada, UK (proof that a new country is config + graph + evals) |
| v0.3 | Australia, Germany, Singapore |
| Later | Worker pathways, other visa types, more destinations |
| Stretch | Eligibility checker (rules engine plus LLM explanation); behaviour fine-tune compared with prompting |

The earlier UAE phase is dropped from the near-term roadmap in favour of the destinations above; it can return when there is demand.

## Definition of done (v0.1)

- Public HTTPS URL answering Ireland and USA student-pathway questions with citations and "last verified" dates
- Intake and guardrails working: unclear paths trigger clarification, out-of-pathway questions are refused
- Eval report on a 50+ question set including exception traps, refusals and cross-country contamination, with at least three documented experiments
- Freshness pipeline running on a schedule, with a working review queue, change log and regression gate; at least one real or simulated source change taken through the full loop
- Load test result and a monitored cost cap
- README with architecture, decisions, failures and results; public repository with clear history

## Ground rules

- Official sources only; every claim cites a source with its verification date
- When unsure, say so and link to the official page
- Not legal advice, and the interface says so
- Exceptions travel with their rules
- A country is not "supported" until its pathway graph, sources and eval questions are complete

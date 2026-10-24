# DISHAA: Project Proposal

**Dishaa** (Sanskrit: *direction*) is a retrieval-augmented assistant that helps people navigate visa and immigration pathways using only official, cited sources.

## 1. Problem

Visa and immigration information is spread across many government sites, changes often, and is written in dense legal language. Generic chatbots answer from training data that may be outdated, give no source, and can state wrong fees, deadlines or eligibility rules with full confidence. In this domain a wrong answer can cost someone a visa, money, or legal status.

## 2. Proposed solution

A retrieval-augmented generation (RAG) system that:

- Answers only from a curated corpus of official sources
- Cites the exact source page for every claim
- Says "I'm not sure" and points to the official source when the corpus doesn't cover a question
- Keeps its knowledge current through an automated freshness pipeline
- Is measured with a reproducible evaluation harness, so quality is a number, not a feeling

The LLM is a hosted model. The value of the project is the system around it: data pipeline, retrieval, evaluation, guardrails and deployment.

## 3. Target users (long term)

Students, workers, refugees and immigrants moving to or between countries. Version 1 targets **international students considering Ireland**.

## 4. Phased roadmap

| Phase | Scope | Outcome |
|---|---|---|
| 1 | Ireland, student visas | Working, evaluated, deployed system |
| 2 | UK, Canada | Proof the pipeline generalizes via config, not new code |
| 3 | UAE | Harder sources, emirate-level variation |
| 4 | USA (F-1 / OPT first) | Largest and most complex corpus |
| Later | Workers, refugees, other visa types | Broader coverage |

## 5. Technical approach

- **Language:** Python
- **API:** FastAPI
- **LLM:** hosted model through Amazon Bedrock
- **Retrieval:** embeddings plus a vector store (pgvector on RDS Postgres; Chroma locally)
- **Deployment:** Docker on AWS (ECS Fargate or App Runner), EventBridge for scheduled refresh
- **CI/CD:** GitHub Actions

## 6. What makes this more than a chatbot

1. Evaluation harness with retrieval and answer-quality metrics
2. Citations on every answer, plus calibrated refusals
3. Freshness pipeline: change detection and incremental re-indexing
4. Production-style deployment with logging, cost and latency tracking
5. Country-tagged data model so rules from one country never leak into another

## 7. Success criteria

- Retrieval hit rate and answer accuracy reported on a 50+ question Ireland eval set, with documented experiments (chunking, top-k, reranking)
- Correct refusal on out-of-scope questions
- Public URL with HTTPS and rate limiting
- README with architecture diagram, design decisions, failures and results

## 8. Risks

| Risk | Mitigation |
|---|---|
| Wrong or outdated legal information | Official sources only, citations, "not legal advice" notice, freshness job |
| Scope creep across countries | Ireland end to end first; one country at a time after |
| Cost overrun on hosted LLM and AWS | Rate limiting, budget alerts, caching |
| Scraping breaks or violates site terms | Respect robots.txt and terms, store source URL and date, prefer official downloads |
| Cross-country answer contamination | Country and visa-type metadata filters at retrieval time |

## 9. Timeline (Phase 1, about 4 weeks)

- **Week 1:** data collection, cleaning, chunking, embedding, retrieval baseline, first eval set
- **Week 2:** grounded generation, evaluation harness, chunking and retrieval experiments
- **Week 3:** API, frontend, guardrails, freshness job
- **Week 4:** AWS deployment, cost and latency tracking, README and demo

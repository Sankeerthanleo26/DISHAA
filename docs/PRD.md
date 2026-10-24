# DISHAA: Product Requirements Document (v1, Ireland)

**Status:** Draft
**Owner:** Sankeerthan Sornapoodi
**Version scope:** Ireland, student visas

## 1. Purpose

Let a prospective or current international student ask plain-language questions about Irish student immigration and get accurate answers grounded in official sources, with citations.

## 2. User stories

1. As a prospective student, I want to know what I need to apply for a study visa so that I can prepare my documents.
2. As a student in Ireland, I want to know how many hours I can work so that I stay compliant.
3. As a graduating student, I want to know my options to stay after my course (Stamp 1G) so that I can plan.
4. As any user, I want to see where each answer came from so that I can verify it myself.
5. As any user, I want the assistant to admit when it doesn't know so that I'm not misled.

## 3. Functional requirements

### 3.1 Data ingestion
- FR-1: Collect pages from approved official sources (see Scope doc) with URL and retrieval date.
- FR-2: Clean content (remove navigation and boilerplate) and split by section into chunks.
- FR-3: Attach metadata to each chunk: country, visa category, source URL, section title, retrieval date, content hash.

### 3.2 Retrieval
- FR-4: Embed chunks and store them in a vector index.
- FR-5: For each query, retrieve top-k chunks filtered by country and, when detectable, visa category.
- FR-6: Support configurable chunk size, overlap, top-k and optional reranking so they can be compared in experiments.

### 3.3 Answer generation
- FR-7: Generate answers using only retrieved context.
- FR-8: Every answer includes citations linking to source pages.
- FR-9: If retrieved context is insufficient, respond that the answer is not covered and link to the relevant official source.
- FR-10: Decline or hedge on questions outside scope (other countries, legal strategy, individual case decisions).
- FR-11: Display a "not legal advice" notice.

### 3.4 API and interface
- FR-12: `POST /ask` accepts a question and returns answer, citations, and a confidence or coverage indicator.
- FR-13: Simple web chat interface with clickable citations.
- FR-14: Log each request (question, retrieved chunk IDs, latency, token usage) without storing personal data.

### 3.5 Freshness
- FR-15: Scheduled job re-fetches sources, detects changes by content hash, and re-indexes only changed pages.
- FR-16: Record a change log of which pages changed and when.

### 3.6 Evaluation
- FR-17: Maintain a versioned eval set of 50+ questions, each with expected answer facts and source passages.
- FR-18: Report retrieval hit rate and answer correctness for any configuration.
- FR-19: Store experiment results so configurations can be compared.

## 4. Non-functional requirements

- **Accuracy:** target at least 85% answer correctness and 90% retrieval hit rate on the v1 eval set (to be revised after the baseline run)
- **Latency:** median response under 5 seconds
- **Cost:** hard monthly budget with alerts; per-IP rate limiting
- **Security:** HTTPS, no secrets in the repo, no personal data stored
- **Maintainability:** per-country source config, so adding a country requires config and eval questions, not code changes

## 5. Out of scope for v1

See the Scope doc.

## 6. Metrics

| Metric | Definition |
|---|---|
| Retrieval hit rate | Share of eval questions where the correct source chunk is in top-k |
| Answer correctness | Share of answers containing the expected facts and no contradictions |
| Refusal accuracy | Share of out-of-scope questions correctly declined |
| Citation validity | Share of citations that actually support the claim |
| Latency (p50, p95) | End-to-end response time |
| Cost per query | LLM plus infrastructure cost |

## 7. Open questions

- Which embedding model (hosted on Bedrock vs open-source) gives the best accuracy per cost?
- Should the LLM judge be a different model from the generator to reduce bias?
- How should the assistant handle ambiguous visa categories: ask a clarifying question or answer for the most likely one?

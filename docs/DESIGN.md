# DISHAA Design Doc (RFC-001)

Status: **Draft, decision 1 accepted 2026-11-21** · Author: Sankeerthan Sornapoodi (Drona) · Date: 2026-11-21
Related: [PRD](PRD.md), [Scope](SCOPE.md), [Decisions](DECISIONS.md), [Eval Plan](EVAL_PLAN.md), [Risk Register](RISK_REGISTER.md)

## 1. Context

DISHAA answers visa and immigration questions from curated official sources, cites every claim, and says "not sure, check X" when it is unsure. v0.1 covers Ireland and the USA on a country-agnostic architecture (ADR-015, ADR-016). Knowledge lives in documents, not model weights (ADR-014). The hard problem is keeping sources fresh (ADR-011, ADR-017).

This RFC records the technical decisions that the PRD leaves open. Each decision has options, a recommendation, and a way to check it against the eval set. Nothing is final until the decision's status says **accepted**.

## 2. Goals and non-goals

Goals
- Every answer is grounded in a cited, dated official source or is an explicit refusal.
- Swapping a model (generator or embedder) is a config change plus a regression run, not a rewrite.
- A source change reaches users only after the review and eval gates (ADR-017).

Non-goals (v0.1)
- Fine-tuning for knowledge (ADR-014).
- Multimodal retrieval, PDFs, voice.
- Legal advice.

## 3. Decision list

| # | Decision | Status |
|---|----------|--------|
| 1 | Generation model and embedding model | **Accepted** (generator pick pending bake-off) |
| 2 | Vector store (keep pgvector on Postgres) | **Accepted** 2026-11-21 |
| 3 | PDF handling | Not started |
| 4 | Freshness scheduler | Not started |
| 5 | Review queue | Not started |
| 6 | Deploy target and IaC | Not started |
| 7 | Eval tooling | Not started |
| 8 | Observability and cost | Not started |

## 4. Decision 1: Models

### 4.1 Why this comes first

`migrations/0001_init.sql` has `embedding vector(1024)` with a comment saying 1024 is a placeholder until the model is chosen. Changing the embedding model later means re-embedding every chunk, so we pick a default now and make the switch cheap.

### 4.2 Constraints

- Hosted on Bedrock (ADR-001), so candidates must be callable through `bedrock-runtime`.
- Postgres with pgvector and an HNSW index (ADR-002, ADR-004). pgvector's HNSW index supports `vector` up to 2,000 dimensions and `halfvec` up to 4,000.
- Answers must be grounded and calibrated. The generator must follow "answer only from the passages, otherwise refuse" reliably. That is a property we measure, not assume.
- Users come from many origin countries, so multilingual embedding quality matters for query-to-English-source matching.

### 4.3 Embedding model options

| Option | Dimensions | Max input | Notes |
|--------|-----------|-----------|-------|
| Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`) | 1024 default, 512, 256 | 8,192 tokens | 100+ languages, optional normalization. Text-only. Fits the current `vector(1024)` column. |
| Cohere Embed v4 | 256 to 1536 (configurable) | up to about 128k tokens | Multimodal, `input_type` distinguishes document and query. Fits under the 2,000 HNSW limit at 1536. |
| Nova Multimodal Embeddings | not checked | not checked | Aimed at mixed media. We have no images or video, so it is out of scope unless the bake-off shows text quality wins. |

### 4.4 Generation model options

| Option | Evidence found | Concern |
|--------|----------------|---------|
| Claude Haiku 5.5 (`anthropic.claude-haiku-5-5`) | Launched Oct 7, 2026, EOL no sooner than Oct 7, 2027, 1M context. | Per-token price not retrieved. |
| Claude Sonnet 5.5 (`anthropic.claude-sonnet-5-5`) | Standard Sonnet 5 pricing was $3 / $15 per million input/output tokens after Aug 31, 2026 (Sonnet 5.5 price not confirmed). | Higher cost per answer. |
| Amazon Nova 2 Lite | Cheap reasoning model, 1M context. | Listed EOL no sooner than Dec 2, 2026, which is a lifecycle risk for a long-lived system. |

Disclosure: the author of this document is a Claude model, so a recommendation for Claude generators has an obvious bias. The recommendation below is therefore a provisional default, and the final choice is made on the eval results, not on this table.

### 4.5 Recommendation

1. **Embeddings:** start with Titan Text Embeddings V2 at 1024 dimensions, normalized. It matches the existing schema, so no migration change is needed, and it is Bedrock-native. Run Cohere Embed v4 (1024 or 1536 dimensions) as the challenger.
2. **Generation:** make the generator a config value. Evaluate Haiku 5.5, Sonnet 5.5 and Nova 2 Lite on the same eval set and pick the cheapest that meets the gates. Do not choose by price before the refusal and exception-trap scores are in.
3. **Re-embedding must be cheap:** store `embedding_model` and `embedding_dim` on each chunk (or on a corpus-version row) so a model switch can run side by side and be rolled back.
4. **Judge model:** use a different model family or tier from the generator for LLM-as-judge scoring (PRD open question).
5. **Pin model IDs** in config and record the model ID in every answer log, because model lifecycle dates are real (see Nova 2 Lite above).

### 4.6 How we validate

Bake-off on the eval set, same chunks, same prompt:

| Metric | Gate (from Eval Plan) |
|--------|------------------------|
| Retrieval hit rate | at least 90% |
| Answer correctness | at least 85% |
| Refusal accuracy | at least 95% |
| Exception traps | 100% |
| Contamination failures | 0 |
| Citation validity | at least 95% |

Also record cost per answer and p95 latency. Tie-break: the cheaper model that passes all gates wins. The eval set currently has 32 seed rows, 15 of which still need expected facts, so the bake-off cannot run until those are filled in.

### 4.7 Open items

- Confirm current Bedrock prices for Haiku 5.5, Sonnet 5.5 and Titan V2 from the pricing page. The only Titan price we found is from an older blog post (about $0.02 per million tokens), so treat it as unverified.
- Confirm that Titan V2 and the chosen generator are available in the deployment region.
- Decide whether a cross-region inference profile is acceptable for the data we send (no personal data is stored, but questions may contain personal details).

## 5. Decision 2: Vector store

### 5.1 Decision

Keep pgvector on Postgres (confirms ADR-002 and ADR-004). Use RDS or Aurora PostgreSQL in AWS and Postgres in a container locally, so dev and prod run the same engine.

### 5.2 Why

- The corpus is small (47 sources, a few thousand chunks), far below the scale where a dedicated vector database pays off.
- Every query filters by pathway, step, country and freshness (ADR-016). Doing that in SQL next to the vectors, with joins to source and review-status tables, is simpler than syncing metadata to a second system.
- One database holds chunks, sources, change history and the review queue (ADR-017), so a source change and its re-embedding can happen in one transaction.
- AWS support exists: RDS for PostgreSQL 17 ships pgvector 0.8.x and Aurora PostgreSQL 18.4 (Aug 2026) is on pgvector 0.8.2.

### 5.3 The filtering trap (must be designed for)

With approximate indexes, pgvector applies filters after scanning the index. With HNSW and the default `hnsw.ef_search` of 40, a filter that matches 10% of rows returns about 4 rows on average. Our pathway filter is exactly this case, so a query could silently return too few chunks and the model would then refuse or answer from thin context.

Rules:
1. Require pgvector 0.8 or newer and set `hnsw.iterative_scan = strict_order` on the retrieval connection, so the index keeps scanning until enough filtered rows are found.
2. Add a test that every pathway filter returns the requested number of chunks (top-k) when enough matching chunks exist.
3. At this corpus size an exact scan (no index) is also acceptable and gives perfect recall. Benchmark both on the eval set, and keep the HNSW index only if it is needed for latency.
4. Consider partial indexes per pathway if filtering by only a few distinct values.

### 5.4 When we would revisit

- Corpus grows past roughly a million chunks, or p95 retrieval latency misses the NFR.
- We need hybrid keyword and vector ranking beyond what Postgres full-text search gives (one benchmark found hybrid search about 3x slower than pure vector search, so measure before adopting).
- Embedding dimension rises above the index limits (see decision 1).

### 5.5 Risks

- Silent recall loss from post-filtering (above). Mitigated by the iterative-scan setting and the top-k test.
- Managed Postgres cost when idle. Revisited in decision 6.

## 6. Sources checked (Nov 21, 2026)

- Titan Text Embeddings: https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html
- Titan V2 dimensions: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-embed-text.html
- Cohere Embed v4: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-embed-v4.html
- Claude Haiku 5.5 model card: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-5-5.html
- Claude Sonnet 5.5 model card: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html
- Nova 2 Lite model card: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-lite.html
- Bedrock pricing: https://aws.amazon.com/bedrock/pricing/
- pgvector index limits and filtering: https://github.com/pgvector/pgvector
- RDS pgvector versions: https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html
- Aurora PostgreSQL releases: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraPostgreSQLReleaseNotes/AuroraPostgreSQL.Updates.html

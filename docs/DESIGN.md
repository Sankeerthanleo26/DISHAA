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
| 3 | PDF handling | **Draft** |
| 4 | Freshness scheduler | **Accepted** 2026-11-21 |
| 5 | Review queue | **Draft** |
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

## 6. Decision 3: PDF handling

### 6.1 Decision (draft)

Keep v0.1 HTML-only (ADR-010). Track PDFs as known gaps. Promote a PDF only when an eval case needs it (ADR-021).

### 6.2 Why

- We have not yet seen our HTML extractor run on the real pages. Adding a second, harder extractor before that is guessing.
- PDF extraction can scramble tables, columns and footnotes. Exceptions are the thing DISHAA must not lose, so a bad parse is worse than a gap.
- The refusal path already handles gaps honestly: "not sure, check X".

### 6.3 What changes because of scope B

University tuition, fee and payment-plan rules are often published as PDFs or catalog pages. Expect pressure to promote PDFs in the university tier first. The promotion rule handles that without a blanket decision.

### 6.4 If a PDF is promoted

1. Store the raw bytes with a hash (already done for HTML, ADR-011).
2. Extract text per page and keep the page number as part of the citation.
3. Reject or flag pages where extraction looks wrong (very little text, scrambled tables) and have a human check the text before it is indexed.
4. Track the PDF's own date or version in the source registry, like page age for HTML.

### 6.5 Open items

- Choose the PDF extraction library only when the first PDF is promoted, and compare at least two on that file.
- Choose the pilot university or universities. This decides which PDFs are likely to matter.

## 7. Decision 4: Freshness scheduler

### 7.1 Decision (accepted 2026-11-21)

A scheduled job runs the existing `dishaa-fetch` code on a per-tier cadence, compares the cleaned-content hash with the stored one (ADR-011), and writes a row to the review queue (Decision 5) when it differs. Blocked pages (HTTP 403, ADR-023) are not fetched by the job. They get a **re-capture due date**, and the stale-source alert fires when it passes. Start the job on **GitHub Actions cron**; the same command moves to AWS EventBridge Scheduler when Decision 6 settles the deploy target.

### 7.2 What the first real run taught us

- 19 of 78 pages refused our fetcher, even from a home connection. Cloud IP ranges (GitHub, AWS) are usually treated more harshly than home ones, so expect more refusals, not fewer, once the job leaves a laptop.
- A page can change and keep its hash if the extractor drops the changed part (the UCD fee tables). The job therefore also checks that each page still contains what it should: a minimum word count, and for fee pages a table.
- Pages carry their own dates ("Last updated: Nov 28, 2023"). That date is a second change signal and a staleness signal.

### 7.3 Cadence (starting values, to tune from the change log)

| Tier | Check | Why |
|---|---|---|
| core, government | every 3 days | A rule change here makes answers wrong |
| core, university | weekly, daily in the 6 weeks before each term | Fees and deadlines move around term starts |
| supporting | every 14 days | Lower stakes |
| manually captured | re-capture due every 14 days (core) or 30 days (supporting) | No automatic signal exists |

Requests use ETag and If-Modified-Since when the server offers them, and keep the existing 3-second delay and robots.txt rules.

### 7.4 Options considered

| Option | For | Against |
|---|---|---|
| A. GitHub Actions cron | No infrastructure, free, every run has a public log, easy to show on a portfolio | Needs somewhere to keep state (a small Postgres or committed manifests); cloud IPs; 6-hour job limit is fine for this load |
| B. AWS EventBridge Scheduler plus a Fargate or Lambda task | Matches the production target; IAM, retries, alarms | Needs Decision 6 first; more to build before the first change is detected |
| C. cron on a small always-on server | Simple mental model | A server to patch and pay for, and nothing about it is portfolio-worthy |

Recommendation: A now, B when Decision 6 is made. Keep the job as a plain command, so moving it is a config change.

### 7.5 Open items

- Where does the job keep state before the production database exists? (Likely the manifests plus a small SQLite or Postgres file in the repo's Actions cache.)
- Whether to email UCD, CU Denver and the State Department for permission or a feed. This is the only route that removes the manual list.
- Decision 5 (review queue) decides what a human sees when the job reports a change.

## 8. Decision 5: Review queue

### 8.1 Decision (draft)

Each detected change becomes **one pull request in a private corpus repository**. The PR shows the old and new cleaned text of the page side by side, a short machine-written summary of what changed, the affected sources, pathways and steps, and the page's own "last updated" date. CI runs the full eval set on the change. **Merging the PR is the approval**, and the merge records who approved and when (FR-32). Postgres holds the serving state: `pending`, `active` or `superseded` per page version. A page with a `pending` core change is served with the "update pending review" warning (FR-29) until the merge flips it to `active`.

### 8.2 Why

- A pull request already is a review queue: diff view, comments, required checks, an audit trail and a notification, with nothing to build or host.
- The eval gate (FR-31) maps onto a required CI check, so "drop below threshold blocks the change" is how the tool works, not extra code.
- It is easy to show: the queue, the reviews and the decisions are public process even though the content is private.
- It fits one reviewer (R16) and still works if a second reviewer joins.

### 8.3 What the reviewer checks (checklist in every PR)

1. Does the new text say what the page now says? Open the live page and compare.
2. Is any exception, footnote or table row missing from the new text (R2, and the UCD fee tables)?
3. Does it contradict another source we hold (R21)? If so, mark "sources differ".
4. Does the page's own date match the change?
5. Review checks "matches the source", not "legally correct" (R16). The PR template says so.

### 8.4 Options considered

| Option | For | Against |
|---|---|---|
| A. Pull requests in a private corpus repo | No build, audit trail, CI gates, notifications | Needs a private repo; two places hold state (git for content, Postgres for serving); slower than a button |
| B. Small admin web page | One screen, approve and reject buttons | Real work to build and secure; weaker audit trail; a login to protect |
| C. Command line plus a Postgres table | Quick to build | No diff view, easy to forget, nothing to show |

Recommendation: A for v0.1. Revisit B only if the queue grows past what one person can handle (R16).

### 8.5 Open items

- **Copyright:** the cleaned text of official pages must not sit in a public repository (the code repository already ignores `data/` for this reason). The corpus repository must be private, or the diffs must live in object storage with only links in the PR.
- Define the queue size at which an alert fires (R16).
- Decide how manually captured pages (ADR-023) enter the same flow. The likely answer is the same PR, opened by `dishaa-manual`.
- Whether a rejected change keeps the old version active and shows a "page changed, review rejected" flag.

## 9. Sources checked (Nov 21, 2026)

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

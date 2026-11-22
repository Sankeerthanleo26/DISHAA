# DISHAA Design Doc (RFC-001)

Status: **Accepted, all eight decisions 2026-11-21 (open items remain)** · Author: Sankeerthan Sornapoodi (Drona) · Date: 2026-11-21
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
| 3 | PDF handling | **Accepted** 2026-11-21 |
| 4 | Freshness scheduler | **Accepted** 2026-11-21 |
| 5 | Review queue | **Accepted** 2026-11-21 |
| 6 | Deploy target and IaC | **Accepted** 2026-11-21 |
| 7 | Eval tooling | **Accepted** 2026-11-21 |
| 8 | Observability and cost | **Accepted** 2026-11-21 |

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

### 6.1 Decision (accepted 2026-11-21)

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

### 8.1 Decision (accepted 2026-11-21)

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

- **Copyright (settled 2026-11-21):** the cleaned text of official pages must not sit in a public repository (the code repository already ignores `data/` for this reason). The corpus lives in a second, **private** repository, for example `dishaa-corpus`. The founder approved this.
- Define the queue size at which an alert fires (R16).
- Decide how manually captured pages (ADR-023) enter the same flow. The likely answer is the same PR, opened by `dishaa-manual`.
- Whether a rejected change keeps the old version active and shows a "page changed, review rejected" flag.

## 9. Decision 6: Deploy target and infrastructure as code

### 9.1 Decision (accepted 2026-11-21)

- **API:** AWS Lambda running the Python app as a container image, behind an API Gateway HTTP API. It scales to zero, so an idle demo costs close to nothing, and API Gateway gives the throttling and custom domain we need for per-IP rate limiting (FR-26).
- **Database:** Aurora PostgreSQL Serverless v2 with auto-pause (minimum 0 ACUs), pgvector 0.8 or newer (Decision 2). The first request after a pause waits for the database to resume, which can take up to about 15 seconds. The intake questions take longer than that, so the web page opens a database connection as soon as it loads (a "warm-up" call) and the user never waits.
- **Freshness job and CI:** GitHub Actions (Decision 4) with OpenID Connect to AWS, so no long-lived keys are stored.
- **Infrastructure as code:** Terraform, with state in S3. `terraform plan` output is posted on every pull request, the same review habit as Decision 5.
- **Region:** pick after checking where Titan V2 and the chosen generator are available (Decision 1 open item).
- **Cost control:** AWS Budgets alerts and a **hard cap in the application** (a daily and monthly counter of Bedrock calls, checked before each call). Budgets alerts do not stop spending by themselves.

### 9.2 Why

- A portfolio project gets few visitors. Paying for an always-on load balancer and database for a demo is the main avoidable cost, and scale-to-zero removes it.
- It is the pattern real teams use for low-traffic APIs, so running it shows the skills a hiring manager looks for: containers, IAM, IaC, CI to cloud, alarms.
- App Runner, the obvious "just run my container" service, is closed to new customers since April 30, 2026. AWS points to ECS Express Mode instead.

### 9.3 Options considered

| Option | For | Against |
|---|---|---|
| A. Lambda container + API Gateway + Aurora Serverless v2 (recommended) | Scales to zero; throttling and custom domain; low idle cost | Database resume delay (handled by warm-up); Lambda cold starts; two services to learn |
| B. Lambda Function URL, no API Gateway | Simplest; no extra charge for the URL | Basic auth only, and API Gateway is the route AWS recommends when you need throttling and custom domains, which FR-26 needs |
| C. ECS Express Mode (Fargate) + RDS PostgreSQL | One always-on container, no cold starts, steady latency | Pays for compute, a load balancer and a database while idle; more to patch |
| D. App Runner + RDS | Easiest to run | Closed to new customers since April 30, 2026 |

### 9.4 Risks

- **Resume delay:** a paused database takes up to about 15 seconds to wake, and AWS recommends connection retries. A user who skips the intake flow (a direct link) could still wait. Mitigation: retry logic, a "waking up" message, and a health check that tests resume time.
- **Cold starts** on Lambda affect the first request after a quiet period. Measure p95 and set the NFR from the measurement.
- **Always-on alternative:** if the demo needs steady latency (for example during interviews), set the database minimum to 0.5 ACU for that window. Prices are unverified; check the Aurora pricing page before committing.

### 9.5 Open items

- Choose the AWS region and confirm Bedrock model availability there.
- Confirm Aurora Serverless v2 auto-pause works with the PostgreSQL engine version and pgvector 0.8.x we pin.
- How per-IP limits are enforced behind API Gateway (usage plans or a WAF rate rule); verify cost and behaviour.
- One account or two (dev and prod). Start with one and separate by naming, move to two when there is real data.
- Whether local development uses Docker Postgres only (current plan) or also LocalStack.

## 10. Decision 7: Eval tooling

### 10.1 Decision (accepted 2026-11-21)

Build a small eval harness in our own Python code, in two layers, and run it from pytest and CI.

1. **Rule checks (no model needed, run on every pull request):** retrieval hit (did the expected source appear in the top-k), refusal accuracy, cross-country contamination, citation validity (every cited passage exists, and says what the answer claims), and exception traps (the answer must contain each required exception, and must not state the general rule alone).
2. **Judge checks (a model scores each answer, run on release candidates and model changes):** correctness against expected facts, and faithfulness to the retrieved passages. The judge is a different model family or tier from the generator (Decision 1). We hand-label 20 cases first and measure how often the judge agrees with us before trusting it.

Results are written to a JSON run report that is committed with the change (and later to a Postgres table), so any two runs can be compared by commit.

### 10.2 Why

- Four of the six gates in the Eval Plan are rules, not opinions. Checking them with code is cheaper, faster, deterministic and does not depend on a judge model being right.
- The exception-trap gate is 100%, and a judge can be lenient. Required-fact assertions cannot.
- Writing the harness is itself proof of work: a reader of the repository sees how quality is measured, not a tool's default dashboard.
- Gates plug into the review queue (Decision 5) as a required CI check.

### 10.3 Options considered

| Option | For | Against |
|---|---|---|
| A. Own harness, two layers (recommended) | Fits our exact gates; deterministic rule checks; small; shows engineering | We write and maintain it; judge prompts need calibration |
| B. Amazon Bedrock Evaluations (managed) | Judge-based metrics for correctness, completeness, faithfulness and refusal; evaluates a custom RAG pipeline from responses we supply; includes citation precision and coverage metrics | Runs as jobs with S3 and IAM, so slow and awkward as a per-PR check; judge metrics only, no rule checks; costs per job |
| C. Open-source framework (promptfoo, Ragas, DeepEval, Inspect) | Ready-made metrics and reports; promptfoo is built for CI gates and Ragas for retrieval and faithfulness metrics | Another dependency and config language; the metrics are generic, while our gates are specific rules; Ragas and similar tools are judge-based, so the 100% exception gate would still need our own assertions |

Recommendation: A. Use B once, as an independent cross-check during the model bake-off (Decision 1), to see whether its judge scores agree with ours. Revisit C if the harness grows past what we want to maintain.

### 10.4 What blocks it

- 15 of the 32 seed rows have no expected facts yet, and the 17 drafted cases are unreviewed. A case without an official source passage for its expected facts does not count toward any gate (R18).
- Pages with missing base rules (the UCD fee tables) mean fee cases cannot be written correctly yet (R23).

### 10.5 Open items

- Write the judge prompt and the 20-case hand-labelled calibration set.
- Decide the pass rule for a case with several required facts (all required, or a weighted score). Starting rule: all required facts present and no forbidden claim.
- Where the harness stores run reports before the production database exists.
- Whether to add adversarial and prompt-injection cases to the same harness (R14).

## 11. Decision 8: Observability and cost

### 11.1 Decision (accepted 2026-11-21)

Use **CloudWatch** (logs, metrics, alarms, dashboard) for v0.1, defined in Terraform with the rest of the infrastructure (Decision 6). Every request writes one structured log line. Alarms page the founder by email. Add Grafana later as a stretch, reading the same CloudWatch data.

**One structured log line per request** holds: request id, timestamp, pathway and step, the pinned generator and embedder model IDs, latency of each stage (retrieve, generate, validate), token counts and estimated cost, the ids and versions of the retrieved chunks, the outcome (answered, refused, error) with the refusal reason, and the citation-validity result.

**Raw question text is logged (founder decision, 2026-11-21).** This amends FR-25 and raises R19. The PII redaction layer is deferred, and the release gate in R19 applies: no public launch until a PII layer exists (redact before write, with a leak test in the eval harness) or the raw-text logging is turned off. While raw text is logged, three free defaults apply: logs encrypted at rest, access limited to the founder, 30-day retention. **Origin country is not logged as a field** and is never joined to a request, which keeps it out of the debugging trail (FR-5).

### 11.2 What we watch

| Signal | Why | Alarm |
|---|---|---|
| p50 and p95 latency per stage | Slow retrieval or a database resume shows here | p95 above the target set after the first measurement |
| Error rate | Bedrock throttling, database failures | Above 2% over 15 minutes (starting value) |
| Refusal rate and refusal reasons | A jump means retrieval broke or a source vanished | Above twice the 7-day average |
| Cost per answer, Bedrock calls per day against the cap (Decision 6) | The hard cap is in the app, so we watch how close we are | 70% and 90% of the daily and monthly cap |
| Database resume count and time | The auto-pause delay (Decision 6) | Resume over 30 seconds, or a failed resume |
| Stale sources, manual pages past their re-capture date | Freshness is the product (Decision 4) | Any core source past its window |
| Review queue age | One reviewer (R16) | Any pending change older than 7 days |
| Eval pass rate per release | Quality gates (Decision 7) | Any gate below its threshold blocks the release |

### 11.3 Cost model

Cost per answer = query embedding + generation input tokens + generation output tokens, using a price table kept in configuration and tied to the pinned model IDs. **The prices are unverified** (Decision 1 open item), so the table starts empty and the first task is to fill it from the Bedrock pricing page. Fixed costs to add up in the cost model: the database while awake, API Gateway requests, CloudWatch logs and metrics, and the Terraform state bucket.

### 11.4 Options considered

| Option | For | Against |
|---|---|---|
| A. CloudWatch only (recommended) | In the same account, no extra service, alarms and dashboards as code, cheap at this volume | Dashboards are plain; a log query language to learn |
| B. CloudWatch plus Grafana (Amazon Managed Grafana or Grafana Cloud) | Better dashboards, a skill employers ask about | Another service to run and pay for; not needed to meet a requirement |
| C. An LLM-observability platform (Langfuse or similar) | Trace view of prompts and retrieved chunks | Stores prompts, which conflicts with not logging questions; another service |
| D. A full vendor stack (Datadog or similar) | Everything in one place | Cost and lock-in out of proportion to a demo |

Recommendation: A now. Add B once the log lines and metrics exist, because the data comes first and the dashboard is a view over it.

### 11.5 Open items

- Set the latency target after measuring cold starts and resume time (Decision 6 risks).
- Verify CloudWatch and Bedrock prices before committing to the retention period.
- Write a one-page runbook for each alarm: what it means, how to check, how to fix.
- Decide log retention (starting value: 30 days) and what, if anything, is kept longer.
- Build the PII layer before any public launch (R19 release gate): choose a redaction tool (verify AWS options), redact before write, and add the leak test to the eval harness.
- Decide what the "answer was wrong" report flow looks like for users. With raw text logged, real questions can seed new eval cases once reviewed.

## 12. Sources checked (Nov 21, 2026)

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
- App Runner availability change: https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html
- Aurora Serverless v2 scale to zero: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html
- Aurora scale-to-zero announcement and resume time: https://aws.amazon.com/blogs/database/introducing-scaling-to-0-capacity-with-amazon-aurora-serverless-v2
- Lambda HTTP invoke options (Function URL vs API Gateway): https://docs.aws.amazon.com/lambda/latest/dg/apig-http-invoke-decision.html
- Bedrock RAG evaluation (custom pipelines, metrics, judge models): https://aws.amazon.com/about-aws/whats-new/2025/03/amazon-bedrock-rag-evaluation-generally-available
- Bedrock evaluations, citation precision and coverage: https://aws.amazon.com/blogs/machine-learning/evaluate-models-or-rag-systems-using-amazon-bedrock-evaluations-now-generally-available
- Eval framework comparisons (secondary sources, treat as opinion): https://andrew.ooo/answers/best-ai-eval-frameworks-april-2026/ and https://machinelearningmastery.com/llm-evaluation-frameworks-compared-how-to-actually-measure-what-your-model-does/

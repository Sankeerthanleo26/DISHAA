# Architecture Decision Log

Each entry records what we chose, why, what else we considered, and what the choice costs us.

---

## ADR-001: Retrieval-augmented generation with a hosted LLM (not a model trained from scratch)

**Decision:** Use a hosted LLM (via Amazon Bedrock) and ground it with retrieval over official sources.

**Why:** Visa rules are facts that change. Facts stored in model weights go stale and can't be cited. Facts stored in documents can be updated, cited and audited. Training a useful model from scratch also needs a compute budget far beyond a side project.

**Alternatives:**
- *Pretrain from scratch:* educational, but the result can't answer questions usefully at affordable scale.
- *Fine-tune an open model on visa text:* helps with tone and format, but still can't cite or stay current. Possible later as an experiment.
- *Prompt only, no retrieval:* simplest, but answers come from training data with no sources.

**Trade-offs:** We depend on a third-party model and pay per request. In exchange we get citations, freshness and a system that can be evaluated.

---

## ADR-002: Postgres with pgvector for vectors and everything else

**Decision:** Store documents, chunks, embeddings (and later logs and eval results) in one PostgreSQL database with the pgvector extension. Run it locally in Docker; deploy on RDS.

**Why:** The project needs more than vectors: change history for the freshness job, request logs, eval results. One database handles all of it, with transactions, SQL filtering by country and visa type, and managed backups on AWS. Local and production use the same engine, so there are no surprises at deploy time.

**Alternatives:**
- *Chroma:* faster to start, but a second store is needed for non-vector data, and you own backups and consistency.
- *Managed vector services (Pinecone, OpenSearch):* scale further than we need and add cost and vendor lock-in.
- *FAISS in memory:* very fast, but no persistence, filtering or transactions without extra code.

**Trade-offs:** More setup on day one (Docker, schema, migrations) and an RDS bill when deployed. Vector search speed at our scale is not the concern.

---

## ADR-003: Two tables, `documents` and `chunks`

**Decision:** `documents` holds one row per source page (URL, country, visa category, content hash). `chunks` holds the embedded pieces and points back to its document.

**Why:** The freshness job compares a page's hash to decide whether anything changed, and only then re-chunks and re-embeds that one document. Citations point to a document URL. Metadata like country lives once on the document instead of being copied into every chunk.

**Alternatives:**
- *One flat chunks table with all metadata repeated:* simpler, but changes and deletions are messier and metadata can drift between chunks of the same page.

**Trade-offs:** Retrieval needs a join to get country and URL. At our size that cost is negligible.

---

## ADR-004: HNSW index with cosine distance

**Decision:** Index embeddings with HNSW using cosine similarity.

**Why:** Text embeddings are normally compared by direction rather than magnitude, which is what cosine measures. HNSW gives fast approximate search without needing to be trained on data first.

**Alternatives:**
- *No index (exact search):* perfectly accurate and fine for a few thousand chunks, but slower as the corpus grows. We keep the index so the design scales to five countries.
- *IVFFlat:* smaller index, but must be built after data is loaded and tuned, and recall is more sensitive to settings.

**Trade-offs:** Approximate search can occasionally miss a true nearest neighbour, and the index uses more memory and build time. We'll measure recall in the eval harness rather than assume it.

---

## ADR-005: Plain SQL migrations with a small runner

**Decision:** Schema changes live in numbered `.sql` files in `migrations/`, applied once each by `dishaa-migrate`.

**Why:** The schema is small, the SQL is readable, and every step is visible, which helps while learning. The runner is about 30 lines.

**Alternatives:**
- *Alembic:* the standard Python tool, with autogeneration and downgrades. Heavier than we need now, and its main benefit is with SQLAlchemy models, which we are not using.
- *Creating tables inside application code:* no history, and it is hard to evolve safely.

**Trade-offs:** No automatic rollbacks and no autogeneration. If the schema grows complicated we can adopt Alembic later; the SQL files carry over.

---

## ADR-006: `src/` layout, `pyproject.toml`, settings from environment

**Decision:** Package code under `src/dishaa/`, dependencies in `pyproject.toml`, configuration through `DISHAA_*` environment variables via pydantic-settings.

**Why:** The `src/` layout forces tests to import the installed package, which catches packaging mistakes early. Environment-based configuration works the same locally, in Docker and on AWS, and keeps secrets out of the repository.

**Alternatives:** flat layout with `requirements.txt` (simpler, but looser packaging); a config file committed to the repo (risks leaking secrets).

**Trade-offs:** Slightly more ceremony up front.

---

## ADR-007: A curated list of URLs instead of a crawler

**Decision:** Sources are a hand-picked list in `sources/ie_student.toml` (14 pages for Ireland v1), each tagged with country, visa category and tier (core or supporting).

**Why:** Immigration answers must come from pages we trust. A fixed list keeps the corpus clean, makes every document's origin auditable, and keeps the load on government servers tiny. Adding a country later means adding a new list file, not changing code.

**Alternatives:**
- *Crawler that follows links:* finds more pages automatically, but pulls in irrelevant and outdated pages, is harder to keep correct, and creates more politeness and legal questions.
- *Sitemap-based ingestion:* good for full-site coverage, but we would still need to filter to the relevant pages.

**Trade-offs:** New pages the government adds are not discovered automatically; someone has to add them to the list. For a high-stakes domain we consider that a feature.

---

## ADR-008: Polite fetching: robots.txt, rate limiting, honest User-Agent

**Decision:** Before fetching, read each site's robots.txt and skip disallowed pages. Wait 2 seconds between requests. Identify ourselves in the User-Agent with a link to the repository. If robots.txt cannot be read (network error or server error), do not fetch and report `robots_unreadable`; a missing robots.txt (404) means no restrictions.

**Why:** It is the correct way to collect data from public sites, avoids harming a government service, and shows responsible engineering. Reporting "could not read robots.txt" separately from "the site said no" keeps problems diagnosable.

**Alternatives:** ignoring robots.txt (rude, and risks being blocked); fetching anyway when robots.txt is unreadable (faster, but we would not know whether we were allowed).

**Trade-offs:** A full run of 14 pages takes about half a minute instead of a few seconds, and a temporary robots.txt problem pauses ingestion until it is fixed.

---

## ADR-009: Keep raw downloads separate from cleaned text, and out of Git

**Decision:** Each fetch saves the untouched response bytes to `data/raw/<country>/<id>.html` (or `.pdf`) and writes a `manifest.json` with URL, final URL, HTTP status, content type, size, SHA-256 hash and timestamp. `data/raw/` is listed in `.gitignore`.

**Why:** Cleaning and chunking rules will change many times during experiments. With the raw copy saved, we re-run those steps without downloading again, and the hash feeds the freshness job. Raw pages are other people's content and large, so they do not belong in the repository.

**Alternatives:** clean while downloading (saves a step, but any cleaning mistake means re-downloading); commit raw pages (gives a visible history, but bloats the repo and republishes third-party content).

**Trade-offs:** Anyone cloning the repo must run the fetcher to get the data, and the snapshot is only as current as the last run.

---

## ADR-010: A hand-written HTML extractor that keeps structure

**Decision:** `extract.py` reads each saved page with BeautifulSoup. It finds the content area (`<main>`, then `<article>` and a few other common containers, falling back to `<body>`), removes menus, footers, sidebars, cookie banners and similar, and converts what is left into a flat list of blocks: headings (with levels), paragraphs, list items and table rows. Tables become one line per row ("Course type: X; Hours per week: 12") so each row still makes sense alone.

**Why:** The chunker cuts pages along their headings, so the extractor must keep the heading structure. We also want to see exactly why each piece of text was kept or dropped, and to be able to tune the rules per site without fighting a library.

**Alternatives:**
- *trafilatura or readability-style "main content" libraries:* less code and good at articles and blogs, but they are built to return flowing prose, so headings and tables are often flattened, and the rules are hard to inspect or adjust.
- *Converting the whole page to Markdown and chunking that:* simple, but menus and footers come along and have to be removed anyway.
- *Rendering the page in a real browser (Playwright):* handles content built by JavaScript, but is slower, heavier, and not needed unless we find pages that need it.

**Trade-offs:** More code to maintain, and the rules are general guesses about how government sites are built. **Not yet checked against the real pages** (the build environment could not reach them), so the first real run must be inspected by eye: `dishaa-chunk --show <page id>`. The extractor does not run JavaScript, so content added by scripts would be missing; the pipeline warns when a page has very little text.

---

## ADR-011: Hash the cleaned content, and keep "hidden" text

**Decision:** A document's `content_hash` is a fingerprint of its cleaned blocks, not of the raw HTML. And we do not remove elements merely because they are marked hidden.

**Why:** Raw HTML changes on every visit for reasons that have nothing to do with the rules (a footer timestamp, a rotating banner, a cookie-script version). Hashing raw bytes would make the freshness job think every page changed every day. Hashing the cleaned content only changes when the real content or structure changes (a test checks this). On hidden text: FAQ accordions usually mark their collapsed answers as hidden until clicked, but those answers are the content we want.

**Alternatives:** hash the raw HTML (simpler, but constant false alarms); drop hidden elements (loses FAQ answers).

**Trade-offs:** A change that only affects what we strip (for example, a note placed in a sidebar) is invisible to us. And because hidden text is kept, a page that hides genuinely irrelevant text will have it included. **Known limitation:** an accordion question that follows an `<h3>` is ranked one level below it, so it can be filed under the wrong parent heading. Accordions directly under an `<h2>` are fine. We will check the real pages.

---

## ADR-012: Chunk along the page's headings, within size limits

**Decision:** `chunk.py` cuts each page into sections at its headings. A section that fits becomes one chunk; a longer one is split at paragraph, list-item and table-row boundaries (over-long paragraphs at sentence ends), and each new piece repeats the end of the previous one. Very small sections are merged with neighbouring sections under the same parent heading, and the merged chunk keeps their headings in its text. Every chunk records its heading path (for example "Frequently asked questions > Can I volunteer?"), and the text we will embed starts with the page title and that path.

**Starting values** (all adjustable on the command line, to be tuned by experiment): maximum 500 tokens, merge sections under 60 tokens, overlap 60 tokens. Overlap repeats whole units where they fit, otherwise the last sentences of a paragraph.

**Why:** Government pages are already organised by topic. Splitting where the authors split keeps one rule with its conditions in one chunk. The heading path means a chunk reading "20 hours per week" still says what it is about. Never cutting inside a table row or a sentence keeps facts intact.

**Alternatives:**
- *Fixed-size windows (every N tokens):* simplest, but cuts through the middle of rules and mixes topics.
- *Recursive character splitters (as in LangChain):* similar to ours but blind to headings and tables.
- *Semantic chunking (use embeddings to find topic changes):* adapts to messy text, but costs embedding calls, is hard to debug, and our pages already have structure.
- *LLM-written chunks:* highest quality in principle, slow and costly, and the model could rewrite facts.

**Trade-offs:** Chunk sizes vary, and a page with poor headings gets size-based chunks only (the pipeline warns about it). The values above are educated guesses; the evaluation harness decides them, not intuition.

---

## ADR-013: Approximate token counting for now

**Decision:** Token counts are estimated as the larger of 1.3 x words and characters / 4. No tokenizer library is used yet.

**Why:** Each embedding model counts tokens its own way, and we have not chosen one. An exact count from the wrong tokenizer would be false precision, and some tokenizer libraries download data files at first use. The estimate is within about 20% and errs towards smaller chunks.

**Alternatives:** tiktoken (an OpenAI tokenizer, not the one our model will use); the chosen model's own tokenizer (best, but not available until the model is picked).

**Trade-offs:** A chunk can be somewhat over or under its nominal size. Once the embedding model is chosen we replace `estimate_tokens` with its tokenizer, and nothing else changes.

---

## Open decisions

- **Embedding model and its dimension.** The schema uses `vector(1024)` as a placeholder. Changing it later requires a migration and re-embedding everything, so we will confirm the model before loading real data.
- **Chunk size, overlap and merge thresholds.** Starting values are set (ADR-012); the final values come from experiments with the eval set.
- **Per-site extraction tuning.** To be decided after the first inspection of the real pages (ADR-010).
- **LLM and embedding provider access** (Bedrock model choices, regions, cost caps).

---

## ADR-014: Knowledge lives in documents, not model weights; fine-tune for behaviour at most

**Decision:** Do not fine-tune for factual knowledge. All immigration facts come from retrieved, cited documents. If we ever fine-tune, it is only for behaviour: intake questions, refusals, citation style.

**Why:** Immigration rules change. Facts baked into weights go stale silently, cannot be cited, and cannot be audited, and every policy change would need retraining and re-evaluation. Documents can be updated, versioned and diffed. This extends ADR-001.

**Alternatives:**
- *Fine-tune on visa text:* may improve tone and domain vocabulary, but stale-fact risk is the exact problem we are solving.
- *Prompt only with no retrieval:* no sources, no freshness.

**Trade-offs:** Quality depends on retrieval and chunking quality, so those need most of our evaluation effort. A behaviour fine-tune stays available as an experiment compared against plain prompting.

---

## ADR-015: Global vision, staged rollout, country-agnostic architecture

**Decision:** The product vision covers any origin to any popular destination, but each release fully covers a small number of destinations. v0.1 is Ireland (simple, slow-changing) plus the USA (large, fast-changing). Everything country-specific lives in config and data (source list, pathway graph, eval questions), not code.

**Why:** A half-covered country gives wrong answers by omission, which is the failure we exist to prevent. Pairing one simple and one hard destination tests both the basic pipeline and the freshness problem in a single release. It also forces the country-agnostic design that makes later countries cheap.

**Alternatives:**
- *Ireland only first:* easiest, but never tests freshness on a hard, fast-moving corpus.
- *Many countries shallowly:* looks impressive, but quality and trust suffer, and evaluation becomes impossible to keep honest.

**Trade-offs:** USA content raises source-curation and update effort in v0.1. Documented in the PRD risk list.

---

## ADR-016: Curated pathway graphs with an intake, plus a scope allowlist

**Decision:** Each destination has a curated pathway graph (ordered steps and branches, for example Student → F-1 → OPT → STEM OPT → H-1B → green card, or O-1). A three-question intake (origin, destination, degree) selects a pathway. Retrieval is filtered to the selected pathway and step. Questions outside the graph are refused.

**Why:** Free-form retrieval over a large corpus produces information overload and conflicting sources. Selecting the path first shrinks what can be retrieved, lowers contamination between routes, and makes the refusal rule simple and testable: if it is not in the graph, it is out of scope.

**Alternatives:**
- *Pure semantic retrieval over everything:* simpler, but exactly the overload we are removing.
- *LLM-inferred pathways at runtime:* flexible, but not auditable, and it can invent routes.

**Trade-offs:** Graphs are hand-maintained and can themselves go stale, so they go through the same review process as sources. Narrow scope means some legitimate questions are declined by design. Refusals must say "outside supported pathways", never imply that a route does not exist.

---

## ADR-017: Changed sources go through review before they are served as current

**Decision (accepted 2026-11-21):** A detected change in a core-tier source creates a review-queue entry. Until a human approves it, answers relying on that page carry an "update pending review" warning. Approval triggers a regression run of the eval set, and failing evals block the change.

**Why:** A silent scraper error or a misparsed page could change answers in a high-stakes domain. Human review plus automatic regression tests keeps the speed of automation without trusting it blindly.

**Alternatives:**
- *Auto-publish all changes:* fastest, but a bad parse reaches users.
- *Block everything until reviewed:* safest, but the system serves outdated rules during review.

**Trade-offs:** Review is manual work and a bottleneck. Supporting-tier sources may be auto-approved later. Status: **accepted** (2026-11-21); see docs/DESIGN.md section 8.

---

## ADR-018: Provisional model choices, validated by bake-off

**Decision (accepted 2026-11-21):** Embeddings default to Titan Text Embeddings V2 at 1024 dimensions, normalized, with Cohere Embed v4 as the challenger. The generator is a config value; Claude Haiku 5.5, Claude Sonnet 5.5 and Nova 2 Lite are compared on the eval set and the cheapest model that passes every release gate is chosen. Model IDs and embedding dimension are recorded with every chunk and every answer.

**Why:** The embedding choice fixes the `vector(...)` dimension, and changing it means re-embedding everything. 1024 matches the existing schema and is well under pgvector's 2,000-dimension HNSW limit. The generator should be chosen on measured refusal and exception-trap scores, not on price or on the author's preference.

**Alternatives:**
- *Cohere Embed v4 as default:* larger context and configurable size, but more surface than a text-only product needs; kept as the challenger.
- *Pick the generator now:* faster, but unmeasured, and the author of this ADR is a Claude model.

**Trade-offs:** The bake-off needs the eval set filled in first. Model lifecycle dates force periodic re-validation. Status: **accepted** (2026-11-21); generator choice still pending the bake-off. See docs/DESIGN.md section 4.

---

## ADR-019: pgvector retrieval uses iterative scans and a top-k filter test

**Decision:** Retrieval connections require pgvector 0.8 or newer and set `hnsw.iterative_scan = strict_order`. A test asserts that every pathway filter returns the requested number of chunks when enough exist. Exact scan is benchmarked as an alternative at our corpus size.

**Why:** pgvector filters after the approximate index scan, so a narrow pathway filter can return far fewer rows than asked for, which would look like a missing source and trigger a wrong refusal.

**Alternatives:**
- *Default HNSW settings:* fast, but silently loses recall under filters.
- *Separate index or table per pathway:* works, but multiplies migrations and indexes.

**Trade-offs:** Iterative scans can be slower on very selective filters. Status: **accepted** (2026-11-21); see docs/DESIGN.md section 5.

---

## ADR-020: v0.1 adds a university-layer pilot (scope option B)

**Decision (accepted 2026-11-21):** v0.1 adds a fourth, optional intake question (the university) and a university source tier for one or two pilot universities. It covers admissions requirements, tuition and fees, payment plans, health insurance and on-campus housing. State, tax, driver's licence, mobile-plan and off-campus topics are declined and kept on the v0.2 backlog. This amends ADR-016, which assumed a three-question intake.

**Why:** 9 of the founder's 15 real questions depend on the university, the state or daily life, not on immigration law. The lost-exception failure (a general rule hiding an international-student exception, as in the tuition payment-plan story) lives in university documents. Taking it on keeps the product's hardest problem, freshness plus exceptions, central without turning v0.1 into a life-admin assistant.

**Alternatives:**
- *A. Immigration only:* simplest, but 9 of 15 real questions are refused.
- *C. Everything:* dozens of source sets, and most effort would go to sources instead of freshness.

**Trade-offs:** More sources to curate and review. Results from one or two universities may not generalise. University documents are often PDFs or catalog pages, so ADR-021 matters more. The pilot universities are CU Denver (US) and University College Dublin (Ireland), chosen 2026-11-21.

---

## ADR-021: PDFs stay deferred in v0.1; promotion needs an eval case

**Decision (accepted 2026-11-21):** The extractor stays HTML-only (ADR-010). PDFs are listed in the source registry as known gaps, never silently dropped. A PDF is promoted to in-scope only when a specific eval case cannot be answered correctly from HTML sources alone. When that happens, it goes through a separate PDF extractor with page-number citations and a manual check of the extracted text.

**Why:** PDF text extraction is lossy (tables, columns, headers and footnotes can be scrambled), and in this domain a scrambled exception is worse than a missing one. Building it before we know which PDFs matter spends effort without evidence.

**Alternatives:**
- *Build PDF extraction now:* covers more, but adds an untested and error-prone path before the HTML pipeline has been inspected on real pages.
- *Ignore PDFs entirely:* risks missing rules that exist only in a PDF, such as the Irish programme criteria and some university fee schedules.

**Trade-offs:** Some answers will say "not sure, check X" where a PDF holds the rule. Status: **accepted** (2026-11-21); see docs/DESIGN.md section 6.

---

## ADR-022: A university catalog with a coverage ladder (amends ADR-020)

**Decision (accepted 2026-11-21):** Keep a catalog of all target universities (US ranked by international students, all Irish higher-education institutions) with a coverage level per university: listed, registered, curated. Every catalog entry appears in the intake picker. Only registered and curated universities get answers; others get a "not covered yet" reply. Universities move up the ladder in waves, largest international enrolment first, and the pilot (1 to 2) is curated first.

**Why:** The founder wants all universities covered. Curating hundreds of schools' fee, insurance and payment-plan rules by hand would take longer than the whole v0.1 and push the freshness problem out. A ladder gives users an honest answer for every school on day one and lets coverage grow without a rewrite.

**Alternatives:**
- *Curate all before release:* complete, but v0.1 would not ship.
- *Pilot only, no catalog:* simplest, but ignores the stated goal.

**Trade-offs:** Uncovered schools get a weaker answer. Registered-level sources are not hand-inspected, so they carry a lower-confidence label until promoted. Status: **accepted** (2026-11-21); see docs/UNIVERSITY_CATALOG.md.

---

## ADR-023: Pages the fetcher cannot read are captured by hand, with provenance

**Decision (accepted 2026-11-21):** When an official page refuses automated requests (HTTP 403) or is built by JavaScript, a person saves it from their own browser into `data/inbox/<source id>.html` and runs `dishaa-manual`. The file is checked (block-page text, too few words), copied next to the fetched pages, and recorded in `manual_manifest.json` with its hash and capture time. The fetcher keeps its honest user agent and obeys robots.txt; it does not pose as a browser to get past a block.

**Why:** The first real run (2026-11-21) returned 403 for all 14 UCD pages and 5 State Department pages, and left some JavaScript-built pages almost empty. Those include the UCD non-EU fee pages that eval case F01 needs. A person reading a public page in a browser is ordinary use, and the page date and hash are still recorded, so the freshness pipeline works the same way.

**Alternatives:**
- *Disguise the fetcher as a browser:* gets past the block, but it ignores the site's wishes and breaks the rule that the system is honest about what it is.
- *Headless browser for JavaScript pages:* may be right later for pages that stay open to bots; heavy for 19 pages and does not fix a 403.
- *Ask each university for permission or a feed:* the right long-term route for the pilot schools; slow, so it runs alongside this one.

**Trade-offs:** Manual capture does not scale to hundreds of universities and goes stale silently unless someone re-saves it. The review queue (design decision 5) must treat manual pages as having a capture date and a reminder. Status: **accepted** (2026-11-21).

---

## ADR-024: Freshness checks run on a per-tier cadence, starting on GitHub Actions cron

**Decision (accepted 2026-11-21):** A scheduled job runs the existing fetch code on a per-tier cadence (core government every 3 days; core university weekly and daily in the 6 weeks before each term; supporting every 14 days), compares the cleaned-content hash (ADR-011), and reports changes to the review queue. It also checks that each page still holds its expected content (minimum word count; a table for fee pages). Pages that cannot be fetched (ADR-023) get a re-capture due date instead, and a stale-source alert fires when it passes. The job starts on GitHub Actions cron and moves to AWS EventBridge Scheduler once the deploy target is decided. See docs/DESIGN.md section 7.

**Why:** The first real run showed that a page can change while keeping its hash if the extractor drops the changed part, and that some pages cannot be fetched at all. A hash comparison alone would have reported both as "no change".

**Alternatives:**
- *EventBridge plus Fargate or Lambda now:* closer to production, but depends on the deploy decision and delays the first detected change.
- *cron on a small server:* simple, but a machine to patch and pay for.

**Trade-offs:** Cloud IP ranges are blocked more often than home connections, so more pages may need manual capture. State between runs needs a home before the production database exists. Cadences are starting values and are tuned from the change log.

---

## ADR-025: Source changes are reviewed as pull requests in a private corpus repository

**Decision (accepted 2026-11-21):** Each detected change to a source page becomes one pull request in a private repository (for example `dishaa-corpus`). The PR shows old and new cleaned text, a summary of what changed, the affected sources, pathways and steps, and the page's own date. CI runs the full eval set as a required check. Merging the PR is the approval and records who approved and when. Postgres holds the serving state (`pending`, `active`, `superseded`); a page with a pending core change is served with an "update pending review" warning. See docs/DESIGN.md section 8.

**Why:** A pull request already provides a diff view, an audit trail, required checks and notifications, so there is nothing to build or host. The eval gate (FR-31) becomes a CI check. It works for one reviewer (R16) and for more.

**Alternatives:**
- *Small admin web page:* one screen, but real work to build and secure, with a weaker audit trail.
- *Command line plus a Postgres table:* quick, but no diff view and easy to forget.

**Trade-offs:** Needs a second, private repository so that third-party page text is never published. Content lives in git while serving state lives in Postgres, so the two must stay in step. Slower than a button, which is acceptable for one reviewer and a few changes a week.

---

## ADR-026: Deploy on Lambda and API Gateway with Aurora Serverless v2, defined in Terraform

**Decision (accepted 2026-11-21):** The API runs as a container image on AWS Lambda behind an API Gateway HTTP API. The database is Aurora PostgreSQL Serverless v2 with auto-pause (minimum 0 ACUs) and pgvector 0.8 or newer. The web page makes a warm-up call on load so the database has resumed before the user finishes the intake questions. Infrastructure is defined in Terraform with state in S3 and `terraform plan` output posted on pull requests. GitHub Actions reaches AWS through OpenID Connect, with no long-lived keys. A hard monthly cost cap is enforced in the application (a counter of Bedrock calls checked before each call), alongside AWS Budgets alerts. Region is chosen after checking Bedrock model availability. See docs/DESIGN.md section 9.

**Why:** A portfolio demo gets few visitors, so an always-on load balancer and database are the main avoidable cost. Scale-to-zero removes it, and API Gateway provides the throttling needed for per-IP rate limits (FR-26). App Runner is closed to new customers since April 30, 2026.

**Alternatives:**
- *Lambda Function URL only:* simplest, but no throttling or custom-domain features.
- *ECS Express Mode with RDS:* steady latency, but always-on cost and more to patch.
- *App Runner:* closed to new customers.

**Trade-offs:** A paused database can take up to about 15 seconds to resume, handled by the warm-up call, connection retries and a "waking up" message. Lambda cold starts affect the first request after a quiet period. Prices are unverified. Open: region, per-IP limit mechanism behind API Gateway, one account or two.

---

## ADR-027: Evaluate with our own two-layer harness: rule checks and a calibrated judge

**Decision (accepted 2026-11-21):** Build a small eval harness in our own Python code and run it from pytest and CI. Layer 1 is rule checks with no model: retrieval hit, refusal accuracy, cross-country contamination, citation validity and exception traps (required facts present, general rule not stated alone). It runs on every pull request. Layer 2 is a judge model scoring correctness and faithfulness, from a different model family or tier than the generator, run on release candidates and model changes. The judge is calibrated first against 20 hand-labelled cases. Run reports are JSON files committed with the change. Amazon Bedrock Evaluations is used once, as an independent cross-check during the model bake-off. See docs/DESIGN.md section 10.

**Why:** Four of the six gates in the Eval Plan are rules, and the exception-trap gate is 100%. Code is deterministic and cheap, while a judge can be lenient. A case without an official source passage for its expected facts does not count toward any gate (R18).

**Alternatives:**
- *Bedrock Evaluations only:* judge metrics but no rule checks, and it runs as jobs, which is awkward for a per-PR check.
- *promptfoo, Ragas or DeepEval:* ready-made, but generic metrics, another dependency, and the exception gate would still need our own assertions.

**Trade-offs:** We write and maintain the harness, and the judge prompt needs calibration. The harness cannot run meaningfully until the 15 unfinished seed rows and 17 drafted cases are reviewed and the missing UCD fee tables are fixed.

---

## ADR-028: Observe with CloudWatch and one structured log line per request; raw question text is logged

**Decision (accepted 2026-11-21):** Use CloudWatch for logs, metrics, alarms and a dashboard, defined in Terraform. Every request writes one structured log line (request id, pathway and step, pinned model IDs, per-stage latency, tokens and cost, retrieved chunk ids and versions, outcome and refusal reason, citation-validity result). Grafana is a later stretch over the same data. By founder decision the **raw question text is logged** and the PII layer is deferred. Origin country is not logged as a field. Free defaults: encryption at rest, founder-only access, 30-day retention. Release gate (R19): no public launch until a PII layer exists (redact before write, with a leak test) or raw logging is off, and a privacy notice says what is kept. See docs/DESIGN.md section 11.

**Why:** The data comes first and dashboards are a view over it. Real questions are the best source of new eval cases.

**Alternatives:**
- *Redact first, then log:* safer, but the founder chose to defer it.
- *Langfuse or a vendor stack:* nicer traces, but another service to run. Langfuse stays a candidate to add later for trace review and eval-case mining (revised 2026-11-26); traces carry raw question text, so Cloud waits for the PII layer or it is self-hosted. A vendor stack is out of proportion to a demo.

**Trade-offs:** Logs can hold personal details until the PII layer exists, so the release gate is binding. Prices for CloudWatch and Bedrock are unverified.

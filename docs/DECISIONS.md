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

## Open decisions

- **Embedding model and its dimension.** The schema uses `vector(1024)` as a placeholder. Changing it later requires a migration and re-embedding everything, so we will confirm the model before loading real data.
- **Chunking strategy** (size, overlap, heading-based splits). To be decided by experiment with the eval set.
- **LLM and embedding provider access** (Bedrock model choices, regions, cost caps).

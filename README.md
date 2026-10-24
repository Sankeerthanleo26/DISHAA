# DISHAA

*Dishaa* means "direction" in Sanskrit. It is a retrieval-augmented assistant that answers visa and immigration questions using only official sources, with citations. Version 1 covers student visas for Ireland.

Docs: [Proposal](docs/PROPOSAL.md) · [PRD](docs/PRD.md) · [Scope](docs/SCOPE.md) · [Decisions](docs/DECISIONS.md)

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d db      # Postgres 16 with pgvector
dishaa-migrate               # create the schema
dishaa-fetch                 # download the curated Irish source pages to data/raw/ie/
pytest
```

`dishaa-fetch` reads `sources/ie_student.toml`, obeys each site's robots.txt, waits between requests, and saves the raw pages plus a `manifest.json`. It prints one line per page: `ok`, `blocked_by_robots`, `robots_unreadable` or `error`.

## Status

Week 1 in progress: foundation (layout, database, migrations) and the fetcher are done. Next: clean the raw pages and split them into chunks.

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
pytest
```

## Status

Week 1 in progress: foundation done (layout, database, migrations). Next: scraper and chunker for Irish sources.

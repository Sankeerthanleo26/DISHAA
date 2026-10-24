"""Load and validate the curated list of source pages from a TOML file."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

VALID_TIERS = {"core", "supporting"}


@dataclass(frozen=True)
class Source:
    id: str
    url: str
    title: str
    country: str
    visa_category: str
    tier: str


def load_sources(path: str | Path) -> list[Source]:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    defaults = data.get("defaults", {})
    sources: list[Source] = []
    seen: set[str] = set()
    for i, entry in enumerate(data.get("source", []), start=1):
        merged = {**defaults, **entry}
        missing = {"id", "url", "title", "country", "visa_category", "tier"} - merged.keys()
        if missing:
            raise ValueError(f"source #{i} is missing {sorted(missing)}")
        source = Source(**{k: merged[k] for k in Source.__dataclass_fields__})
        if source.id in seen:
            raise ValueError(f"duplicate source id: {source.id}")
        if urlsplit(source.url).scheme != "https":
            raise ValueError(f"source {source.id} must use https: {source.url}")
        if source.tier not in VALID_TIERS:
            raise ValueError(f"source {source.id} has invalid tier: {source.tier}")
        seen.add(source.id)
        sources.append(source)
    return sources

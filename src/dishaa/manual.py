"""Bring in pages that a person saved from their own browser (ADR-023).

Some official sites refuse automated requests (HTTP 403) or build the page with JavaScript, so
dishaa-fetch cannot read them. A person can still open them, so the route is: save the page in a
browser, drop the file in the inbox folder named <source id>.html, then run dishaa-manual.

Reads   data/inbox/<source id>.html
Writes  data/raw/<country>/<source id>.html            (same place dishaa-fetch writes)
        data/raw/<country>/manual_manifest.json        (who/when/what, kept apart from fetch's
                                                        manifest.json, which dishaa-fetch rewrites)
"""

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from dishaa.extract import extract_document
from dishaa.sources import Source, load_sources

MIN_WORDS = 150  # fewer words than this and the saved file is probably not the real page
BLOCK_PAGE_MARKERS = (
    "access denied", "forbidden", "just a moment", "verify you are human", "request blocked",
    "attention required",
)  # fmt: skip


@dataclass
class ManualResult:
    id: str
    url: str
    country: str
    status: str  # "saved", "suspect" or "unchanged"
    words: int = 0
    note: str = ""
    sha256: str = ""
    saved_at: str = ""


def _check(html: bytes, source: Source, min_words: int) -> tuple[int, str]:
    """Return (word count, problem). An empty problem means the file looks like a real page."""
    doc = extract_document(html, source)
    words = doc.word_count
    head = (doc.page_title + " " + " ".join(b.text for b in doc.blocks[:3])).lower()
    for marker in BLOCK_PAGE_MARKERS:
        if marker in head and words < 400:
            return words, f"looks like a block page ('{marker}')"
    if words < min_words:
        return words, f"only {words} words: saved before the page finished loading?"
    return words, ""


def ingest(
    sources: list[Source], inbox: Path, raw_dir: Path, min_words: int = MIN_WORDS
) -> tuple[list[ManualResult], list[str]]:
    """Copy inbox files into the raw folder. Returns (results, inbox files with no matching id)."""
    by_id = {s.id: s for s in sources}
    results: list[ManualResult] = []
    unknown: list[str] = []
    for path in sorted(inbox.glob("*.htm*")) if inbox.exists() else []:
        source = by_id.get(path.stem)
        if source is None:
            unknown.append(path.name)
            continue
        html = path.read_bytes()
        words, problem = _check(html, source, min_words)
        digest = hashlib.sha256(html).hexdigest()
        result = ManualResult(
            id=source.id, url=source.url, country=source.country, status="saved",
            words=words, sha256=digest, saved_at=datetime.now(UTC).isoformat(),
        )  # fmt: skip
        if problem:
            result.status, result.note = "suspect", problem  # not copied: it would pollute the data
            results.append(result)
            continue
        target = raw_dir / source.country.lower() / f"{source.id}.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
            result.status = "unchanged"
        else:
            target.write_bytes(html)
        results.append(result)
    _write_manifests(results, raw_dir)
    return results, unknown


def _write_manifests(results: list[ManualResult], raw_dir: Path) -> None:
    by_country: dict[str, dict[str, dict]] = {}
    for r in results:
        if r.status == "suspect":
            continue
        by_country.setdefault(r.country, {})[r.id] = {**asdict(r), "capture": "manual"}
    for country, items in by_country.items():
        path = raw_dir / country.lower() / "manual_manifest.json"
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        existing.update(items)  # keep earlier captures of other pages
        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def missing_pages(sources: list[Source], raw_dir: Path) -> list[Source]:
    """Sources that have no saved page yet, from either dishaa-fetch or dishaa-manual."""
    return [
        s for s in sources
        if not (raw_dir / s.country.lower() / f"{s.id}.html").exists()
        and not (raw_dir / s.country.lower() / f"{s.id}.pdf").exists()
    ]  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bring in pages saved from a browser, and list the pages still missing."
    )
    parser.add_argument("--sources", nargs="+", default=["sources/ie_student.toml"])
    parser.add_argument("--inbox", default="data/inbox")
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument(
        "--min-words",
        type=int,
        default=MIN_WORDS,
        help="lower this for a page that is short on purpose",
    )
    args = parser.parse_args(argv)

    sources = [s for path in args.sources for s in load_sources(path)]
    raw_dir = Path(args.raw)
    results, unknown = ingest(sources, Path(args.inbox), raw_dir, args.min_words)

    for r in results:
        print(f"{r.status:<10} {r.id:<36} {r.words:>6} words  {r.note}")
    for name in unknown:
        print(f"ignored    {name}: no source has this id (the file name must be <id>.html)")

    todo = missing_pages(sources, raw_dir)
    print(f"\n{len(sources) - len(todo)} of {len(sources)} pages have content; {len(todo)} missing")
    if todo:
        print(f"Save each page from your browser into {args.inbox}/ with this file name:")
        for s in todo:
            print(f"  {s.id}.html   <-  {s.url}")
    return 0 if not todo and not any(r.status == "suspect" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

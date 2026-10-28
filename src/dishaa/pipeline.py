"""Run extraction and chunking over every source and report what came out.

Reads   data/raw/<country>/<id>.html        (saved by dishaa-fetch)
Writes  data/clean/<country>/<id>.json      (cleaned, structured page)
        data/chunks/<country>/<id>.jsonl    (one chunk per line)
"""

import argparse
import json
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dishaa.chunk import Chunk, ChunkConfig, chunk_document
from dishaa.extract import extract_document
from dishaa.sources import Source, load_sources

MIN_WORDS = 150  # fewer words than this on a page is suspicious


@dataclass
class Report:
    source_id: str
    status: str  # "ok", "missing_raw" or "unsupported_pdf"
    words: int = 0
    headings: int = 0
    chunks: int = 0
    min_tokens: int = 0
    median_tokens: int = 0
    max_tokens: int = 0
    root: str = ""
    warnings: list[str] = field(default_factory=list)


def process_source(
    source: Source, raw_dir: Path, clean_dir: Path, chunk_dir: Path, config: ChunkConfig
) -> tuple[Report, list[Chunk]]:
    country = source.country.lower()
    html_path = raw_dir / country / f"{source.id}.html"
    if not html_path.exists():
        pdf_exists = (raw_dir / country / f"{source.id}.pdf").exists()
        return Report(source.id, "unsupported_pdf" if pdf_exists else "missing_raw"), []

    doc = extract_document(html_path.read_bytes(), source)
    chunks = chunk_document(doc, config)

    (clean_dir / country).mkdir(parents=True, exist_ok=True)
    (clean_dir / country / f"{source.id}.json").write_text(
        json.dumps(doc.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (chunk_dir / country).mkdir(parents=True, exist_ok=True)
    (chunk_dir / country / f"{source.id}.jsonl").write_text(
        "".join(json.dumps(asdict(c), ensure_ascii=False) + "\n" for c in chunks),
        encoding="utf-8",
    )

    report = Report(
        source.id,
        "ok",
        words=doc.word_count,
        headings=doc.heading_count,
        chunks=len(chunks),
        root=doc.root_selector,
    )
    if chunks:
        sizes = [c.token_count for c in chunks]
        report.min_tokens, report.max_tokens = min(sizes), max(sizes)
        report.median_tokens = int(statistics.median(sizes))
    if doc.word_count < MIN_WORDS:
        report.warnings.append(
            "very little text: page may be empty, blocked or built by JavaScript"
        )
    if doc.heading_count == 0:
        report.warnings.append("no headings: chunks are size-based only")
    if doc.root_selector == "body":
        report.warnings.append(
            "no <main>/<article> found: whole body used, check for leftover menus"
        )
    return report, chunks


def _print_chunks(chunks: list[Chunk]) -> None:
    for chunk in chunks:
        path = " > ".join(chunk.heading_path) or "(top of page)"
        print(f"\n--- {chunk.chunk_id}  [{chunk.token_count} tokens]  {path}")
        print(chunk.text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Clean the fetched pages and split them into chunks."
    )
    parser.add_argument("--sources", default="sources/ie_student.toml")
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--clean", default="data/clean")
    parser.add_argument("--chunks", default="data/chunks")
    parser.add_argument("--max-tokens", type=int, default=ChunkConfig.max_tokens)
    parser.add_argument("--min-tokens", type=int, default=ChunkConfig.min_tokens)
    parser.add_argument("--overlap-tokens", type=int, default=ChunkConfig.overlap_tokens)
    parser.add_argument("--show", metavar="SOURCE_ID", help="print the chunks of one page")
    args = parser.parse_args(argv)

    config = ChunkConfig(args.max_tokens, args.min_tokens, args.overlap_tokens)
    reports: list[Report] = []
    shown: list[Chunk] = []
    for source in load_sources(args.sources):
        report, chunks = process_source(
            source, Path(args.raw), Path(args.clean), Path(args.chunks), config
        )
        reports.append(report)
        if source.id == args.show:
            shown = chunks

    print(
        f"{'page':<34}{'status':<10}{'words':>6}{'heads':>6}{'chunks':>7}{'tokens min/med/max':>22}  root"
    )
    for r in reports:
        sizes = f"{r.min_tokens}/{r.median_tokens}/{r.max_tokens}" if r.chunks else "-"
        print(
            f"{r.source_id:<34}{r.status:<10}{r.words:>6}{r.headings:>6}{r.chunks:>7}{sizes:>22}  {r.root}"
        )
        for warning in r.warnings:
            print(f"    warning: {warning}")
    ok = [r for r in reports if r.status == "ok" and r.chunks]
    print(f"\n{len(ok)} of {len(reports)} pages produced {sum(r.chunks for r in ok)} chunks")

    if args.show:
        _print_chunks(shown)
    return 0 if len(ok) == len(reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())

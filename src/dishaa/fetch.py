"""Polite page fetcher.

For each source URL it:
  1. checks the site's robots.txt and skips pages we are not allowed to fetch,
  2. waits between requests (rate limiting),
  3. downloads the page and saves the untouched bytes,
  4. records what happened in a manifest.json next to the saved files.

Cleaning and chunking happen later, from these saved raw files.
"""

import argparse
import hashlib
import json
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from dishaa.config import get_settings
from dishaa.sources import Source, load_sources


@dataclass
class FetchResult:
    id: str
    url: str
    country: str
    status: str  # "ok", "blocked_by_robots", "robots_unreadable" or "error"
    http_status: int | None = None
    final_url: str | None = None
    content_type: str | None = None
    bytes: int | None = None
    sha256: str | None = None
    path: str | None = None
    fetched_at: str | None = None
    error: str | None = None


class RobotsPolicy:
    """Answers "may we fetch this URL?" using each site's robots.txt, fetched once per site."""

    def __init__(self, client: httpx.Client, user_agent: str):
        self._client = client
        self._user_agent = user_agent
        self._rules: dict[str, tuple[RobotFileParser, bool]] = {}

    def decision(self, url: str) -> str:
        """Return "allowed", "blocked_by_robots" (the site says no) or "robots_unreadable"
        (we could not read the rules, so we play it safe and do not fetch)."""
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._rules:
            self._rules[origin] = self._load(origin)
        parser, readable = self._rules[origin]
        if not readable:
            return "robots_unreadable"
        return "allowed" if parser.can_fetch(self._user_agent, url) else "blocked_by_robots"

    def _load(self, origin: str) -> tuple[RobotFileParser, bool]:
        parser = RobotFileParser()
        try:
            response = self._client.get(f"{origin}/robots.txt")
        except httpx.HTTPError:
            return parser, False  # network trouble: cannot read the rules
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
            parser.modified()  # the standard library refuses to answer unless this is set
            return parser, True
        if 400 <= response.status_code < 500:
            parser.allow_all = True  # no robots.txt means no restrictions
            return parser, True
        return parser, False  # server trouble (5xx): cannot read the rules


def _extension(content_type: str | None) -> str:
    return ".pdf" if content_type and "pdf" in content_type.lower() else ".html"


def fetch_sources(
    sources: list[Source],
    out_dir: Path,
    client: httpx.Client,
    user_agent: str,
    delay_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
) -> list[FetchResult]:
    robots = RobotsPolicy(client, user_agent)
    results: list[FetchResult] = []
    made_request = False

    for source in sources:
        result = FetchResult(id=source.id, url=source.url, country=source.country, status="error")

        decision = robots.decision(source.url)
        if decision != "allowed":
            result.status = decision
            results.append(result)
            continue

        if made_request:
            sleep(delay_seconds)
        made_request = True

        try:
            response = client.get(source.url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            result.http_status = exc.response.status_code
            result.error = f"HTTP {exc.response.status_code}"
            results.append(result)
            continue
        except httpx.HTTPError as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            results.append(result)
            continue

        content_type = response.headers.get("content-type")
        target = out_dir / source.country.lower() / f"{source.id}{_extension(content_type)}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)

        result.status = "ok"
        result.http_status = response.status_code
        result.final_url = str(response.url)
        result.content_type = content_type
        result.bytes = len(response.content)
        result.sha256 = hashlib.sha256(response.content).hexdigest()
        result.path = str(target)
        result.fetched_at = datetime.now(UTC).isoformat()
        results.append(result)

    _write_manifests(results, out_dir)
    return results


def _write_manifests(results: list[FetchResult], out_dir: Path) -> None:
    by_country: dict[str, list[FetchResult]] = defaultdict(list)
    for result in results:
        by_country[result.country].append(result)
    for country, items in by_country.items():
        folder = out_dir / country.lower()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "manifest.json").write_text(
            json.dumps([asdict(r) for r in items], indent=2), encoding="utf-8"
        )


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Fetch the curated source pages politely.")
    parser.add_argument("--sources", default="sources/ie_student.toml")
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--delay", type=float, default=settings.request_delay_seconds)
    args = parser.parse_args(argv)

    sources = load_sources(args.sources)
    with httpx.Client(
        headers={"User-Agent": settings.user_agent},
        timeout=settings.request_timeout_seconds,
        follow_redirects=True,
    ) as client:
        results = fetch_sources(sources, Path(args.out), client, settings.user_agent, args.delay)

    for r in results:
        detail = r.error or (f"{r.bytes} bytes" if r.bytes is not None else "")
        print(f"{r.status:<18} {r.id:<32} {detail}")
    problems = [r for r in results if r.status != "ok"]
    print(f"\n{len(results) - len(problems)} of {len(results)} pages saved to {args.out}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

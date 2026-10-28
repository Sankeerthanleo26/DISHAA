import json
from pathlib import Path

import httpx

from dishaa.fetch import fetch_sources
from dishaa.sources import Source

UA = "Dishaa/0.1 (test)"


def make_sources(*paths: str) -> list[Source]:
    return [
        Source(
            id=p.strip("/").replace("/", "-") or "root",
            url=f"https://site.test{p}",
            title=p,
            country="IE",
            visa_category="student",
            tier="core",
        )
        for p in paths
    ]


def run(handler, sources, tmp_path: Path, delay: float = 2.0):
    sleeps: list[float] = []
    requested: list[str] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return handler(request)

    with httpx.Client(
        transport=httpx.MockTransport(recording_handler), headers={"User-Agent": UA}
    ) as client:
        results = fetch_sources(sources, tmp_path, client, UA, delay, sleep=sleeps.append)
    return results, sleeps, requested


def html_ok(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(404)
    return httpx.Response(
        200, text=f"<html>{request.url.path}</html>", headers={"content-type": "text/html"}
    )


def test_saves_raw_files_and_manifest(tmp_path: Path):
    results, _, _ = run(html_ok, make_sources("/a", "/b"), tmp_path)
    assert [r.status for r in results] == ["ok", "ok"]
    saved = tmp_path / "ie" / "a.html"
    assert saved.read_text() == "<html>/a</html>"
    manifest = json.loads((tmp_path / "ie" / "manifest.json").read_text())
    assert [m["id"] for m in manifest] == ["a", "b"]
    assert len(manifest[0]["sha256"]) == 64
    assert manifest[0]["fetched_at"]


def test_waits_between_requests_but_not_before_the_first(tmp_path: Path):
    _, sleeps, _ = run(html_ok, make_sources("/a", "/b", "/c"), tmp_path, delay=1.5)
    assert sleeps == [1.5, 1.5]


def test_robots_disallow_means_page_is_never_requested(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
        return html_ok(request)

    results, sleeps, requested = run(handler, make_sources("/private/x", "/open"), tmp_path)
    assert [r.status for r in results] == ["blocked_by_robots", "ok"]
    assert "/private/x" not in requested
    assert sleeps == []  # skipped pages cause no waiting


def test_robots_rule_for_our_user_agent_is_obeyed(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: Dishaa\nDisallow: /\n")
        return html_ok(request)

    results, _, requested = run(handler, make_sources("/a"), tmp_path)
    assert results[0].status == "blocked_by_robots"
    assert requested == ["/robots.txt"]


def test_missing_robots_txt_allows_everything(tmp_path: Path):
    results, _, _ = run(html_ok, make_sources("/a"), tmp_path)
    assert results[0].status == "ok"


def test_robots_server_error_is_treated_cautiously(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(503)
        return html_ok(request)

    results, _, requested = run(handler, make_sources("/a"), tmp_path)
    assert results[0].status == "robots_unreadable"
    assert requested == ["/robots.txt"]


def test_robots_network_failure_is_reported_as_unreadable_not_blocked(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    results, _, _ = run(handler, make_sources("/a", "/b"), tmp_path)
    assert [r.status for r in results] == ["robots_unreadable", "robots_unreadable"]


def test_robots_txt_is_fetched_once_per_site(tmp_path: Path):
    _, _, requested = run(html_ok, make_sources("/a", "/b", "/c"), tmp_path)
    assert requested.count("/robots.txt") == 1


def test_http_errors_are_recorded_and_do_not_stop_the_run(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/missing":
            return httpx.Response(404)
        return html_ok(request)

    results, _, _ = run(handler, make_sources("/missing", "/fine"), tmp_path)
    assert [r.status for r in results] == ["error", "ok"]
    assert results[0].http_status == 404
    assert not (tmp_path / "ie" / "missing.html").exists()


def test_network_errors_are_recorded(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        raise httpx.ConnectError("boom")

    results, _, _ = run(handler, make_sources("/a"), tmp_path)
    assert results[0].status == "error"
    assert "ConnectError" in results[0].error


def test_pdf_content_type_gets_pdf_extension(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=b"%PDF-1.4", headers={"content-type": "application/pdf"})

    results, _, _ = run(handler, make_sources("/doc"), tmp_path)
    assert results[0].path.endswith("doc.pdf")

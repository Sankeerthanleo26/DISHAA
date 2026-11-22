import json

from dishaa.manual import ingest, missing_pages
from dishaa.sources import Source

SRC = Source("fees", "https://example.test/fees/", "Fees", "IE", "student", "core")
OTHER = Source("deposit", "https://example.test/deposit/", "Deposit", "IE", "student", "core")

WORDS = " ".join(f"word{i}" for i in range(200))
GOOD = f"<html><body><main><h1>Fees</h1><p>{WORDS}</p></main></body></html>"
BLOCKED = "<html><head><title>Access Denied</title></head><body><main><h1>Access Denied</h1><p>No.</p></main></body></html>"


def put(inbox, name, html):
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / name).write_text(html, encoding="utf-8")


def test_good_page_is_copied_and_recorded(tmp_path):
    put(tmp_path / "inbox", "fees.html", GOOD)
    results, unknown = ingest([SRC, OTHER], tmp_path / "inbox", tmp_path / "raw")
    assert [r.status for r in results] == ["saved"] and unknown == []
    assert (tmp_path / "raw" / "ie" / "fees.html").read_text(encoding="utf-8") == GOOD
    manifest = json.loads((tmp_path / "raw" / "ie" / "manual_manifest.json").read_text())
    assert manifest["fees"]["capture"] == "manual" and manifest["fees"]["sha256"]


def test_block_page_and_thin_page_are_not_copied(tmp_path):
    put(tmp_path / "inbox", "fees.html", BLOCKED)
    results, _ = ingest([SRC], tmp_path / "inbox", tmp_path / "raw")
    assert results[0].status == "suspect" and "block page" in results[0].note
    assert not (tmp_path / "raw" / "ie" / "fees.html").exists()
    put(
        tmp_path / "inbox",
        "fees.html",
        "<html><body><main><h1>Fees</h1><p>Short.</p></main></body></html>",
    )
    results, _ = ingest([SRC], tmp_path / "inbox", tmp_path / "raw")
    assert results[0].status == "suspect" and "words" in results[0].note
    results, _ = ingest([SRC], tmp_path / "inbox", tmp_path / "raw", min_words=1)
    assert results[0].status == "saved"


def test_unknown_names_are_reported_and_second_run_is_unchanged(tmp_path):
    put(tmp_path / "inbox", "fees.html", GOOD)
    put(tmp_path / "inbox", "typo.html", GOOD)
    results, unknown = ingest([SRC], tmp_path / "inbox", tmp_path / "raw")
    assert unknown == ["typo.html"]
    results, _ = ingest([SRC], tmp_path / "inbox", tmp_path / "raw")
    assert results[0].status == "unchanged"


def test_missing_pages_lists_sources_without_content(tmp_path):
    put(tmp_path / "inbox", "fees.html", GOOD)
    ingest([SRC, OTHER], tmp_path / "inbox", tmp_path / "raw")
    assert [s.id for s in missing_pages([SRC, OTHER], tmp_path / "raw")] == ["deposit"]

import json
import shutil
from pathlib import Path

from dishaa.pipeline import main

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_gov_page.html"

SOURCES = """
[defaults]
country = "IE"
visa_category = "student"
tier = "core"

[[source]]
id = "working"
title = "Working while studying"
url = "https://example.test/working/"

[[source]]
id = "absent"
title = "Never downloaded"
url = "https://example.test/absent/"
"""


def setup(tmp_path: Path, with_absent: bool = True) -> list[str]:
    raw = tmp_path / "raw" / "ie"
    raw.mkdir(parents=True)
    shutil.copy(FIXTURE, raw / "working.html")
    sources = tmp_path / "sources.toml"
    text = SOURCES if with_absent else SOURCES.split('[[source]]\nid = "absent"')[0]
    sources.write_text(text)
    return [
        "--sources", str(sources),
        "--raw", str(tmp_path / "raw"),
        "--clean", str(tmp_path / "clean"),
        "--chunks", str(tmp_path / "chunks"),
    ]  # fmt: skip


def test_writes_clean_json_and_chunk_files(tmp_path, capsys):
    code = main(setup(tmp_path, with_absent=False))
    assert code == 0

    clean = json.loads((tmp_path / "clean" / "ie" / "working.json").read_text())
    assert clean["source_id"] == "working"
    assert clean["root_selector"] == "main"
    assert len(clean["content_hash"]) == 64

    lines = (tmp_path / "chunks" / "ie" / "working.jsonl").read_text().splitlines()
    chunks = [json.loads(line) for line in lines]
    assert chunks and chunks[0]["chunk_id"] == "working:0000"
    assert all(c["country"] == "IE" and c["token_count"] > 0 for c in chunks)
    assert "1 of 1 pages produced" in capsys.readouterr().out


def test_missing_raw_file_is_reported_and_gives_a_nonzero_exit_code(tmp_path, capsys):
    code = main(setup(tmp_path))
    out = capsys.readouterr().out
    assert code == 1
    assert "absent" in out and "missing_raw" in out
    assert (tmp_path / "chunks" / "ie" / "working.jsonl").exists()  # the good page still ran


def test_show_prints_the_chunks_of_one_page(tmp_path, capsys):
    main([*setup(tmp_path, with_absent=False), "--show", "working"])
    out = capsys.readouterr().out
    assert "--- working:0000" in out
    assert "Keep payslips for every job." in out


def test_short_pages_get_a_warning(tmp_path, capsys):
    args = setup(tmp_path, with_absent=False)
    short_page = "<html><body><main><h2>Rules</h2><p>" + "A short sentence of text. " * 10
    (tmp_path / "raw" / "ie" / "working.html").write_text(short_page + "</p></main></body></html>")
    main(args)
    assert "very little text" in capsys.readouterr().out


def test_a_normal_length_page_gets_no_warning(tmp_path, capsys):
    main(setup(tmp_path, with_absent=False))
    assert "warning" not in capsys.readouterr().out

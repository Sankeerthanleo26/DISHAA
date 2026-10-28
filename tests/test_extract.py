from pathlib import Path

import pytest

from dishaa.extract import extract_document, normalise
from dishaa.sources import Source

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_gov_page.html"

SOURCE = Source(
    id="working",
    url="https://example.test/working/",
    title="Working while studying",
    country="IE",
    visa_category="student",
    tier="core",
)


@pytest.fixture(scope="module")
def html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def doc(html):
    return extract_document(html, SOURCE)


def all_text(doc) -> str:
    return "\n".join(b.text for b in doc.blocks)


def test_page_furniture_is_removed(doc):
    text = all_text(doc)
    for junk in [
        "Accept cookies", "Skip to content", "menu entry", "Search the site", "Privacy policy",
        "Contact us", "Last rebuilt", "Related links", "Unrelated sidebar", "Share this page",
        "Print this page", "analytics", "Home",
    ]:  # fmt: skip
        assert junk not in text, junk


def test_real_content_is_kept(doc):
    text = all_text(doc)
    for wanted in [
        "Students on an approved course may work part-time",
        "Keep payslips for every job.",
        "Self-employment is not allowed",
        "unpaid volunteering is allowed",
    ]:
        assert wanted in text


def test_root_and_titles(doc):
    assert doc.root_selector == "main"
    assert doc.page_title == "Working while studying"
    assert doc.title == "Working while studying"
    assert doc.blocks[0].kind != "heading" or doc.blocks[0].level != 1  # h1 became the page title


def test_headings_keep_their_levels_in_order(doc):
    headings = [(b.level, b.text) for b in doc.blocks if b.kind == "heading"]
    assert headings == [
        (2, "Term time"),
        (2, "Holiday periods"),
        (2, "Frequently asked questions"),
        (3, "Can I be self-employed?"),
        (3, "Can I volunteer?"),
        (2, "More questions"),
        (3, "What happens if I break the rules?"),  # <summary> ranks one level below the last h2
    ]


def test_hidden_accordion_answers_are_kept(doc):
    assert "Your permission may be withdrawn" in all_text(doc)


def test_lists_become_list_items_including_nested_ones(doc):
    items = [b.text for b in doc.blocks if b.kind == "list_item"]
    assert items == [
        "Keep payslips for every job.",
        "Tell the college if your hours change.",
        "Changes must be reported within a month.",
    ]


def test_table_rows_are_written_so_each_row_stands_alone(doc):
    rows = [b.text for b in doc.blocks if b.kind == "table_row"]
    assert rows == [
        "Course type: Example Level 8 course; Hours per week: 12; Period: Term time",
        "Course type: Example Level 9 course; Hours per week: 34; Period: Holidays",
    ]


def test_whitespace_and_punctuation_are_tidied(doc):
    intro = doc.blocks[0].text
    assert "\u00a0" not in intro
    assert "  " not in intro
    assert "registration card. Rules" in intro  # no stray space before the full stop
    assert "term time, and" in intro  # no stray space before the comma
    assert "term time\nand" not in intro


def test_invisible_characters_are_removed_and_punctuation_tidied():
    messy = "a" + chr(0x200B) + "b" + chr(0xA0) + "c" + chr(0xFEFF) + "  d ,  (  e ) ."
    assert normalise(messy) == "ab c d, (e)."


def test_line_breaks_do_not_glue_words_together(doc):
    assert "weekly limit. Your employer" in all_text(doc)


def test_hash_ignores_page_furniture_but_notices_content_changes(html, doc):
    furniture_changed = (
        html.replace("2026-10-27T10:00:00Z", "2026-11-30T23:59:59Z")
        .replace("We use cookies.", "Cookies help us.")
        .replace("Study menu entry", "Study menu renamed")
    )
    assert extract_document(furniture_changed, SOURCE).content_hash == doc.content_hash

    content_changed = html.replace("up to a weekly limit", "up to a different limit")
    assert extract_document(content_changed, SOURCE).content_hash != doc.content_hash


def test_extraction_is_deterministic(html, doc):
    assert extract_document(html, SOURCE) == doc


def test_fallback_to_body_when_there_is_no_main_or_article():
    page = (
        "<html><head><title>Plain page - Site</title></head><body>"
        "<header><div>Site logo</div></header>"
        "<div class='wrapper'><h2>Rules</h2><p>" + "Useful sentence here. " * 15 + "</p></div>"
        "<footer>Footer text</footer></body></html>"
    )
    doc = extract_document(page, SOURCE)
    assert doc.root_selector == "body"
    text = all_text(doc)
    assert "Site logo" not in text and "Footer text" not in text
    assert "Useful sentence here." in text
    assert doc.page_title == "Plain page"  # taken from <title>, minus the site name


def test_bytes_input_is_accepted(html):
    assert extract_document(html.encode("utf-8"), SOURCE).word_count > 50


def test_empty_page_gives_an_empty_document():
    doc = extract_document("<html><body></body></html>", SOURCE)
    assert doc.blocks == []
    assert doc.word_count == 0

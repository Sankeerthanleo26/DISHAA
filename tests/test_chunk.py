from itertools import pairwise

import pytest

from dishaa.chunk import ChunkConfig, chunk_document, estimate_tokens
from dishaa.extract import Block, CleanDocument


def make_doc(*blocks: Block) -> CleanDocument:
    return CleanDocument(
        source_id="page",
        url="https://example.test/page/",
        country="IE",
        visa_category="student",
        tier="core",
        title="Example page",
        page_title="Example page",
        root_selector="main",
        content_hash="x",
        blocks=list(blocks),
    )


def h(level: int, text: str) -> Block:
    return Block("heading", text, level)


def p(text: str) -> Block:
    return Block("paragraph", text)


def words(n: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


SMALL = ChunkConfig(max_tokens=100, min_tokens=20, overlap_tokens=30)


def test_one_chunk_per_section_with_heading_path_and_ids():
    doc = make_doc(
        p("Intro text that is long enough to stand alone " + words(20, "i")),
        h(2, "Alpha"),
        p(words(40, "a")),
        h(3, "Alpha child"),
        p(words(40, "c")),
        h(2, "Beta"),
        p(words(40, "b")),
    )
    chunks = chunk_document(doc, ChunkConfig(max_tokens=200, min_tokens=10, overlap_tokens=20))
    assert [c.heading_path for c in chunks] == [[], ["Alpha"], ["Alpha", "Alpha child"], ["Beta"]]
    assert [c.chunk_id for c in chunks] == [f"page:{i:04d}" for i in range(4)]
    assert [c.chunk_index for c in chunks] == [0, 1, 2, 3]
    assert all(c.source_id == "page" and c.country == "IE" and c.tier == "core" for c in chunks)


def test_every_chunk_body_respects_the_size_limit():
    long_section = [p(words(60, f"p{i}x")) for i in range(12)]
    chunks = chunk_document(make_doc(h(2, "Big"), *long_section), SMALL)
    assert len(chunks) > 3
    assert all(c.token_count <= SMALL.max_tokens for c in chunks)


def test_no_content_is_lost():
    blocks = [h(2, "Big")] + [p(words(35, f"p{i}x")) for i in range(15)]
    chunks = chunk_document(make_doc(*blocks), SMALL)
    covered = set(" ".join(c.text for c in chunks).split())
    expected = {w for b in blocks if b.kind == "paragraph" for w in b.text.split()}
    assert expected <= covered


def test_split_sections_repeat_the_last_whole_unit_when_it_fits_the_overlap_budget():
    units = [p(words(25, f"u{i}x")) for i in range(8)]  # about 33 tokens each
    config = ChunkConfig(max_tokens=100, min_tokens=20, overlap_tokens=40)
    chunks = chunk_document(make_doc(h(2, "Long"), *units), config)
    assert len(chunks) >= 3
    for earlier, later in pairwise(chunks):
        last_unit_of_earlier = earlier.text.split("\n\n")[-1]
        assert later.text.startswith(
            last_unit_of_earlier
        )  # repeated at the start of the next chunk


def test_a_paragraph_too_big_to_repeat_whole_contributes_its_last_sentences():
    sentences = [f"Sentence {i:02d} has a handful of words in it." for i in range(12)]
    paragraphs = [
        p(" ".join(sentences[i * 4 : i * 4 + 4])) for i in range(3)
    ]  # about 60 tokens each
    config = ChunkConfig(max_tokens=100, min_tokens=20, overlap_tokens=30)
    chunks = chunk_document(make_doc(h(2, "Long"), *paragraphs), config)
    assert len(chunks) >= 2
    first, second = chunks[0], chunks[1]
    repeated = second.text.split("\n\n")[0]
    assert repeated and repeated in first.text  # something was repeated...
    assert estimate_tokens(repeated) <= config.overlap_tokens  # ...within the budget
    assert repeated.endswith(".") and repeated[0].isupper()  # ...as whole sentences
    assert len(repeated) < len(paragraphs[1].text)  # ...not the whole paragraph


def test_overlap_of_zero_means_no_repeated_text():
    units = [p(words(25, f"u{i}x")) for i in range(8)]
    config = ChunkConfig(max_tokens=100, min_tokens=20, overlap_tokens=0)
    chunks = chunk_document(make_doc(h(2, "Long"), *units), config)
    seen: set[str] = set()
    for c in chunks:
        for unit in c.text.split("\n\n"):
            assert unit not in seen
            seen.add(unit)


def test_tiny_sibling_sections_are_merged_and_keep_their_headings():
    doc = make_doc(
        h(2, "Parent"),
        h(3, "Q one"), p("Short answer one."),
        h(3, "Q two"), p("Short answer two."),
        h(3, "Q three"), p("Short answer three."),
    )  # fmt: skip
    chunks = chunk_document(doc, ChunkConfig(max_tokens=200, min_tokens=40, overlap_tokens=10))
    assert len(chunks) == 1
    assert chunks[0].heading_path == ["Parent"]
    assert chunks[0].text == (
        "Q one\nShort answer one.\n\nQ two\nShort answer two.\n\nQ three\nShort answer three."
    )


def test_small_sections_under_different_parents_are_not_merged():
    doc = make_doc(
        h(2, "First"), h(3, "A"), p("Tiny."),
        h(2, "Second"), h(3, "B"), p("Tiny too."),
    )  # fmt: skip
    chunks = chunk_document(doc, ChunkConfig(max_tokens=200, min_tokens=40, overlap_tokens=10))
    assert [c.heading_path for c in chunks] == [["First", "A"], ["Second", "B"]]


def test_merging_stops_before_exceeding_the_maximum():
    doc = make_doc(
        h(2, "Parent"),
        h(3, "One"), p(words(25, "a")),
        h(3, "Two"), p(words(25, "b")),
        h(3, "Three"), p(words(25, "c")),
    )  # fmt: skip
    config = ChunkConfig(max_tokens=70, min_tokens=60, overlap_tokens=10)
    chunks = chunk_document(doc, config)
    assert len(chunks) >= 2
    assert all(c.token_count <= 70 for c in chunks)


def test_a_long_paragraph_is_split_at_sentence_ends():
    sentences = [f"Sentence number {i} says something useful about the topic." for i in range(30)]
    chunks = chunk_document(make_doc(h(2, "Wall of text"), p(" ".join(sentences))), SMALL)
    assert len(chunks) > 2
    assert all(c.token_count <= SMALL.max_tokens for c in chunks)
    assert all(c.text.rstrip().endswith(".") for c in chunks)


def test_table_rows_are_never_cut_in_half():
    rows = [Block("table_row", f"Course: Example {i}; Hours: {i}; Period: Term") for i in range(40)]
    chunks = chunk_document(make_doc(h(2, "Table"), *rows), SMALL)
    assert len(chunks) > 1
    for c in chunks:
        for line in c.text.split("\n"):
            assert line.startswith("Course: Example") and line.endswith("Period: Term")


def test_list_items_are_rendered_as_bullets_on_separate_lines():
    doc = make_doc(
        h(2, "Steps"),
        p("Do these things:"),
        Block("list_item", "first"),
        Block("list_item", "second"),
    )
    (chunk,) = chunk_document(doc, ChunkConfig(max_tokens=100, min_tokens=0, overlap_tokens=0))
    assert chunk.text == "Do these things:\n\n- first\n- second"


def test_heading_with_no_text_of_its_own_creates_no_empty_chunk():
    doc = make_doc(h(2, "Parent"), h(3, "Child"), p(words(30, "c")))
    chunks = chunk_document(doc, SMALL)
    assert [c.heading_path for c in chunks] == [["Parent", "Child"]]


def test_embedding_text_carries_title_and_heading_path():
    doc = make_doc(h(2, "Term time"), h(3, "Limits"), p(words(30, "x")))
    (chunk,) = chunk_document(doc, SMALL)
    assert chunk.embedding_text.startswith("Example page > Term time > Limits\n\n")
    assert chunk.embedding_text.endswith(chunk.text)


def test_empty_document_has_no_chunks():
    assert chunk_document(make_doc(), SMALL) == []


def test_chunking_is_deterministic():
    doc = make_doc(h(2, "A"), *[p(words(30, f"p{i}x")) for i in range(9)])
    assert chunk_document(doc, SMALL) == chunk_document(doc, SMALL)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_tokens": 100, "overlap_tokens": 100},
        {"max_tokens": 100, "min_tokens": 100},
        {"max_tokens": 100, "overlap_tokens": -1},
    ],
)
def test_bad_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        ChunkConfig(**kwargs)


def test_token_estimate_is_conservative_and_handles_empty_text():
    assert estimate_tokens("") == 0
    assert estimate_tokens("one two three four") == 6  # 4 words x 1.3, rounded up
    assert estimate_tokens("x" * 400) == 100  # long words: the character rule wins

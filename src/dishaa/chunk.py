"""Split a cleaned document into chunks that are good units for search.

Strategy, in plain words:
  1. Cut the page into sections at its own headings (a section is a heading plus its text).
  2. A section that fits in the size limit becomes one chunk.
  3. A section that is too long is split at paragraph, list-item or table-row boundaries,
     and each new piece repeats the last few units of the previous one (overlap).
  4. A section that is very small is merged with its neighbouring sections under the same
     parent heading, so we do not end up with chunks that are one line long.
Nothing is ever dropped: every word of the cleaned page ends up in at least one chunk.
"""

import math
import re
from dataclasses import dataclass

from dishaa.extract import Block, CleanDocument

JOINED_KINDS = ("list_item", "table_row")  # consecutive units of these kinds sit on separate lines
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"\u201c(])")


def estimate_tokens(text: str) -> int:
    """A rough token count (accurate to about 20%), with no model or download needed.

    The embedding model is not chosen yet, and each model counts tokens its own way.
    We take the larger of two common rules of thumb so that chunks err on the small side.
    """
    if not text:
        return 0
    return max(math.ceil(len(text.split()) * 1.3), math.ceil(len(text) / 4))


@dataclass(frozen=True)
class ChunkConfig:
    max_tokens: int = 500  # a chunk's body never exceeds this
    min_tokens: int = 60  # sections smaller than this are merged with their siblings
    overlap_tokens: int = (
        60  # how much of the previous piece to repeat when splitting a long section
    )

    def __post_init__(self) -> None:
        if not 0 <= self.overlap_tokens < self.max_tokens:
            raise ValueError("overlap_tokens must be at least 0 and less than max_tokens")
        if not 0 <= self.min_tokens < self.max_tokens:
            raise ValueError("min_tokens must be at least 0 and less than max_tokens")


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    url: str
    country: str
    visa_category: str
    tier: str
    doc_title: str
    heading_path: list[str]  # the headings above this chunk, outermost first
    chunk_index: int
    text: str
    token_count: int

    @property
    def embedding_text(self) -> str:
        """What gets embedded: the text plus the page title and heading path, so that a chunk
        reading "20 hours per week" still carries "Working while studying" with it."""
        header = [self.doc_title]
        header += [h for h in self.heading_path if h != self.doc_title]
        return " > ".join(header) + "\n\n" + self.text


@dataclass(frozen=True)
class _Unit:
    kind: str
    text: str
    tokens: int


@dataclass
class _Section:
    path: tuple[str, ...]
    units: list[_Unit]


@dataclass
class _Piece:
    path: tuple[str, ...]  # heading path for the piece as a whole
    parts: list[tuple[str | None, list[_Unit]]]  # (own heading, units); several when merged
    whole: bool  # the piece is an entire section, so it may be merged with its neighbours
    parent: tuple[str, ...]  # path of the parent heading; only siblings merge

    @property
    def tokens(self) -> int:
        total = sum(u.tokens for _, units in self.parts for u in units)
        if len(self.parts) > 1:
            total += sum(estimate_tokens(h) for h, _ in self.parts if h)
        return total

    @property
    def text(self) -> str:
        if len(self.parts) == 1:
            return _join(self.parts[0][1])
        blocks = [f"{h}\n{_join(units)}" if h else _join(units) for h, units in self.parts]
        return "\n\n".join(blocks)


def _unit_text(block: Block) -> str:
    return f"- {block.text}" if block.kind == "list_item" else block.text


def _join(units: list[_Unit]) -> str:
    text = ""
    for i, unit in enumerate(units):
        if i:
            same_line_group = unit.kind in JOINED_KINDS and units[i - 1].kind == unit.kind
            text += "\n" if same_line_group else "\n\n"
        text += unit.text
    return text


def _sections(doc: CleanDocument) -> list[_Section]:
    stack: list[tuple[int, str]] = []  # (level, text) of the headings we are currently under
    sections = [_Section((), [])]  # text before the first heading belongs to the first section
    for block in doc.blocks:
        if block.kind == "heading":
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.text))
            sections.append(_Section(tuple(t for _, t in stack), []))
        else:
            text = _unit_text(block)
            sections[-1].units.append(_Unit(block.kind, text, estimate_tokens(text)))
    return [s for s in sections if s.units]


def _split_unit(unit: _Unit, max_tokens: int) -> list[_Unit]:
    """Break a single over-long paragraph at sentence ends, and as a last resort at words."""
    if unit.tokens <= max_tokens:
        return [unit]
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(unit.text):
        candidate = f"{current} {sentence}".strip()
        if current and estimate_tokens(candidate) > max_tokens:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)

    final: list[str] = []
    for piece in pieces:
        if estimate_tokens(piece) <= max_tokens:
            final.append(piece)
            continue
        words: list[str] = []
        for word in piece.split():
            if words and estimate_tokens(" ".join([*words, word])) > max_tokens:
                final.append(" ".join(words))
                words = []
            words.append(word)
        if words:
            final.append(" ".join(words))
    return [_Unit(unit.kind, text, estimate_tokens(text)) for text in final]


def _tail_sentences(unit: _Unit, budget: int) -> _Unit | None:
    """The last whole sentences of a paragraph that fit in the budget, or None if not even one does."""
    tail: list[str] = []
    for sentence in reversed(_SENTENCE_END.split(unit.text)):
        if estimate_tokens(" ".join([sentence, *tail])) > budget:
            break
        tail.insert(0, sentence)
    if not tail:
        return None
    text = " ".join(tail)
    return _Unit(unit.kind, text, estimate_tokens(text))


def _overlap_seed(previous_piece: list[_Unit], budget: int) -> list[_Unit]:
    """What the next piece repeats from the end of the previous one, within the token budget.

    Whole units (list items, table rows, short paragraphs) are repeated as they are.
    A paragraph too big to repeat whole contributes only its last sentences."""
    seed: list[_Unit] = []
    used = 0
    for unit in reversed(previous_piece):
        if used + unit.tokens <= budget:
            seed.insert(0, unit)
            used += unit.tokens
            continue
        if unit.kind == "paragraph":
            tail = _tail_sentences(unit, budget - used)
            if tail:
                seed.insert(0, tail)
        break
    return seed


def _pack(units: list[_Unit], max_tokens: int, overlap_tokens: int) -> list[list[_Unit]]:
    """Fill pieces up to max_tokens; each new piece starts with the previous piece's last lines."""
    pieces: list[list[_Unit]] = []
    current: list[_Unit] = []
    size = 0
    for unit in units:
        if current and size + unit.tokens > max_tokens:
            pieces.append(current)
            seed = _overlap_seed(current, overlap_tokens)
            seed_size = sum(u.tokens for u in seed)
            if seed_size + unit.tokens > max_tokens:
                seed, seed_size = [], 0
            current, size = seed, seed_size
        current.append(unit)
        size += unit.tokens
    if current:
        pieces.append(current)
    return pieces


def _merge_small(pieces: list[_Piece], config: ChunkConfig) -> list[_Piece]:
    merged: list[_Piece] = []
    for piece in pieces:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and prev.whole
            and piece.whole
            and prev.parent == piece.parent
            and prev.tokens < config.min_tokens
            and prev.tokens + piece.tokens + estimate_tokens(piece.path[-1] if piece.path else "")
            <= config.max_tokens
        ):
            prev.parts.extend(piece.parts)
            prev.path = prev.parent  # the merged chunk sits under the shared parent heading
        else:
            merged.append(piece)
    return merged


def chunk_document(doc: CleanDocument, config: ChunkConfig | None = None) -> list[Chunk]:
    config = config or ChunkConfig()
    pieces: list[_Piece] = []
    for section in _sections(doc):
        units = [u for unit in section.units for u in _split_unit(unit, config.max_tokens)]
        heading = section.path[-1] if section.path else None
        parent = section.path[:-1]
        if sum(u.tokens for u in units) <= config.max_tokens:
            pieces.append(_Piece(section.path, [(heading, units)], True, parent))
        else:
            for group in _pack(units, config.max_tokens, config.overlap_tokens):
                pieces.append(_Piece(section.path, [(heading, group)], False, parent))

    chunks = []
    for index, piece in enumerate(_merge_small(pieces, config)):
        text = piece.text
        chunks.append(
            Chunk(
                chunk_id=f"{doc.source_id}:{index:04d}",
                source_id=doc.source_id,
                url=doc.url,
                country=doc.country,
                visa_category=doc.visa_category,
                tier=doc.tier,
                doc_title=doc.title,
                heading_path=list(piece.path),
                chunk_index=index,
                text=text,
                token_count=estimate_tokens(text),
            )
        )
    return chunks

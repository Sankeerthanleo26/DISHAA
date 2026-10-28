"""Turn a saved raw HTML page into a clean, structured document.

Two ideas drive this module:
  * keep the structure (headings, lists, table rows), because the chunker uses it to cut
    the text along the page's own topic boundaries;
  * throw away page furniture (menus, footers, cookie banners), because it would pollute search.

One thing it deliberately does NOT do: drop "hidden" elements. Collapsed accordion panels
(FAQ answers) are usually marked hidden or display:none but are real content.
"""

import hashlib
import re
from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup, NavigableString, Tag

from dishaa.sources import Source

HEADING_LEVELS = {f"h{i}": i for i in range(1, 7)}

# Where the page's real content usually lives, most reliable first.
ROOT_SELECTORS = (
    "main",
    "[role=main]",
    "article",
    "#content",
    "#main",
    ".entry-content",
    ".page-content",
)
MIN_ROOT_CHARS = 200  # a candidate with less text than this is probably not the real content

# Tags that never hold content we want.
REMOVE_TAGS = (
    "script", "style", "noscript", "template", "svg", "iframe", "canvas",
    "form", "select", "input", "textarea", "dialog", "nav", "footer", "aside",
)  # fmt: skip

# Whole-word class names that mark page furniture. Matched against each class token
# (and the id), never as a substring, so "has-sidebar-layout" is not caught by "sidebar".
BOILERPLATE_CLASS_TOKENS = {
    "breadcrumb", "breadcrumbs", "sidebar", "skip-link", "skip-to-content", "share",
    "sharing", "social", "related", "pagination", "newsletter", "back-to-top",
}  # fmt: skip

# Elements that start a new block of text. Everything else is treated as inline text.
BLOCK_TAGS = {
    "p", "div", "section", "article", "main", "header", "ul", "ol", "li", "table", "thead",
    "tbody", "tfoot", "tr", "td", "th", "blockquote", "pre", "dl", "dt", "dd", "figure",
    "figcaption", "details", "summary", "hr", "address", *HEADING_LEVELS,
}  # fmt: skip

# Lines that are page furniture even when they sit inside the content area.
BOILERPLATE_LINES = {
    "skip to content", "skip to main content", "back to top", "print this page", "print",
    "share", "share this page", "menu", "search",
}  # fmt: skip

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff\u2060"), None)


@dataclass
class Block:
    """One unit of content. kind is heading, paragraph, list_item or table_row."""

    kind: str
    text: str
    level: int = 0  # heading level (1-6); 0 for everything else


@dataclass
class CleanDocument:
    source_id: str
    url: str
    country: str
    visa_category: str
    tier: str
    title: str  # the curated title from sources/*.toml, stable across site redesigns
    page_title: str  # what the page itself calls its main heading
    root_selector: str  # which part of the page we treated as the content
    content_hash: str  # fingerprint of the cleaned content (not of the raw HTML)
    blocks: list[Block]

    @property
    def word_count(self) -> int:
        return sum(len(b.text.split()) for b in self.blocks)

    @property
    def heading_count(self) -> int:
        return sum(1 for b in self.blocks if b.kind == "heading")

    def to_dict(self) -> dict:
        return asdict(self)


def normalise(text: str) -> str:
    """Collapse whitespace, remove invisible characters, tidy spaces left around punctuation."""
    text = text.translate(_ZERO_WIDTH).replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:%)])", r"\1", text)
    return re.sub(r"(\()\s+", r"\1", text)


def _has_block_descendant(tag: Tag) -> bool:
    return tag.find(list(BLOCK_TAGS)) is not None


class _Walker:
    """Reads an HTML subtree in document order and produces a flat list of Blocks."""

    def __init__(self) -> None:
        self.level = 1  # level of the most recent heading; accordion <summary> ranks below it

    def text_of(self, tag: Tag) -> str:
        return normalise(" ".join(b.text for b in self.walk(tag)))

    def walk(self, node: Tag) -> list[Block]:
        out: list[Block] = []
        buffer: list[str] = []  # loose text that sits directly inside a container

        def flush() -> None:
            text = normalise("".join(buffer))
            buffer.clear()
            if text:
                out.append(Block("paragraph", text))

        for child in node.children:
            if type(child) is NavigableString:  # skips comments, doctypes and similar
                buffer.append(str(child))
            elif not isinstance(child, Tag):
                continue
            elif child.name in HEADING_LEVELS:
                flush()
                text = self.text_of(child)
                if text:
                    self.level = HEADING_LEVELS[child.name]
                    out.append(Block("heading", text, self.level))
            elif child.name == "summary":  # accordion question: treat as a heading
                flush()
                text = self.text_of(child)
                if text:
                    out.append(Block("heading", text, min(self.level + 1, 6)))
            elif child.name == "table":
                flush()
                out.extend(self._table(child))
            elif child.name in ("ul", "ol"):
                flush()
                out.extend(self._list_items(child))
            elif child.name in BLOCK_TAGS or _has_block_descendant(child):
                flush()
                out.extend(self.walk(child))
            else:  # inline element such as <a>, <strong>, <span>
                buffer.append(child.get_text())
        flush()
        return out

    def _list_items(self, lst: Tag) -> list[Block]:
        out: list[Block] = []
        for li in lst.find_all("li", recursive=False):
            inner = self.walk(li)
            if inner and inner[0].kind == "paragraph":
                inner[0] = Block("list_item", inner[0].text)
            out.extend(inner)
        return out

    def _table(self, table: Tag) -> list[Block]:
        """One block per row, written as "Column: value; Column: value" so each row
        still makes sense on its own after the table layout is gone."""
        rows: list[Block] = []
        headers: list[str] | None = None
        for tr in table.find_all("tr"):
            if tr.find_parent("table") is not table:  # row of a nested table
                continue
            cells = tr.find_all(["th", "td"], recursive=False)
            texts = [self.text_of(c) for c in cells]
            if not any(texts):
                continue
            if headers is None and not rows and all(c.name == "th" for c in cells):
                headers = texts
                continue
            if headers and len(headers) == len(texts):
                parts = [f"{h}: {t}" if h else t for h, t in zip(headers, texts, strict=True) if t]
                rows.append(Block("table_row", "; ".join(parts)))
            elif len(cells) == 2 and cells[0].name == "th":
                rows.append(Block("table_row", f"{texts[0]}: {texts[1]}"))
            else:
                rows.append(Block("table_row", " | ".join(t for t in texts if t)))
        return rows


def _pick_root(soup: BeautifulSoup) -> tuple[Tag, str]:
    for selector in ROOT_SELECTORS:
        candidates = soup.select(selector)
        if candidates:
            best = max(candidates, key=lambda t: len(t.get_text()))
            if len(best.get_text(strip=True)) >= MIN_ROOT_CHARS:
                return best, selector
    return (soup.body or soup), "body"


def _is_boilerplate(tag: Tag) -> bool:
    classes = [c.lower() for c in (tag.get("class") or [])]
    element_id = (tag.get("id") or "").lower()
    if "cookie" in element_id or any("cookie" in c for c in classes):
        return True
    return element_id in BOILERPLATE_CLASS_TOKENS or any(
        c in BOILERPLATE_CLASS_TOKENS for c in classes
    )


def _strip_boilerplate(root: Tag, root_is_body: bool) -> None:
    for tag in root.find_all(list(REMOVE_TAGS)):
        tag.extract()
    if root_is_body:
        # No <main> or <article> was found. A page-level <header> is furniture unless it
        # carries the page's <h1>.
        for header in root.find_all("header"):
            if header.find("h1") is None:
                header.extract()
    for tag in root.find_all(True):  # descendants only, so the root itself is never removed
        if _is_boilerplate(tag):
            tag.extract()


def _clean_blocks(blocks: list[Block]) -> list[Block]:
    out: list[Block] = []
    for block in blocks:
        if block.kind != "heading" and block.text.lower() in BOILERPLATE_LINES:
            continue
        if out and out[-1] == block:  # menus are often included twice (desktop and mobile)
            continue
        out.append(block)
    return out


def _site_title(meta_title: str) -> str:
    return re.split(r"\s[-|\u2013\u2014]\s", meta_title, maxsplit=1)[0].strip()


def content_hash(page_title: str, blocks: list[Block]) -> str:
    digest = hashlib.sha256(page_title.encode())
    for b in blocks:
        digest.update(f"\n{b.kind}:{b.level}:{b.text}".encode())
    return digest.hexdigest()


def extract_document(html: bytes | str, source: Source) -> CleanDocument:
    soup = BeautifulSoup(html, "lxml")
    meta_title = normalise(soup.title.get_text()) if soup.title else ""
    for br in soup.find_all("br"):
        br.replace_with(" ")

    root, selector = _pick_root(soup)
    _strip_boilerplate(root, root_is_body=(selector == "body"))
    blocks = _clean_blocks(_Walker().walk(root))

    page_title = ""
    if blocks and blocks[0].kind == "heading" and blocks[0].level == 1:
        page_title = blocks.pop(0).text  # the page's own title, not a section of its content
    page_title = page_title or _site_title(meta_title) or source.title

    return CleanDocument(
        source_id=source.id,
        url=source.url,
        country=source.country,
        visa_category=source.visa_category,
        tier=source.tier,
        title=source.title,
        page_title=page_title,
        root_selector=selector,
        content_hash=content_hash(page_title, blocks),
        blocks=blocks,
    )

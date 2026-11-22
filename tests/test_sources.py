from pathlib import Path

import pytest

from dishaa.sources import load_sources

REAL_FILE = Path(__file__).resolve().parents[1] / "sources" / "ie_student.toml"
US_FILE = Path(__file__).resolve().parents[1] / "sources" / "us_student.toml"


def test_real_ireland_list_is_valid():
    sources = load_sources(REAL_FILE)
    assert len(sources) == 14
    assert len({s.id for s in sources}) == 14
    assert all(s.url.startswith("https://") for s in sources)
    assert {s.country for s in sources} == {"IE"}
    assert [s.id for s in sources if s.tier == "supporting"] == ["education-in-ireland-working"]
    assert [s.id for s in sources if s.visa_category == "graduate"] == ["graduate-programme-1g"]


def test_defaults_are_applied_and_overridable(tmp_path: Path):
    f = tmp_path / "s.toml"
    f.write_text(
        '[defaults]\ncountry="IE"\nvisa_category="student"\ntier="core"\n'
        '[[source]]\nid="a"\ntitle="A"\nurl="https://x.test/a"\n'
        '[[source]]\nid="b"\ntitle="B"\nurl="https://x.test/b"\nvisa_category="graduate"\n'
    )
    a, b = load_sources(f)
    assert (a.visa_category, b.visa_category) == ("student", "graduate")


DEFAULTS = 'country = "IE"\nvisa_category = "student"\ntier = "core"\n'


def toml(defaults: str = "", *sources: str) -> str:
    return f"[defaults]\n{defaults}" + "".join(sources)


def src(id: str, url: str) -> str:
    return f'[[source]]\nid = "{id}"\ntitle = "T"\nurl = "{url}"\n'


@pytest.mark.parametrize(
    "body, message",
    [
        (toml("", src("a", "https://x.test")), "missing"),
        (toml(DEFAULTS, src("a", "http://x.test")), "https"),
        (toml(DEFAULTS, src("a", "https://x.test/1"), src("a", "https://x.test/2")), "duplicate"),
        (
            toml(DEFAULTS.replace("core", "weird"), src("a", "https://x.test/1")),
            "tier",
        ),
    ],
)
def test_bad_files_are_rejected(tmp_path: Path, body: str, message: str):
    f = tmp_path / "s.toml"
    f.write_text(body)
    with pytest.raises(ValueError, match=message):
        load_sources(f)


def test_real_usa_list_is_valid():
    sources = load_sources(US_FILE)
    assert len(sources) == 33
    assert len({s.id for s in sources}) == 33
    assert all(s.url.startswith("https://") for s in sources)
    assert {s.country for s in sources} == {"US"}
    assert {s.tier for s in sources} == {"core", "supporting"}
    assert sum(s.tier == "supporting" for s in sources) == 8
    assert {s.visa_category for s in sources} == {
        "f1-student", "f1-employment", "practical-training", "opt", "stem-opt",
        "h1b", "o1", "green-card", "pathway-overview",
    }


def test_us_and_ireland_ids_do_not_collide():
    ids = [s.id for s in load_sources(REAL_FILE)] + [s.id for s in load_sources(US_FILE)]
    assert len(ids) == len(set(ids))


def test_no_pdfs_or_dated_posts_in_lists():
    import re

    for path in (REAL_FILE, US_FILE):
        for s in load_sources(path):
            assert not s.url.lower().endswith(".pdf"), s.id
            assert not re.search(r"/20\d\d/\d\d/", s.url), s.id


def test_pilot_university_lists_are_valid():
    base = Path(__file__).resolve().parents[1] / "sources"
    cud = load_sources(base / "cu_denver.toml")
    ucd = load_sources(base / "ucd.toml")
    assert len(cud) == 17 and len(ucd) == 14
    assert {s.country for s in cud} == {"US"} and {s.country for s in ucd} == {"IE"}
    assert all(s.id.startswith("cud-") for s in cud) and all(s.id.startswith("ucd-") for s in ucd)
    assert all(s.visa_category.startswith("university-") for s in cud + ucd)
    ids = [s.id for s in cud + ucd]
    assert len(ids) == len(set(ids))
    existing = {s.id for f in ("us_student.toml", "ie_student.toml") for s in load_sources(base / f)}
    assert not existing & set(ids)
    assert all(s.url.startswith("https://") and not s.url.lower().endswith(".pdf") for s in cud + ucd)

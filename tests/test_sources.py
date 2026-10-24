from pathlib import Path

import pytest

from dishaa.sources import load_sources

REAL_FILE = Path(__file__).resolve().parents[1] / "sources" / "ie_student.toml"


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

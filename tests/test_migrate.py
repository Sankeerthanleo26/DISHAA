from pathlib import Path

from dishaa.migrate import pending_migrations


def test_pending_migrations_skips_applied_and_keeps_order(tmp_path: Path):
    for name in ["0002_b.sql", "0001_a.sql", "0003_c.sql"]:
        (tmp_path / name).write_text("SELECT 1;")
    todo = pending_migrations({"0001_a.sql"}, directory=tmp_path)
    assert [p.name for p in todo] == ["0002_b.sql", "0003_c.sql"]

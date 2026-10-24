"""A deliberately small SQL migration runner.

Applies files in migrations/ (named 0001_*.sql, 0002_*.sql, ...) in order, once each,
and records what has been applied in the schema_migrations table.
"""

from pathlib import Path

from dishaa.db import connect

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def pending_migrations(applied: set[str], directory: Path = MIGRATIONS_DIR) -> list[Path]:
    return [p for p in sorted(directory.glob("*.sql")) if p.name not in applied]


def main() -> None:
    with connect(register_vectors=False) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        applied = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
        todo = pending_migrations(applied)
        if not todo:
            print("Database is up to date.")
            return
        for path in todo:
            print(f"Applying {path.name} ...")
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
        print(f"Applied {len(todo)} migration(s).")


if __name__ == "__main__":
    main()

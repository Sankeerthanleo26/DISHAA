"""Database connection helper."""

import psycopg
from pgvector.psycopg import register_vector

from dishaa.config import get_settings


def connect(register_vectors: bool = True) -> psycopg.Connection:
    """Open a connection. Vector types can only be registered once the extension exists,
    so the migration runner passes register_vectors=False."""
    conn = psycopg.connect(get_settings().database_url)
    if register_vectors:
        register_vector(conn)
    return conn


from collections.abc import Sequence
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import settings, validate_settings


class Database:
    """Manage pooled connections to the WhoKnows Neon database."""

    def __init__(self) -> None:
        validate_settings()

        self.pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=5,
            kwargs={
                "row_factory": dict_row,
                "autocommit": False,
            },
            open=False,
        )

    def open(self) -> None:
        """Open the pool and wait for an initial connection."""
        self.pool.open(wait=True)

    def close(self) -> None:
        """Close the connection pool."""
        self.pool.close()

    def fetch_all(
        self,
        query: str,
        params: Sequence[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a SELECT query and return all rows as dictionaries."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def fetch_one(
        self,
        query: str,
        params: Sequence[Any] | None = None,
    ) -> dict[str, Any] | None:
        """Execute a query and return one row, or None."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()

    def execute(
        self,
        query: str,
        params: Sequence[Any] | None = None,
    ) -> None:
        """Execute a write query and commit the transaction."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
            conn.commit()

    def execute_many(
        self,
        query: str,
        rows: Sequence[Sequence[Any]],
    ) -> None:
        """Execute a parameterized write for multiple rows."""
        if not rows:
            return

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, rows)
            conn.commit()

    def test_connection(self) -> bool:
        """Check whether the database is reachable."""
        row = self.fetch_one("SELECT 1 AS connected")
        return row is not None and row["connected"] == 1


if __name__ == "__main__":
    db = Database()

    try:
        db.open()

        if db.test_connection():
            print("Successfully connected to Neon PostgreSQL.")
    except Exception as exc:
        print(f"Database connection failed: {exc}")
        raise
    finally:
        db.close()

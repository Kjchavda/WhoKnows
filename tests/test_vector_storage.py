import unittest
from pathlib import Path
from typing import cast

from backend.db import Database as BaseDatabase
from crawler.crawler import run_init_db
from embeddings.chunker import Chunker
from embeddings.embedder import Embedder
from embeddings.pipeline import Pipeline
from embeddings.search import SemanticSearch
from embeddings.store import Store
from sentence_transformers import SentenceTransformer


class _FakeDatabase(BaseDatabase):
    def __init__(self, existing_rows: list[dict] | None = None):
        self.existing_rows = existing_rows or []
        self.query = None
        self.rows = None
        self.fetch_query = None

    def fetch_all(self, query, _params=None):
        self.fetch_query = query
        return self.existing_rows

    def execute_many(self, query, rows):
        self.query = query
        self.rows = rows

    def run_tx(self, callback):
        return callback(_FakeConnection())


class _FakeConnection:
    def __init__(self):
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((query, params))
        return _FakeCursor()


class _FakeCursor:
    def fetchall(self):
        return [{"item_id": 1}]


class _ChunkerStub(Chunker):
    def __init__(self, candidates):
        self.candidates = candidates

    def chunk_records(self, _records):
        return self.candidates


class _ModelStub:
    def encode(self, _query):
        return _Embedding()


class _Embedding:
    def tolist(self):
        return [0.1, 0.2]


class _EmbedderStub(Embedder):
    def __init__(self):
        self.model = cast(SentenceTransformer, _ModelStub())

    def embed_records(self, records):
        return records


class _StoreStub(Store):
    def __init__(self, db):
        super().__init__(db)
        self.stored = []

    def store_records(self, records):
        self.stored.extend(records)


class VectorStorageTests(unittest.TestCase):
    def test_pipeline_deduplicates_only_the_same_authored_source_chunk(self):
        existing = {
            "item_id": 42,
            "source": "review",
            "source_id": 11,
            "author_id": 7,
            "chunk_index": 0,
            "chunk_hash": "same-text",
        }
        candidates = [
            existing.copy(),
            {**existing, "author_id": 8},
            {**existing, "source_id": 12},
            {**existing, "item_id": 43},
            {**existing, "chunk_hash": "updated-text"},
        ]
        db = _FakeDatabase([existing])
        pipeline = Pipeline.__new__(Pipeline)
        pipeline.db = db
        pipeline.chunker = _ChunkerStub(candidates)
        pipeline.embedder = _EmbedderStub()
        pipeline.store = _StoreStub(db)

        calls = 0

        def extract_method(**_kwargs):
            nonlocal calls
            calls += 1
            return [{"text": "unused"}] if calls == 1 else []

        pipeline.process_source(
            repo_id=1,
            source_name="Reviews",
            extract_method=extract_method,
            dry_run=False,
        )

        self.assertEqual(pipeline.store.stored, candidates[1:])
        self.assertIn("author_id", db.fetch_query or "")

    def test_search_sets_hnsw_search_depth_in_the_query_transaction(self):
        class Database(BaseDatabase):
            connection: _FakeConnection

            def run_tx(self, callback):
                connection = _FakeConnection()
                self.connection = connection
                return callback(connection)

        db = Database()
        rows = SemanticSearch(db, _EmbedderStub()).search("query", repo_id=9)

        self.assertEqual(rows, [{"item_id": 1}])
        self.assertEqual(
            db.connection.queries[0][0],
            "SET LOCAL hnsw.ef_search = 100",
        )
        self.assertIn("i.repo_id = %s", db.connection.queries[1][0])
        params = db.connection.queries[1][1]
        self.assertIsNotNone(params)
        if params is not None:
            self.assertEqual(params[1], 9)

    def test_store_targets_the_schema_unique_index_columns(self):
        db = _FakeDatabase()
        Store(db).store_records([{
            "item_id": 1,
            "source": "review",
            "source_id": 2,
            "author_id": 3,
            "text": "LGTM",
            "embedding": [0.1, 0.2],
            "embedding_model": "model",
            "chunk_index": 0,
            "chunk_hash": "hash",
        }])

        query = db.query or ""
        self.assertIn(
            "ON CONFLICT (item_id, source, source_id, author_id, chunk_index)",
            query,
        )
        self.assertIn("created_at = EXCLUDED.created_at", query)
        rows = db.rows or []
        self.assertEqual(rows[0][5:9], ([0.1, 0.2], "model", 0, "hash"))

    def test_init_db_reads_the_root_schema_file(self):
        class Connection:
            def __init__(self):
                self.schema = None

            def execute(self, schema):
                self.schema = schema

        class Database(BaseDatabase):
            connection: Connection

            def run_tx(self, callback):
                self.connection = Connection()
                callback(self.connection)

        db = Database()
        run_init_db(db)

        schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
        self.assertEqual(
            db.connection.schema,
            schema_path.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()

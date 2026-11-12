import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from backend.db import Database as BaseDatabase
from crawler.crawler import run_init_db
from embeddings.chunker import Chunker
from embeddings.embedder import Embedder
from embeddings.pipeline import Pipeline
from embeddings.search import SemanticSearch
from embeddings.store import Store
from embeddings.text_extractor import TextExtractor
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
    def test_extractors_use_historical_source_timestamps(self):
        created_at = datetime(2020, 1, 2, tzinfo=timezone.utc)

        item_db = _FakeDatabase([{
            "item_id": 1,
            "author_id": 2,
            "text": "Issue body",
            "created_at": created_at,
        }])
        item = TextExtractor(item_db).extract_item_bodies(9)[0]
        self.assertEqual(item["created_at"], created_at)
        self.assertIn("created_at", item_db.fetch_query or "")

        comment_db = _FakeDatabase([{
            "github_id": 3,
            "kind": "issue_comment",
            "author_id": 4,
            "item_id": 1,
            "body": "Comment body",
            "created_at": created_at,
        }])
        comment = TextExtractor(comment_db).extract_comments(9)[0]
        self.assertEqual(comment["created_at"], created_at)
        self.assertIn("c.created_at", comment_db.fetch_query or "")

        review_db = _FakeDatabase([{
            "github_id": 5,
            "item_id": 1,
            "reviewer_id": 6,
            "body": "Review body",
            "created_at": created_at,
        }])
        review = TextExtractor(review_db).extract_reviews(9)[0]
        self.assertEqual(review["created_at"], created_at)
        self.assertIn("rv.submitted_at AS created_at", review_db.fetch_query or "")

    def test_chunker_copies_timestamp_to_every_chunk(self):
        created_at = datetime(2020, 1, 2, tzinfo=timezone.utc)
        chunker = Chunker()
        chunker.chunk_size = 2
        chunker.chunk_overlap = 0

        chunks = chunker.chunk_records([{
            "item_id": 1,
            "source": "item_body",
            "source_id": None,
            "author_id": 2,
            "text": "one two three",
            "created_at": created_at,
        }])

        self.assertEqual(len(chunks), 2)
        self.assertTrue(all(chunk["created_at"] == created_at for chunk in chunks))

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

    def test_pipeline_reindexes_chunk_when_historical_timestamp_changed(self):
        created_at = datetime(2020, 1, 2, tzinfo=timezone.utc)
        existing = {
            "item_id": 42,
            "source": "review",
            "source_id": 11,
            "author_id": 7,
            "chunk_index": 0,
            "chunk_hash": "same-text",
            "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        }
        candidate = {**existing, "created_at": created_at}
        db = _FakeDatabase([existing])
        pipeline = Pipeline.__new__(Pipeline)
        pipeline.db = db
        pipeline.chunker = _ChunkerStub([candidate])
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

        self.assertEqual(pipeline.store.stored, [candidate])
        self.assertIn("created_at", db.fetch_query or "")

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

    def test_search_applies_optional_time_and_item_exclusions(self):
        class Database(BaseDatabase):
            connection: _FakeConnection

            def run_tx(self, callback):
                connection = _FakeConnection()
                self.connection = connection
                return callback(connection)

        db = Database()
        as_of = datetime(2020, 1, 2, tzinfo=timezone.utc)
        SemanticSearch(db, _EmbedderStub()).search(
            "query",
            repo_id=9,
            limit=20,
            as_of=as_of,
            exclude_item_ids={41, 42},
        )

        query, params = db.connection.queries[1]
        self.assertIn("c.created_at < %s", query)
        self.assertIn("c.item_id = ANY(%s::bigint[])", query)
        self.assertEqual(params[1:5], (9, as_of, as_of, [41, 42]))
        self.assertEqual(params[6], 20)

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
            "created_at": datetime(2020, 1, 2, tzinfo=timezone.utc),
        }])

        query = db.query or ""
        self.assertIn(
            "ON CONFLICT (item_id, source, source_id, author_id, chunk_index)",
            query,
        )
        self.assertIn("created_at = EXCLUDED.created_at", query)
        rows = db.rows or []
        self.assertEqual(rows[0][5:9], ([0.1, 0.2], "model", 0, "hash"))
        self.assertEqual(rows[0][9], datetime(2020, 1, 2, tzinfo=timezone.utc))
        self.assertIn("VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", query)

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

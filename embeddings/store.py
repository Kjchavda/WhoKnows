
from backend.db import Database


class Store:
    def __init__(self, db: Database):
        self.db = db

    def store_records(self, records):
        if not records:
            return

        query = """
            INSERT INTO chunks (
                item_id,
                source,
                source_id,
                author_id,
                text,
                embedding,
                embedding_model,
                chunk_index,
                chunk_hash,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (item_id, source, source_id, author_id, chunk_index)
            DO UPDATE SET
                text = EXCLUDED.text,
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model,
                chunk_hash = EXCLUDED.chunk_hash,
                created_at = EXCLUDED.created_at;
        """

        rows = [
            (
                record["item_id"],
                record["source"],
                record["source_id"],
                record["author_id"],
                record["text"],
                record["embedding"],
                record["embedding_model"],
                record["chunk_index"],
                record["chunk_hash"],
            )
            for record in records
        ]

        self.db.execute_many(query, rows)

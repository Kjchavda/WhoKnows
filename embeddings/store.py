
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
                chunk_hash,
                embedding,
                embedding_model,
                chunk_index
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT uq_chunks_source_chunk
            DO UPDATE SET
                author_id = EXCLUDED.author_id,
                text = EXCLUDED.text,
                chunk_hash = EXCLUDED.chunk_hash,
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model;
        """

        rows = [
            (
                record["item_id"],
                record["source"],
                record["source_id"],
                record["author_id"],
                record["text"],
                record["chunk_hash"],
                record["embedding"],
                record["embedding_model"],
                record["chunk_index"],
            )
            for record in records
        ]

        self.db.execute_many(query, rows)

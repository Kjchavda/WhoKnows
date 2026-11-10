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
            ON CONFLICT (item_id, source, chunk_index) DO NOTHING;
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
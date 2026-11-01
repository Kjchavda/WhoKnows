from config import settings
from db import Database


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
                embedding_model
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s
            );
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
            )
            for record in records
        ]

        self.db.execute_many(query, rows)

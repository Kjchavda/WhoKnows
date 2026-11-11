from typing import Optional

from backend.config import settings as dbsettings
from backend.db import Database
from embeddings.chunker import Chunker
from embeddings.config import settings as embeddingsettings
from embeddings.embedder import Embedder
from embeddings.store import Store
from embeddings.text_extractor import TextExtractor


class Pipeline:
    def __init__(self, db: Optional[Database] = None, embedder: Optional[Embedder] = None):
        # Allow sharing existing DB connection or create a new one
        self._owns_db = db is None
        self.db = db if db is not None else Database()
        self.extractor = TextExtractor(self.db)
        self.chunker = Chunker()
        # Shared embedder instance to prevent re-loading weights
        self.embedder = embedder if embedder is not None else Embedder()
        self.store = Store(self.db)

    @staticmethod
    def _chunk_key(chunk: dict) -> tuple:
        return (
            chunk["item_id"],
            chunk["source"],
            chunk["source_id"],
            chunk["author_id"],
            chunk["chunk_index"],
            chunk["chunk_hash"],
        )

    def process_source(
        self,
        repo_id: int,
        source_name: str,
        extract_method,
        dry_run: bool = True,
        max_batches: Optional[int] = None,
    ):
        offset = 0
        batch_number = 0
        total_records = 0
        total_chunks = 0
        total_stored = 0

        while True:
            # 1. Extract one batch from the selected repository
            records = extract_method(
                repo_id=repo_id,
                limit=embeddingsettings.extraction_batch_size,
                offset=offset,
            )

            if not records:
                break

            batch_number += 1
            total_records += len(records)

            # 2. Split source records into chunks (includes chunk_hash)
            chunks = self.chunker.chunk_records(records)
            
            # 3. Incremental check: filter out chunks that already exist in DB
            if not dry_run and chunks:
                # Extract item_ids and source_ids present in this chunk batch
                item_ids = tuple({c["item_id"] for c in chunks if c.get("item_id") is not None})
                
                if item_ids:
                    sql = """
                        SELECT item_id, source, source_id, author_id, chunk_index, chunk_hash
                        FROM chunks 
                        WHERE item_id = ANY(%s) AND chunk_hash IS NOT NULL;
                    """
                    existing_rows = self.db.fetch_all(sql, (list(item_ids),))
                    existing_keys = {
                        self._chunk_key(row) for row in existing_rows
                    }

                    chunks = [
                        chunk
                        for chunk in chunks
                        if self._chunk_key(chunk) not in existing_keys
                    ]
            # 4. Embed ONLY new/missing chunks
            if chunks:
                embedded_chunks = self.embedder.embed_records(chunks)
            else:
                embedded_chunks = []

            # 5. Store in smaller database batches
            if not dry_run and embedded_chunks:
                for start in range(
                    0,
                    len(embedded_chunks),
                    dbsettings.database_batch_size,
                ):
                    batch = embedded_chunks[
                        start : start + dbsettings.database_batch_size
                    ]

                    self.store.store_records(batch)
                    total_stored += len(batch)

            print(
                f"{source_name} | batch {batch_number} | "
                f"records: {len(records)} | "
                f"new chunks embedded: {len(chunks)} | "
                f"stored: {0 if dry_run else total_stored}"
            )

            offset += len(records)

            if max_batches is not None and batch_number >= max_batches:
                break

        print(
            f"\nFinished {source_name}: "
            f"{total_records} records, "
            f"{total_chunks} new chunks, "
            f"{total_stored} stored."
        )

    def run(self, repo_id: int, dry_run: bool = True, max_batches: Optional[int] = None):
        if self._owns_db:
            self.db.open()

        try:
            sources = [
                ("Item bodies", self.extractor.extract_item_bodies),
                ("Comments", self.extractor.extract_comments),
                ("Reviews", self.extractor.extract_reviews),
            ]

            for source_name, extract_method in sources:
                self.process_source(
                    repo_id=repo_id,
                    source_name=source_name,
                    extract_method=extract_method,
                    dry_run=dry_run,
                    max_batches=max_batches,
                )

        finally:
            if self._owns_db:
                self.db.close()
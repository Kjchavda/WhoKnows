
from embeddings.config import settings
from embeddings.db import Database
from embeddings.text_extractor import TextExtractor
from embeddings.chunker import Chunker
from embeddings.embedder import Embedder
from embeddings.store import Store


class Pipeline:
    def __init__(self):
        self.db = Database()
        self.extractor = TextExtractor(self.db)
        self.chunker = Chunker()
        self.embedder = Embedder()
        self.store = Store(self.db)

    def process_source(
        self,
        source_name,
        extract_method,
        dry_run=True,
        max_batches=None,
    ):
        offset = 0
        batch_number = 0
        total_records = 0
        total_chunks = 0
        total_stored = 0

        while True:
            # 1. Extract one batch from PostgreSQL
            records = extract_method(
                limit=settings.extraction_batch_size,
                offset=offset,
            )

            if not records:
                break

            batch_number += 1
            total_records += len(records)

            # 2. Split source records into chunks
            chunks = self.chunker.chunk_records(records)
            total_chunks += len(chunks)

            # 3. Generate embeddings
            embedded_chunks = self.embedder.embed_records(chunks)

            # 4. Store in smaller database batches
            if not dry_run:
                for start in range(
                    0,
                    len(embedded_chunks),
                    settings.database_batch_size,
                ):
                    batch = embedded_chunks[
                        start : start + settings.database_batch_size
                    ]
                    self.store.store_records(batch)
                    total_stored += len(batch)

            print(
                f"{source_name} | batch {batch_number} | "
                f"records: {len(records)} | "
                f"chunks: {len(chunks)} | "
                f"stored: {0 if dry_run else total_stored}"
            )

            offset += len(records)

            # Stop after the requested number of batches, if specified.
            if max_batches is not None and batch_number >= max_batches:
                break

        print(
            f"\nFinished {source_name}: "
            f"{total_records} records, "
            f"{total_chunks} chunks, "
            f"{total_stored} stored."
        )

    def run(self, dry_run=True, max_batches=None):
        self.db.open()

        try:
            sources = [
                ("Item bodies", self.extractor.extract_item_bodies),
                ("Comments", self.extractor.extract_comments),
                ("Reviews", self.extractor.extract_reviews),
            ]

            for source_name, extract_method in sources:
                self.process_source(
                    source_name=source_name,
                    extract_method=extract_method,
                    dry_run=dry_run,
                    max_batches=max_batches,
                )

        finally:
            self.db.close()


if __name__ == "__main__":
    pipeline = Pipeline()

    # Safe initial test: process one extraction batch per source
    # without writing anything to the chunks table.
    pipeline.run(dry_run=True, max_batches=1)

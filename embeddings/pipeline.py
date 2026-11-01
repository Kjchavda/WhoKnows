
from db import Database
from text_extractor import TextExtractor
from chunker import Chunker
from embedder import Embedder
from store import Store


class EmbeddingPipeline:
    def __init__(self):
        self.db = Database()
        self.extractor = TextExtractor(self.db)
        self.chunker = Chunker()
        self.embedder = Embedder()
        self.store = Store(self.db)

    def run(self):
        self.db.open()

        try:
            # 1. Extract records from all three sources.
            records = (
                self.extractor.extract_item_bodies()
                + self.extractor.extract_comments()
                + self.extractor.extract_reviews()
            )
            print(f"Extracted {len(records)} records")

            # 2. Split text into chunks.
            chunked_records = self.chunker.chunk_records(records)
            print(f"Created {len(chunked_records)} chunks")

            # 3. Generate embeddings.
            embedded_records = self.embedder.embed_records(chunked_records)
            print(f"Generated {len(embedded_records)} embeddings")

            # 4. Save to PostgreSQL.
            self.store.store_records(embedded_records)
            print("Stored embeddings successfully")

        finally:
            self.db.close()

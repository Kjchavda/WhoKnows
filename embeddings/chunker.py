import hashlib
import os
from dotenv import load_dotenv

load_dotenv()


class Chunker:
    def __init__(self):
        # Defaulting to 150 words with 30 overlap fits all-MiniLM-L6-v2 token limits
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "150"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "30"))

    def compute_hash(self, text: str) -> str:
        """Generates a SHA-256 hash for chunk uniqueness across database re-runs."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def chunk_text(self, text: str):
        words = text.split()
        chunks = []

        if not words:
            return chunks

        start = 0
        step = self.chunk_size - self.chunk_overlap

        # Edge case: if step <= 0, force progress to prevent an infinite loop
        if step <= 0:
            step = max(1, self.chunk_size)

        while start < len(words):
            end = start + self.chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)

            start += step

        return chunks

    def chunk_records(self, records):
        chunked_records = []

        for record in records:
            chunks = self.chunk_text(record["text"])

            for chunk_index, chunk in enumerate(chunks):
                chunked_record = {
                    "item_id": record["item_id"],
                    "source": record["source"],
                    "source_id": record["source_id"],
                    "author_id": record["author_id"],
                    "created_at": record.get("created_at"),
                    "chunk_index": chunk_index,
                    "text": chunk,
                    "chunk_hash": self.compute_hash(chunk),  # Required for ON CONFLICT DO NOTHING
                }
                chunked_records.append(chunked_record)

        return chunked_records
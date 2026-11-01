import os
from dotenv import load_dotenv

load_dotenv()


class Chunker:
    def chunk_text(self, text: str):
        words = text.split()
        chunks = []

        chunk_size = int(os.getenv("CHUNK_SIZE", "500"))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "75"))

        start = 0
        step = chunk_size - chunk_overlap

        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)

            start += step

        return chunks

    def chunk_records(self, records):
        chunked_records = []

        for record in records:
            chunks = self.chunk_text(record["text"])
            # 2. Loop through each text chunk

            for chunk_index, chunk in enumerate(chunks):
                chunked_record = {
                    "item_id": record["item_id"],
                    "source": record["source"],
                    "source_id": record["source_id"],
                    "author_id": record["author_id"],
                    "chunk_index": chunk_index,
                    "text": chunk
                }
                chunked_records.append(chunked_record)

        return chunked_records

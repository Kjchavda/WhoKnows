
from sentence_transformers import SentenceTransformer
from embeddings.config import settings


class Embedder:
    def __init__(self):
        # Load the model once and reuse it for every batch.
        self.model = SentenceTransformer(settings.embedding_model)

    def embed_records(self, records):
        embedded_records = []

        batch_size = settings.embedding_batch_size

        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]

            # Extract text from each record.
            texts = [record["text"] for record in batch]

            # Generate one embedding per text.
            embeddings = self.model.encode(texts)

            # Preserve metadata and attach the corresponding embedding.
            for record, embedding in zip(batch, embeddings):
                embedded_record = record.copy()
                embedded_record["embedding"] = embedding.tolist()
                embedded_record["embedding_model"] = settings.embedding_model

                embedded_records.append(embedded_record)

        return embedded_records

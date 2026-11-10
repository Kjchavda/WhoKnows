from typing import Optional
from sentence_transformers import SentenceTransformer
from backend.config import settings as dbsettings
from embeddings.config import settings as embeddingsettings


class Embedder:
    def __init__(self, model_instance: Optional[SentenceTransformer] = None):
        """
        Accepts an existing SentenceTransformer instance (e.g. from app.state).
        If None is passed (or called empty like Embedder()), it loads the default model.
        """
        if model_instance is not None:
            self.model = model_instance
        else:
            self.model = SentenceTransformer(embeddingsettings.embedding_model)

    def embed_records(self, records):
        if not records:
            return []

        embedded_records = []
        batch_size = embeddingsettings.embedding_batch_size

        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            texts = [record["text"] for record in batch]

            embeddings = self.model.encode(texts, show_progress_bar=False)

            for record, embedding in zip(batch, embeddings):
                embedded_record = record.copy()
                embedded_record["embedding"] = embedding.tolist()
                embedded_record["embedding_model"] = embeddingsettings.embedding_model

                embedded_records.append(embedded_record)

        return embedded_records
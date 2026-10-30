import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from the project root's .env file.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Database
    database_url: str = os.getenv("DATABASE_URL", "")

    # Embedding model
    # Placeholder: choose your actual model before running the pipeline.
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )

    # all-MiniLM-L6-v2 produces 384-dimensional embeddings.
    embedding_dimensions: int = int(
        os.getenv("EMBEDDING_DIMENSIONS", "384")
    )

    # Chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "75"))

    # Processing
    extraction_batch_size: int = int(
        os.getenv("EXTRACTION_BATCH_SIZE", "100")
    )
    embedding_batch_size: int = int(
        os.getenv("EMBEDDING_BATCH_SIZE", "32")
    )
    database_batch_size: int = int(
        os.getenv("DATABASE_BATCH_SIZE", "100")
    )

    # Pipeline
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()


def validate_settings() -> None:
    """Validate configuration before starting the pipeline."""

    if not settings.database_url:
        raise ValueError(
            "DATABASE_URL is missing. Set it in your .env file."
        )

    if settings.embedding_dimensions <= 0:
        raise ValueError("EMBEDDING_DIMENSIONS must be positive.")

    if settings.chunk_size <= 0:
        raise ValueError("CHUNK_SIZE must be positive.")

    if not 0 <= settings.chunk_overlap < settings.chunk_size:
        raise ValueError(
            "CHUNK_OVERLAP must be non-negative "
            "and smaller than CHUNK_SIZE."
        )

    if min(
        settings.extraction_batch_size,
        settings.embedding_batch_size,
        settings.database_batch_size,
    ) <= 0:
        raise ValueError("All batch sizes must be positive.")

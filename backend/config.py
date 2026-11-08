import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from the project root's .env file.
load_dotenv()


@dataclass(frozen=True)
class DbSettings:
    # Database
    database_url: str = os.getenv("DATABASE_URL", "")

    database_batch_size: int = int(
        os.getenv("DATABASE_BATCH_SIZE", "100")
    )

    # Pipeline
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = DbSettings()


def validate_settings() -> None:
    """Validate configuration before starting the pipeline."""

    if not settings.database_url:
        raise ValueError(
            "DATABASE_URL is missing. Set it in your .env file."
        )

    if settings.database_batch_size <= 0:
        raise ValueError("All batch sizes must be positive.")

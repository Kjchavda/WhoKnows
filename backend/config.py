import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from the project root's .env file.
load_dotenv()


@dataclass(frozen=True)
class DbSettings:
    # Database
    database_url: str = os.getenv("DATABASE_URL", "")

    github_client_id: str = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    github_redirect_uri: str = os.getenv("GITHUB_REDIRECT_URI", "")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    session_cookie_secure: bool = os.getenv(
        "SESSION_COOKIE_SECURE",
        "true",
    ).lower() in {"1", "true", "yes"}

    redis_url: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0",
    )

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

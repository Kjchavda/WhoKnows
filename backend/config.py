import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load environment variables from the project root's .env file.
load_dotenv()


def _admin_github_ids_from_env() -> tuple[frozenset[int], tuple[str, ...]]:
    ids = set()
    invalid_entries = []
    for entry in os.getenv("ADMIN_GITHUB_IDS", "").split(","):
        value = entry.strip()
        if not value:
            continue
        try:
            ids.add(int(value))
        except ValueError:
            invalid_entries.append(value)
    return frozenset(ids), tuple(invalid_entries)


@dataclass(frozen=True)
class DbSettings:
    # Database
    database_url: str = os.getenv("DATABASE_URL", "")

    github_client_id: str = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    github_redirect_uri: str = os.getenv("GITHUB_REDIRECT_URI", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    session_cookie_samesite: str = os.getenv(
        "SESSION_COOKIE_SAMESITE",
        "lax",
    ).lower()
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
    admin_github_ids: frozenset[int] = field(init=False)
    _invalid_admin_github_id_entries: tuple[str, ...] = field(
        init=False,
        repr=False,
    )
    search_rate_limit_per_minute: int = int(
        os.getenv("SEARCH_RATE_LIMIT_PER_MINUTE", "30")
    )
    max_items_per_index: int = int(
        os.getenv("MAX_ITEMS_PER_INDEX", "8000")
    )
    max_active_index_jobs_per_user: int = int(
        os.getenv("MAX_ACTIVE_INDEX_JOBS_PER_USER", "1")
    )

    # Pipeline
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self) -> None:
        ids, invalid_entries = _admin_github_ids_from_env()
        object.__setattr__(self, "admin_github_ids", ids)
        object.__setattr__(
            self,
            "_invalid_admin_github_id_entries",
            invalid_entries,
        )


settings = DbSettings()


def validate_settings() -> None:
    """Validate configuration before starting the pipeline."""

    if not settings.database_url:
        raise ValueError(
            "DATABASE_URL is missing. Set it in your .env file."
        )

    if settings.database_batch_size <= 0:
        raise ValueError("All batch sizes must be positive.")

    if settings._invalid_admin_github_id_entries:
        invalid_entries = ", ".join(settings._invalid_admin_github_id_entries)
        raise ValueError(
            "ADMIN_GITHUB_IDS must contain comma-separated integers; "
            f"invalid entries: {invalid_entries}"
        )

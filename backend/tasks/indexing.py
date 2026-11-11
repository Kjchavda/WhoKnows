from backend.db import Database
from backend.services.repository_service import RepositoryService
from embeddings.embedder import Embedder


_embedder: Embedder | None = None


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def index_repository_task(
    full_name: str,
    user_id: int | None = None,
    grant_owner: bool = False,
):
    db = Database()
    db.open()

    try:
        service = RepositoryService(db, _get_embedder())
        repository = service.index_repository(
            full_name,
            indexed_by=user_id,
            grant_owner=grant_owner,
        )

        return repository

    finally:
        db.close()
from backend.db import Database
from backend.services.repository_service import RepositoryService
from embeddings.embedder import Embedder


def index_repository_task(full_name: str):
    db = Database()
    db.open()
    embedder = Embedder()

    try:
        service = RepositoryService(db, embedder)
        repository = service.index_repository(full_name)

        return repository

    finally:
        db.close()
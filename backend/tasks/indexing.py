from backend.db import Database
from backend.services.repository_service import RepositoryService


def index_repository_task(full_name: str):
    db = Database()
    db.open()

    try:
        service = RepositoryService(db)
        repository = service.index_repository(full_name)

        return repository

    finally:
        db.close()
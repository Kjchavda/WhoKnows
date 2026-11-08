
from backend.services.repository_service import RepositoryService
from backend.db import Database

db = Database()
db.open()

indexer = RepositoryService(db)

indexer.index_repository("redis/redis-py")

db.close()
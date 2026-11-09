import redis
from rq import Queue

from backend.config import settings


redis_connection = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=False,
)

indexing_queue = Queue(
    "indexing",
    connection=redis_connection,
)
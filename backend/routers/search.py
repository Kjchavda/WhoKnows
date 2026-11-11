
import logging
import time

from redis.exceptions import RedisError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.access import ensure_repo_read, get_current_user
from backend.config import settings
from backend.redis_queue import redis_connection
from backend.services.search_service import SearchService


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


class SearchRequest(BaseModel):
    repo_id: int = Field(gt=0)
    query: str = Field(min_length=1)
    limit: int = Field(default=100, gt=0, le=500)


def get_search_service(request: Request):
    db = request.app.state.db
    embedder = request.app.state.embedder
    return SearchService(db, embedder)


@router.post("/")
def search_repository(
    body: SearchRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
):
    ensure_repo_read(request.app.state.db, body.repo_id, user)

    now = int(time.time())
    epoch_minute = now // 60
    rate_limit_key = (
        f"ratelimit:search:{user['id']}:{epoch_minute}"
    )
    try:
        request_count = redis_connection.incr(rate_limit_key)
        if request_count == 1:
            redis_connection.expire(rate_limit_key, 60)
    except RedisError:
        logger.exception("Could not apply search rate limit; allowing request")
    else:
        if request_count > settings.search_rate_limit_per_minute:
            retry_after = 60 - now % 60
            raise HTTPException(
                status_code=429,
                detail="Search rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

    try:
        results = service.search(
            repo_id=body.repo_id,
            query=body.query,
            limit=body.limit,
        )
        return {
            "repo_id": body.repo_id,
            "query": body.query,
            "results": results,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

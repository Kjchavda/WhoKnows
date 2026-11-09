
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.services.search_service import SearchService


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
    return SearchService(db)


@router.post("/")
def search_repository(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service),
):
    try:
        results = service.search(
            repo_id=request.repo_id,
            query=request.query,
            limit=request.limit,
        )
        return {
            "repo_id": request.repo_id,
            "query": request.query,
            "results": results,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

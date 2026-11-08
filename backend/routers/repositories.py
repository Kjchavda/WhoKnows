
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.services.repository_service import RepositoryService


router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
)


class IndexRepositoryRequest(BaseModel):
    full_name: str


def get_repository_service(request: Request):
    db = request.app.state.db
    return RepositoryService(db)


@router.get("/")
def list_repositories(
    service: RepositoryService = Depends(get_repository_service),
):
    return service.list_repositories()


@router.get("/{repo_id}")
def get_repository(
    repo_id: int,
    service: RepositoryService = Depends(get_repository_service),
):
    repository = service.get_repository(repo_id)

    if repository is None:
        raise HTTPException(
            status_code=404,
            detail="Repository not found",
        )

    return repository


@router.post("/index")
def index_repository(
    request: IndexRepositoryRequest,
    service: RepositoryService = Depends(get_repository_service),
):
    try:
        return service.index_repository(request.full_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

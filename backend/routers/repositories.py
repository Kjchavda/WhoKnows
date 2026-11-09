from rq.job import Job
from rq.exceptions import NoSuchJobError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.services.repository_service import RepositoryService
from backend.redis_queue import indexing_queue
from backend.tasks.indexing import index_repository_task
from backend.redis_queue import redis_connection


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


@router.post("/index", status_code=202)
def index_repository(request: IndexRepositoryRequest):
    full_name = request.full_name.strip()

    parts = full_name.split("/")
    if len(parts) != 2 or not all(parts):
        raise HTTPException(
            status_code=400,
            detail="Repository must be in OWNER/NAME format",
        )

    job = indexing_queue.enqueue(
        index_repository_task,
        full_name,
        job_timeout="2h",
        result_ttl=86400,
        failure_ttl=604800,
    )

    return {
        "message": "Repository indexing queued",
        "job_id": job.id,
        "repository": full_name,
        "status": "queued",
    }

@router.get("/jobs/{job_id}")
def get_indexing_job(job_id: str):
    try:
        job = Job.fetch(
            job_id,
            connection=redis_connection,
        )
    except NoSuchJobError:
        raise HTTPException(
            status_code=404,
            detail="Indexing job not found",
        )

    status = job.get_status(refresh=True)

    response = {
        "job_id": job.id,
        "status": status.value,
    }

    if status.value == "finished":
        response["result"] = job.result

    elif status.value == "failed":
        response["error"] = "Repository indexing failed"

    return response

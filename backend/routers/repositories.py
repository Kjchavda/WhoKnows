import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.registry import StartedJobRegistry

from backend.access import (
    ensure_can_index,
    ensure_repo_read,
    get_current_user,
    is_platform_admin,
    is_repo_owner,
)
from backend.config import settings
from backend.redis_queue import indexing_queue, redis_connection
from backend.services.repository_service import RepositoryService
from backend.tasks.indexing import index_repository_task
from crawler.crawler import API_URL, GitHub


router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
)


class IndexRepositoryRequest(BaseModel):
    full_name: str


def get_repository_service(request: Request):
    db = request.app.state.db
    embedder = request.app.state.embedder
    return RepositoryService(db, embedder)


@router.get("/")
def list_repositories(
    user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    return service.list_repositories(user)


@router.get(
    "/{repo_id}",
)
def get_repository(
    repo_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    ensure_repo_read(request.app.state.db, repo_id, user)
    repository = service.get_repository(repo_id)

    if repository is None:
        raise HTTPException(
            status_code=404,
            detail="Repository not found",
        )

    return repository


@router.get(
    "/{repo_id}/stats",
)
def get_repository_stats(
    repo_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    ensure_repo_read(request.app.state.db, repo_id, user)
    stats = service.get_repository_stats(repo_id)

    if stats is None:
        raise HTTPException(
            status_code=404,
            detail="Repository not found",
        )

    return {
        "issues": stats["issues"] or 0,
        "pull_requests": stats["pull_requests"] or 0,
        "developers": stats["developers"] or 0,
        "chunks": stats["chunks"] or 0,
        "last_indexed_at": stats["last_indexed_at"],
    }


def _active_index_jobs() -> list[Job]:
    jobs = list(indexing_queue.jobs)
    registry = StartedJobRegistry(queue=indexing_queue)
    for job_id in registry.get_job_ids():
        try:
            jobs.append(Job.fetch(job_id, connection=redis_connection))
        except NoSuchJobError:
            continue
    return jobs


@router.post(
    "/index",
    status_code=202,
)
def index_repository(
    body: IndexRepositoryRequest,
    user: dict = Depends(get_current_user),
):
    full_name = body.full_name.strip()

    parts = full_name.split("/")
    if len(parts) != 2 or not all(parts):
        raise HTTPException(
            status_code=400,
            detail="Repository must be in OWNER/NAME format",
        )
    owner, name = parts

    admin = is_platform_admin(user)
    if not admin and owner.lower() != user["username"].lower():
        raise HTTPException(
            status_code=403,
            detail=(
                "You can only index repositories owned by your own GitHub account"
            ),
        )

    github = GitHub()
    try:
        github_repo, _ = github.get_json(
            f"{API_URL}/repos/{owner}/{name}"
        )
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Repository not found on GitHub",
            ) from exc
        raise HTTPException(
            status_code=503,
            detail="Could not verify repository, try again",
        ) from exc
    except (requests.RequestException, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not verify repository, try again",
        ) from exc

    owner_data = (
        github_repo.get("owner")
        if isinstance(github_repo, dict)
        else None
    )
    if (
        not isinstance(github_repo, dict)
        or not isinstance(github_repo.get("full_name"), str)
        or not isinstance(github_repo.get("private"), bool)
        or not isinstance(owner_data, dict)
        or not isinstance(owner_data.get("id"), int)
        or not isinstance(owner_data.get("type"), str)
    ):
        raise HTTPException(
            status_code=503,
            detail="Could not verify repository, try again",
        )

    if github_repo.get("private"):
        raise HTTPException(
            status_code=400,
            detail="Only public repositories are supported",
        )

    ensure_can_index(user, github_repo)
    full_name = github_repo["full_name"]

    if not admin:
        try:
            size_data, _ = github.get_json(
                f"{API_URL}/search/issues",
                params={"q": f"repo:{full_name}", "per_page": 1},
            )
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Could not verify repository size, try again",
            ) from exc

        total_count = (
            size_data.get("total_count")
            if isinstance(size_data, dict)
            else None
        )
        if (
            not isinstance(total_count, int)
            or isinstance(total_count, bool)
            or total_count < 0
        ):
            raise HTTPException(
                status_code=503,
                detail="Could not verify repository size, try again",
            )
        if total_count > settings.max_items_per_index:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Repository is too large to index "
                    f"({total_count} items, limit "
                    f"{settings.max_items_per_index})"
                ),
            )

    active_jobs = _active_index_jobs()
    if not admin:
        user_jobs = [
            job
            for job in active_jobs
            if job.meta.get("user_id") == user["id"]
        ]
        if len(user_jobs) >= settings.max_active_index_jobs_per_user:
            raise HTTPException(
                status_code=429,
                detail="You already have an indexing job in progress",
            )

    for job in active_jobs:
        if job.meta.get("full_name") == full_name:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Repository indexing is already in progress",
                    "job_id": job.id,
                },
            )

    job = indexing_queue.enqueue(
        index_repository_task,
        full_name,
        user["id"],
        is_repo_owner(user, github_repo),
        job_timeout="2h",
        result_ttl=86400,
        failure_ttl=604800,
        meta={"user_id": user["id"], "full_name": full_name},
    )

    return {
        "message": "Repository indexing queued",
        "job_id": job.id,
        "repository": full_name,
        "status": "queued",
    }


@router.get("/jobs/{job_id}")
def get_indexing_job(
    job_id: str,
    user: dict = Depends(get_current_user),
):
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

    if (
        job.meta.get("user_id") != user["id"]
        and not is_platform_admin(user)
    ):
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

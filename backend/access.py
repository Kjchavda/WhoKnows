from typing import Any

from fastapi import HTTPException, Request

from backend.config import settings
from backend.dependencies import require_current_user_id
from backend.services.user_service import UserService


def get_current_user(request: Request) -> dict[str, Any]:
    user_id = require_current_user_id(request)
    user = UserService(request.app.state.db).get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


def is_platform_admin(user: dict[str, Any]) -> bool:
    return user["github_id"] in settings.admin_github_ids


def repo_role(
    db: Any,
    repo_id: int,
    user: dict[str, Any],
) -> str | None:
    row = db.fetch_one(
        """
        SELECT r.visibility, ur.access_role
        FROM repositories r
        LEFT JOIN user_repositories ur
          ON ur.repo_id = r.github_id AND ur.user_id = %s
        WHERE r.github_id = %s
        """,
        (user["id"], repo_id),
    )
    if row is None:
        return None

    if is_platform_admin(user):
        return "admin"
    if row["access_role"] is not None:
        return row["access_role"]
    if row["visibility"] == "public":
        return "viewer"
    return None


def ensure_repo_read(
    db: Any,
    repo_id: int,
    user: dict[str, Any],
) -> str:
    role = repo_role(db, repo_id, user)
    if role is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return role


def is_repo_owner(
    user: dict[str, Any],
    github_repo: dict[str, Any],
) -> bool:
    owner = github_repo.get("owner")
    return (
        isinstance(owner, dict)
        and owner.get("id") == user["github_id"]
        and owner.get("type") == "User"
    )


def ensure_can_index(
    user: dict[str, Any],
    github_repo: dict[str, Any],
) -> bool:
    if github_repo.get("private"):
        raise HTTPException(
            status_code=400,
            detail="Only public repositories are supported",
        )
    if is_platform_admin(user) or is_repo_owner(user, github_repo):
        return True
    raise HTTPException(
        status_code=403,
        detail=(
            "You can only index repositories owned by your own GitHub account"
        ),
    )

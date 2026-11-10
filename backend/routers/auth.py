import base64
import hashlib
import hmac
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from backend.config import settings
from backend.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_SCOPES = "read:user"
SESSION_COOKIE = "whoknows_session"
OAUTH_STATE_COOKIE = "whoknows_oauth_state"
SESSION_MAX_AGE = 60 * 60 * 24 * 7


def _require_session_secret() -> None:
    if len(settings.session_secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="SESSION_SECRET must contain at least 32 characters.",
        )


def _require_github_oauth_settings() -> None:
    _require_session_secret()
    if not all(
        (
            settings.github_client_id,
            settings.github_client_secret,
            settings.github_redirect_uri,
        )
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID, "
                "GITHUB_CLIENT_SECRET, and GITHUB_REDIRECT_URI in your .env file."
            ),
        )


def _session_cookie_value(user_id: int) -> str:
    expires_at = int(time.time()) + SESSION_MAX_AGE
    payload = f"{user_id}.{expires_at}"
    signature = hmac.new(
        settings.session_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload}.{encoded_signature}"


def _session_user_id(cookie_value: str | None) -> int | None:
    if not cookie_value:
        return None

    try:
        user_id_text, expires_at_text, signature = cookie_value.split(".")
        user_id = int(user_id_text)
        expires_at = int(expires_at_text)
    except ValueError:
        return None

    try:
        signature_bytes = signature.encode("ascii")
    except UnicodeEncodeError:
        return None

    payload = f"{user_id_text}.{expires_at_text}"
    expected_signature = base64.urlsafe_b64encode(
        hmac.new(
            settings.session_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).digest()
    ).decode().rstrip("=")

    if (
        user_id <= 0
        or expires_at <= int(time.time())
        or not hmac.compare_digest(
            signature_bytes,
            expected_signature.encode("ascii"),
        )
    ):
        return None

    return user_id


def _set_auth_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=_session_cookie_value(user_id),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def _user_service(request: Request) -> UserService:
    return UserService(request.app.state.db)


async def _fetch_github_user(code: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri,
                },
            )
            token_response.raise_for_status()
            token_payload = token_response.json()

            if not isinstance(token_payload, dict):
                raise HTTPException(
                    status_code=502,
                    detail="GitHub returned an invalid OAuth token response.",
                )

            access_token = token_payload.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise HTTPException(
                    status_code=502,
                    detail="GitHub did not return an OAuth access token.",
                )

            user_response = await client.get(
                GITHUB_USER_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            user_response.raise_for_status()
            profile = user_response.json()

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not complete the GitHub OAuth exchange.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="GitHub returned an invalid OAuth response.",
        ) from exc

    if (
        not isinstance(profile, dict)
        or type(profile.get("id")) is not int
        or not isinstance(profile.get("login"), str)
        or not profile["login"]
        or profile.get("email") is not None
        and not isinstance(profile.get("email"), str)
        or profile.get("avatar_url") is not None
        and not isinstance(profile.get("avatar_url"), str)
    ):
        raise HTTPException(
            status_code=502,
            detail="GitHub returned an invalid user profile.",
        )

    return profile


@router.get("/github")
def github_login() -> RedirectResponse:
    _require_github_oauth_settings()

    state = secrets.token_urlsafe(32)
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": GITHUB_SCOPES,
            "state": state,
        }
    )
    response = RedirectResponse(f"{GITHUB_AUTHORIZE_URL}?{params}")
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/github/callback")
async def github_callback(
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    _require_github_oauth_settings()

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    _clear_oauth_state_cookie(response)

    if error:
        raise HTTPException(
            status_code=400,
            detail="GitHub authorization was not completed.",
        )

    if (
        not code
        or not state
        or not expected_state
        or not hmac.compare_digest(state.encode(), expected_state.encode())
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state.",
        )

    github_user = await _fetch_github_user(code)
    user = _user_service(request).save_github_user(github_user)

    _set_auth_cookie(response, user["id"])
    return {"user": user}


@router.get("/me")
async def current_user(request: Request) -> dict[str, Any]:
    _require_session_secret()

    user_id = _session_user_id(request.cookies.get(SESSION_COOKIE))
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user = _user_service(request).get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return {"user": user}


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    _require_session_secret()
    _clear_auth_cookie(response)
    return {"message": "Logged out."}
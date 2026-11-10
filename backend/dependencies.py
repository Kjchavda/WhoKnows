import base64
import hashlib
import hmac
import time

from fastapi import HTTPException, Request

from backend.config import settings

SESSION_COOKIE = "whoknows_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7


def require_session_secret() -> None:
    if len(settings.session_secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="SESSION_SECRET must contain at least 32 characters.",
        )
    if settings.session_cookie_samesite not in {"lax", "strict", "none"}:
        raise HTTPException(
            status_code=503,
            detail=(
                "SESSION_COOKIE_SAMESITE must be 'lax', 'strict', or 'none'."
            ),
        )
    if (
        settings.session_cookie_samesite == "none"
        and not settings.session_cookie_secure
    ):
        raise HTTPException(
            status_code=503,
            detail="SESSION_COOKIE_SECURE must be true when SameSite is 'none'.",
        )


def session_cookie_value(user_id: int) -> str:
    expires_at = int(time.time()) + SESSION_MAX_AGE
    payload = f"{user_id}.{expires_at}"
    signature = hmac.new(
        settings.session_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload}.{encoded_signature}"


def session_user_id(cookie_value: str | None) -> int | None:
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


def require_current_user_id(request: Request) -> int:
    require_session_secret()
    user_id = session_user_id(request.cookies.get(SESSION_COOKIE))
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user_id

"""Verify with Supabase Auth itself: supports both legacy and rotated signing keys.

No JWT payload is trusted locally. The configured project's /user endpoint verifies
signature, expiry and accepted claims. Provider outages are NOT invalid sessions.
"""

from dataclasses import dataclass
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError


@dataclass(frozen=True)
class VerifiedIdentity:
    subject: str
    email: str
    display_name: str


def unauthorized():
    return AppError("UNAUTHORIZED", "Your session has expired. Please sign in again.", 401)


def verify_access_token(token: str) -> VerifiedIdentity:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key.get_secret_value():
        raise AppError("AUTH_UNAVAILABLE", "Sign-in is not configured on the server.", 503)
    try:
        response = httpx.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.supabase_anon_key.get_secret_value(),
            },
            timeout=8,
            follow_redirects=False,
        )
    except httpx.HTTPError:
        raise AppError(
            "AUTH_UNAVAILABLE",
            "Sign-in verification is temporarily unavailable. Please retry.",
            503,
        ) from None
    if response.status_code in (401, 403):
        raise unauthorized()
    if response.status_code != 200:
        raise AppError(
            "AUTH_UNAVAILABLE",
            "Sign-in verification is temporarily unavailable. Please retry.",
            503,
        )
    try:
        data = response.json()
        subject = str(UUID(data["id"]))
        email = data.get("email") or ""
        if not isinstance(email, str) or len(email) > 254 or data.get("is_anonymous", False):
            raise ValueError()
        metadata = data.get("user_metadata") or {}
        name = (
            metadata.get("display_name")
            or metadata.get("full_name")
            or email.split("@")[0]
            or "Student"
        )
        if not isinstance(name, str):
            name = "Student"
        return VerifiedIdentity(subject, email, name.strip()[:120] or "Student")
    except (ValueError, KeyError, TypeError, AttributeError):
        raise AppError(
            "AUTH_UNAVAILABLE", "Sign-in verification returned an unexpected response.", 503
        ) from None

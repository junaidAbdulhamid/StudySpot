"""A tiny GoTrue-shaped identity boundary used only by Playwright.

Production never imports this module. It lets the real supabase-js client and
the real backend verifier exercise their HTTP contracts without test accounts
or secrets in an external Supabase project.
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/test-auth/auth/v1", include_in_schema=False)
users: dict[str, dict] = {}
access_tokens: dict[str, str] = {}
refresh_tokens: dict[str, str] = {}


def _user(identifier: str, email: str, name: str):
    now = datetime.now(UTC).isoformat()
    return {
        "id": identifier,
        "aud": "authenticated",
        "role": "authenticated",
        "email": email,
        "email_confirmed_at": now,
        "phone": "",
        "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {"display_name": name},
        "identities": [],
        "created_at": now,
        "updated_at": now,
        "is_anonymous": False,
    }


def _session(user: dict):
    access = f"e2e-access-{user['id']}-{uuid4()}"
    refresh = f"e2e-refresh-{user['id']}-{uuid4()}"
    access_tokens[access] = user["id"]
    refresh_tokens[refresh] = user["id"]
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": 3600,
        "user": user,
    }


for identifier, email, name in (
    ("10000000-0000-4000-8000-000000000001", "alex@example.edu", "Alex"),
    ("20000000-0000-4000-8000-000000000002", "blair@example.edu", "Blair"),
):
    users[email] = _user(identifier, email, name)


@router.post("/signup")
async def signup(request: Request):
    body = await request.json()
    email = str(body.get("email", "")).lower()
    if email in users:
        raise HTTPException(400, detail="User already registered")
    user = _user(str(uuid4()), email, email.split("@")[0].title())
    users[email] = user
    return {**_session(user)}


@router.post("/token")
async def token(request: Request):
    body = await request.json()
    grant = request.query_params.get("grant_type")
    if grant == "refresh_token":
        identifier = refresh_tokens.get(str(body.get("refresh_token", "")))
        user = next((item for item in users.values() if item["id"] == identifier), None)
    else:
        user = users.get(str(body.get("email", "")).lower())
    if user is None or (grant != "refresh_token" and body.get("password") != "StudySpot123!"):
        return JSONResponse(
            status_code=400,
            content={
                "code": "invalid_credentials",
                "error_code": "invalid_credentials",
                "message": "Invalid login credentials",
            },
        )
    return _session(user)


@router.get("/user")
def current_user(authorization: str = Header(default="")):
    identifier = access_tokens.get(authorization.removeprefix("Bearer "))
    if not identifier:
        raise HTTPException(401, detail="Invalid token")
    return next(item for item in users.values() if item["id"] == identifier)


@router.post("/logout", status_code=204)
def logout(authorization: str = Header(default="")):
    access_tokens.pop(authorization.removeprefix("Bearer "), None)
    return Response(status_code=204)

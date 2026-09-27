"""Coverage for the code the `client` fixture bypasses: token verification and
account synchronization. Route-level auth behavior (401/503 status codes) is
covered in test_api.py via the unauthenticated `anonymous_client` fixture.
"""

from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select

from app.core.auth import VerifiedIdentity, verify_access_token
from app.core.exceptions import AppError
from app.models import Favorite, User, UserPreference
from app.services.accounts import AccountService


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


def configure(monkeypatch, url="https://project.supabase.co", key="anon-key"):
    settings = SimpleNamespace(
        supabase_url=url, supabase_anon_key=SimpleNamespace(get_secret_value=lambda: key)
    )
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)
    return settings


def test_verify_rejects_when_supabase_not_configured(monkeypatch):
    configure(monkeypatch, url="", key="")
    with pytest.raises(AppError) as excinfo:
        verify_access_token("some-token")
    assert excinfo.value.status == 503
    assert excinfo.value.code == "AUTH_UNAVAILABLE"


def test_verify_rejects_on_network_error(monkeypatch):
    configure(monkeypatch)

    def raise_network_error(*args, **kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr("app.core.auth.httpx.get", raise_network_error)
    with pytest.raises(AppError) as excinfo:
        verify_access_token("some-token")
    assert excinfo.value.status == 503
    assert excinfo.value.code == "AUTH_UNAVAILABLE"


@pytest.mark.parametrize("status", [401, 403])
def test_verify_rejects_invalid_session(monkeypatch, status):
    configure(monkeypatch)
    monkeypatch.setattr("app.core.auth.httpx.get", lambda *a, **k: FakeResponse(status))
    with pytest.raises(AppError) as excinfo:
        verify_access_token("expired-token")
    assert excinfo.value.status == 401
    assert excinfo.value.code == "UNAUTHORIZED"


def test_verify_rejects_provider_outage(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr("app.core.auth.httpx.get", lambda *a, **k: FakeResponse(500))
    with pytest.raises(AppError) as excinfo:
        verify_access_token("some-token")
    assert excinfo.value.status == 503
    assert excinfo.value.code == "AUTH_UNAVAILABLE"


@pytest.mark.parametrize(
    "body",
    [
        {"id": "not-a-uuid", "email": "a@b.com"},
        {"email": "a@b.com"},
        {"id": str(uuid4()), "email": "a@b.com", "is_anonymous": True},
        {"id": str(uuid4()), "email": "x" * 260},
    ],
)
def test_verify_rejects_malformed_or_anonymous_identity(monkeypatch, body):
    configure(monkeypatch)
    monkeypatch.setattr("app.core.auth.httpx.get", lambda *a, **k: FakeResponse(200, body))
    with pytest.raises(AppError) as excinfo:
        verify_access_token("some-token")
    assert excinfo.value.status == 503
    assert excinfo.value.code == "AUTH_UNAVAILABLE"


def test_verify_accepts_valid_session_and_derives_display_name(monkeypatch):
    configure(monkeypatch)
    subject = str(uuid4())
    body = {
        "id": subject,
        "email": "casey@example.edu",
        "user_metadata": {"full_name": "Casey Lee"},
    }
    monkeypatch.setattr("app.core.auth.httpx.get", lambda *a, **k: FakeResponse(200, body))
    identity = verify_access_token("valid-token")
    assert identity.subject == subject
    assert identity.email == "casey@example.edu"
    assert identity.display_name == "Casey Lee"


def test_verify_falls_back_to_email_prefix_then_student(monkeypatch):
    configure(monkeypatch)
    subject = str(uuid4())
    monkeypatch.setattr(
        "app.core.auth.httpx.get",
        lambda *a, **k: FakeResponse(200, {"id": subject, "email": "casey@example.edu"}),
    )
    assert verify_access_token("t").display_name == "casey"
    monkeypatch.setattr(
        "app.core.auth.httpx.get",
        lambda *a, **k: FakeResponse(200, {"id": subject, "email": ""}),
    )
    assert verify_access_token("t").display_name == "Student"


def test_synchronize_creates_user_with_default_preferences(db):
    subject = str(uuid4())
    user = AccountService(db).synchronize(
        VerifiedIdentity(subject, "new@example.edu", "New Student")
    )
    assert user.auth_provider_id == subject
    assert user.email == "new@example.edu"
    assert user.display_name == "New Student"
    assert user.onboarding_completed is False
    preference = db.scalar(select_preference(db, user.id))
    assert preference is not None
    assert preference.noise_preference.value == "quiet"


def test_synchronize_updates_email_but_preserves_display_name(db):
    subject = str(uuid4())
    service = AccountService(db)
    first = service.synchronize(VerifiedIdentity(subject, "old@example.edu", "Original Name"))
    assert first.display_name == "Original Name"
    second = service.synchronize(VerifiedIdentity(subject, "new@example.edu", "Renamed Elsewhere"))
    assert second.id == first.id
    assert second.email == "new@example.edu"
    assert second.display_name == "Original Name"


def test_synchronize_is_idempotent_for_preferences(db):
    subject = str(uuid4())
    service = AccountService(db)
    identity = VerifiedIdentity(subject, "a@b.edu", "A")
    user = service.synchronize(identity)
    service.synchronize(identity)
    service.synchronize(identity)
    count = db.scalar(
        select(func.count()).select_from(UserPreference).where(UserPreference.user_id == user.id)
    )
    assert count == 1


def test_delete_application_data_cascades(db):
    subject = str(uuid4())
    user = AccountService(db).synchronize(VerifiedIdentity(subject, "gone@example.edu", "Gone"))
    db.add(Favorite(user_id=user.id, location_id="zone-1"))
    db.commit()
    AccountService(db).delete_application_data(user)
    assert db.get(User, user.id) is None
    assert db.scalar(select_preference(db, user.id)) is None
    assert db.scalar(select(Favorite).where(Favorite.user_id == user.id)) is None


def select_preference(db, user_id):
    return select(UserPreference).where(UserPreference.user_id == user_id)

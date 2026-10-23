import pytest
from sqlalchemy import func, select
from app.core.config import get_settings
from app.db.models import User
from app.services.auth_service import AuthService, RegistrationClosedError
from app.services.auth_context_service import AuthContextService, InvalidAccessTokenError
from app.core.security import create_access_token
from tests.api.test_auth_notifications_api import _make_client
from app.main import app


@pytest.fixture
def setup(monkeypatch):
    client, session = _make_client(monkeypatch)
    monkeypatch.setenv('REGISTRATION_MODE', 'invitation')
    get_settings.cache_clear()
    monkeypatch.setattr('app.services.auth_service.notify_new_pending_user', lambda **kwargs: None)
    yield client, session
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_uninvited_verified_login_creates_no_user_or_token(setup, monkeypatch):
    client, factory = setup
    monkeypatch.setattr('app.services.auth_service.verify_and_extract_telegram_user', lambda **kwargs: {'telegram_id': '555001'})
    response = client.post('/api/v1/auth/telegram', json={'init_data': 'verified'})
    assert response.status_code == 403
    assert 'access_token' not in response.json()
    with factory() as db: assert db.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize('status', ['approved', 'active'])
def test_existing_approved_user_still_logs_in(setup, status):
    _, factory = setup
    with factory() as db:
        service = AuthService(db)
        service.user_repo.create_with_telegram_identity('555001', 'Existing', None, status=status)
        db.commit()
        assert service._upsert_telegram_user({'telegram_id': '555001'})


def test_admin_and_invited_user_can_register(setup, monkeypatch):
    _, factory = setup
    monkeypatch.setenv('REGISTRATION_ALLOWED_TELEGRAM_IDS', '555001')
    get_settings.cache_clear()
    with factory() as db:
        service = AuthService(db)
        service._upsert_telegram_user({'telegram_id': '281896361'})
        service._upsert_telegram_user({'telegram_id': '555001'})
        assert service.user_repo.get_by_telegram_id('281896361').status == 'approved'
        assert service.user_repo.get_by_telegram_id('555001').status == 'pending'


def test_rejected_user_cannot_login_even_if_invited_and_old_token_is_revoked(setup, monkeypatch):
    _, factory = setup
    monkeypatch.setenv('REGISTRATION_ALLOWED_TELEGRAM_IDS', '555001'); get_settings.cache_clear()
    with factory() as db:
        service = AuthService(db)
        user = service.user_repo.create_with_telegram_identity('555001', 'Rejected', None, status='rejected')
        db.commit()
        token = create_access_token({'sub': str(user.id)})
        with pytest.raises(RegistrationClosedError): service._upsert_telegram_user({'telegram_id': '555001'})
        with pytest.raises(InvalidAccessTokenError): AuthContextService(db).resolve_user_from_authorization_header('Bearer ' + token)

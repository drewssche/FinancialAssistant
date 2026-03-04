from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user, get_current_user_id
from app.core.security import create_access_token


def test_get_current_user_rejects_missing_header():
    with pytest.raises(HTTPException, match="Missing Authorization header"):
        get_current_user(authorization=None, db=None)


def test_get_current_user_rejects_invalid_scheme():
    with pytest.raises(HTTPException, match="Invalid auth scheme"):
        get_current_user(authorization="Token abc", db=None)


def test_get_current_user_accepts_valid_bearer(monkeypatch):
    token = create_access_token({"sub": "123"})

    def fake_get_by_id(self, user_id: int):
        return SimpleNamespace(id=user_id)

    monkeypatch.setattr("app.api.deps.UserRepository.get_by_id", fake_get_by_id)

    user = get_current_user(authorization=f"Bearer {token}", db=object())
    assert get_current_user_id(user) == 123

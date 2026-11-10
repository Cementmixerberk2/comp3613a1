"""Unit tests for AuthService. The user repository is mocked, so no database is used."""

from unittest.mock import MagicMock

import jwt

from app.config import get_settings
from app.models.user import User
from app.services.auth_service import AuthService
from app.utilities.security import encrypt_password, verify_password


def _user(username="alice", password="pass123", role="student", user_id=1):
    return User(id=user_id, username=username, email=f"{username}@example.com",
                password=encrypt_password(password), role=role)


def test_authenticate_returns_token_for_valid_credentials():
    repo = MagicMock()
    repo.get_by_username.return_value = _user()
    token = AuthService(repo).authenticate_user("alice", "pass123")
    payload = jwt.decode(token, get_settings().secret_key, algorithms=[get_settings().jwt_algorithm])
    assert payload["sub"] == "1"
    assert payload["role"] == "student"


def test_authenticate_returns_none_for_wrong_password():
    repo = MagicMock()
    repo.get_by_username.return_value = _user()
    assert AuthService(repo).authenticate_user("alice", "wrong") is None


def test_authenticate_returns_none_for_unknown_user():
    repo = MagicMock()
    repo.get_by_username.return_value = None
    assert AuthService(repo).authenticate_user("nobody", "pass123") is None


def test_authenticate_resolves_login_alias():
    repo = MagicMock()
    northwind = _user("northwind", "companypass", "company", 2)
    repo.get_by_username.side_effect = lambda name: northwind if name == "northwind" else None
    assert AuthService(repo).authenticate_user("company1", "companypass") is not None


def test_register_user_hashes_password_and_sets_role():
    repo = MagicMock()
    repo.create.side_effect = lambda data: data
    created = AuthService(repo).register_user("carol", "carol@example.com", "pass123", role="company")
    assert created.role == "company"
    assert created.password != "pass123"
    assert verify_password("pass123", created.password)

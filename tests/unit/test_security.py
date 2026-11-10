"""Unit tests for app.utilities.security (password hashing and JWTs)."""

from datetime import timedelta

import jwt
import pytest

from app.config import get_settings
from app.utilities.security import (
    access_token_cookie_kwargs,
    create_access_token,
    encrypt_password,
    verify_password,
)


def test_encrypt_password_does_not_store_plain_text():
    hashed = encrypt_password("secret")
    assert hashed != "secret"
    assert "secret" not in hashed


def test_encrypt_password_salts_each_hash():
    assert encrypt_password("secret") != encrypt_password("secret")


def test_verify_password_accepts_correct_password():
    hashed = encrypt_password("secret")
    assert verify_password("secret", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = encrypt_password("secret")
    assert verify_password("wrong", hashed) is False


def test_access_token_contains_subject_role_and_expiry():
    token = create_access_token({"sub": "5", "role": "student"})
    payload = jwt.decode(token, get_settings().secret_key, algorithms=[get_settings().jwt_algorithm])
    assert payload["sub"] == "5"
    assert payload["role"] == "student"
    assert "exp" in payload


def test_expired_access_token_is_rejected():
    token = create_access_token({"sub": "5"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, get_settings().secret_key, algorithms=[get_settings().jwt_algorithm])


def test_cookie_is_http_only():
    assert access_token_cookie_kwargs()["httponly"] is True

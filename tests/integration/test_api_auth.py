"""Integration tests: authentication and authorization through the HTTP API."""

from tests.conftest import login


def test_login_returns_bearer_token_and_role(client, world):
    response = client.post("/api/auth/login", json={"username": "alice", "password": "pass123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "student"
    assert body["access_token"]


def test_login_with_wrong_password_returns_401(client, world):
    response = client.post("/api/auth/login", json={"username": "alice", "password": "nope"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_with_missing_fields_returns_422(client, world):
    response = client.post("/api/auth/login", json={"username": "alice"})
    assert response.status_code == 422


def test_me_returns_logged_in_user(client, world):
    headers = login(client, "acme")
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "acme"
    assert response.json()["role"] == "company"
    assert "password" not in response.json()


def test_web_login_cookie_also_authenticates_api(client, world):
    client.post("/login", data={"username": "alice", "password": "pass123"}, follow_redirects=False)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_register_creates_student_with_profile(client, world):
    response = client.post(
        "/api/auth/register",
        json={"username": "dana", "email": "dana@example.com", "password": "secret1"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "student"
    assert "password" not in response.json()
    headers = login(client, "dana", "secret1")
    assert client.get("/api/students/me/applications", headers=headers).json() == []


def test_register_duplicate_username_returns_409(client, world):
    response = client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "new@example.com", "password": "secret1"},
    )
    assert response.status_code == 409


def test_register_cannot_create_admin(client, world):
    response = client.post(
        "/api/auth/register",
        json={"username": "evil", "email": "evil@example.com", "password": "secret1", "role": "admin"},
    )
    assert response.status_code == 422


def test_protected_endpoint_without_token_returns_json_401(client, world):
    response = client.get("/api/positions")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")


def test_invalid_token_returns_401(client, world):
    response = client.get("/api/positions", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_users_list_is_admin_only(client, world):
    assert client.get("/api/users", headers=login(client, "alice")).status_code == 403
    response = client.get("/api/users", headers=login(client, "admin"))
    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()}
    assert {"admin", "acme", "alice", "bob"} <= usernames
    assert all("password" not in u for u in response.json())

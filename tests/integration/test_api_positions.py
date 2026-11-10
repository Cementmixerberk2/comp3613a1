"""Integration tests: Workflow 1, a company posts an internship position."""

from tests.conftest import login, make_company


def test_company_can_post_position_and_it_is_live_immediately(client, world):
    company = login(client, "acme")
    response = client.post(
        "/api/positions",
        json={"title": "Cloud Intern", "description": "Work on AWS tooling", "total_slots": 3},
        headers=company,
    )
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "Cloud Intern"
    assert created["available_slots"] == 3
    assert created["company"]["name"] == "Acme Ltd"

    # A student sees it straight away, with no approval step.
    student = login(client, "alice")
    titles = [p["title"] for p in client.get("/api/positions", headers=student).json()]
    assert "Cloud Intern" in titles


def test_student_cannot_post_position(client, world):
    response = client.post(
        "/api/positions",
        json={"title": "Fake", "description": "Fake", "total_slots": 1},
        headers=login(client, "alice"),
    )
    assert response.status_code == 403


def test_admin_cannot_post_position(client, world):
    response = client.post(
        "/api/positions",
        json={"title": "Fake", "description": "Fake", "total_slots": 1},
        headers=login(client, "admin"),
    )
    assert response.status_code == 403


def test_post_position_rejects_invalid_body(client, world):
    company = login(client, "acme")
    for body in (
        {"title": "", "description": "Desc", "total_slots": 1},
        {"title": "Title", "description": "Desc", "total_slots": 0},
        {"description": "Desc", "total_slots": 1},
    ):
        assert client.post("/api/positions", json=body, headers=company).status_code == 422


def test_post_position_rejects_whitespace_title(client, world):
    response = client.post(
        "/api/positions",
        json={"title": "   ", "description": "Desc", "total_slots": 1},
        headers=login(client, "acme"),
    )
    assert response.status_code == 400
    assert "Title cannot be blank" in response.json()["detail"]


def test_get_single_position(client, world):
    position_id = world["software"].id
    response = client.get(f"/api/positions/{position_id}", headers=login(client, "alice"))
    assert response.status_code == 200
    assert response.json()["title"] == "Software Intern"


def test_get_unknown_position_returns_404(client, world):
    assert client.get("/api/positions/9999", headers=login(client, "alice")).status_code == 404


def test_company_positions_lists_only_own_positions(client, world, session):
    make_company(session, "globex", "Globex")
    response = client.get("/api/company/positions", headers=login(client, "acme"))
    assert response.status_code == 200
    titles = {row["position"]["title"] for row in response.json()}
    assert titles == {"Software Intern", "Design Intern"}


def test_company_positions_is_company_only(client, world):
    assert client.get("/api/company/positions", headers=login(client, "alice")).status_code == 403

"""Integration tests: the three main workflows through the web UI (forms + cookie login)."""

from sqlmodel import select

from app.models.internship import Application, Position


def _web_login(client, username, password="pass123"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=False)


def test_login_redirects_each_role_to_its_dashboard(client, world):
    expected = {"admin": "/admin", "acme": "/company", "alice": "/student"}
    for username, path in expected.items():
        client.cookies.clear()
        response = _web_login(client, username)
        assert response.status_code == 303
        assert response.headers["location"].endswith(path)


def test_wrong_password_redirects_back_to_login(client, world):
    response = _web_login(client, "alice", "wrong")
    assert response.status_code == 303
    assert response.headers["location"].endswith("/login")


def test_dashboards_block_other_roles(client, world):
    _web_login(client, "alice")
    assert client.get("/company").status_code == 403


def test_full_internship_flow_through_web_pages(client, world, session):
    # 1. Company posts a position.
    _web_login(client, "acme")
    response = client.post(
        "/company/positions",
        data={"title": "Mobile Intern", "description": "Flutter apps", "total_slots": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    position = session.exec(select(Position).where(Position.title == "Mobile Intern")).one()

    # 2. Student sees it and applies.
    client.cookies.clear()
    _web_login(client, "alice")
    assert "Mobile Intern" in client.get("/student").text
    response = client.post(
        f"/student/positions/{position.id}/apply", data={"cover_note": "Keen"}, follow_redirects=False
    )
    assert response.status_code == 303
    application = session.exec(select(Application).where(Application.position_id == position.id)).one()
    assert application.status == "Submitted"

    # 3. Admin matches the application.
    client.cookies.clear()
    _web_login(client, "admin")
    response = client.post(f"/admin/applications/{application.id}/match", follow_redirects=False)
    assert response.status_code == 303
    session.refresh(application)
    session.refresh(position)
    assert application.status == "Matched"
    assert position.available_slots == 0

    # The company now sees the intern on its Assigned Interns tab.
    client.cookies.clear()
    _web_login(client, "acme")
    assert "Alice Smith" in client.get("/company?tab=interns").text

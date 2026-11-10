"""Integration tests: Workflow 2 (student applies) and Workflow 3 (admin matches)."""

from tests.conftest import login, make_application


def _apply(client, headers, position_id, note="I am interested"):
    return client.post(f"/api/positions/{position_id}/applications", json={"cover_note": note}, headers=headers)


# ---------------------------------------------------------------- Workflow 2: apply

def test_student_can_apply_and_status_is_submitted(client, world):
    student = login(client, "alice")
    response = _apply(client, student, world["software"].id)
    assert response.status_code == 201
    assert response.json()["status"] == "Submitted"
    assert response.json()["cover_note"] == "I am interested"

    mine = client.get("/api/students/me/applications", headers=student).json()
    assert [a["position"]["title"] for a in mine] == ["Software Intern"]


def test_cover_note_is_optional(client, world):
    response = client.post(
        f"/api/positions/{world['software'].id}/applications", json={}, headers=login(client, "alice")
    )
    assert response.status_code == 201
    assert response.json()["cover_note"] == ""


def test_student_cannot_apply_twice_to_same_position(client, world):
    student = login(client, "alice")
    assert _apply(client, student, world["software"].id).status_code == 201
    second = _apply(client, student, world["software"].id)
    assert second.status_code == 409
    assert "already applied" in second.json()["detail"]


def test_apply_to_unknown_position_returns_404(client, world):
    assert _apply(client, login(client, "alice"), 9999).status_code == 404


def test_company_cannot_apply(client, world):
    assert _apply(client, login(client, "acme"), world["software"].id).status_code == 403


def test_students_only_see_their_own_applications(client, world):
    _apply(client, login(client, "alice"), world["software"].id)
    bob_apps = client.get("/api/students/me/applications", headers=login(client, "bob")).json()
    assert bob_apps == []


# ---------------------------------------------------------------- Workflow 3: match

def test_admin_lists_all_applications(client, world):
    _apply(client, login(client, "alice"), world["software"].id)
    _apply(client, login(client, "bob"), world["design"].id)
    response = client.get("/api/applications", headers=login(client, "admin"))
    assert response.status_code == 200
    names = {a["student"]["full_name"] for a in response.json()}
    assert names == {"Alice Smith", "Bob Jones"}


def test_admin_can_filter_applications_by_position(client, world):
    _apply(client, login(client, "alice"), world["software"].id)
    _apply(client, login(client, "bob"), world["design"].id)
    response = client.get(
        f"/api/applications?position_id={world['design'].id}", headers=login(client, "admin")
    )
    assert [a["student"]["full_name"] for a in response.json()] == ["Bob Jones"]


def test_non_admin_cannot_list_or_match_applications(client, world):
    app_id = _apply(client, login(client, "alice"), world["software"].id).json()["id"]
    for user in ("alice", "acme"):
        headers = login(client, user)
        assert client.get("/api/applications", headers=headers).status_code == 403
        assert client.patch(f"/api/applications/{app_id}", json={"status": "Matched"}, headers=headers).status_code == 403


def test_admin_match_sets_status_and_reduces_slots(client, world):
    app_id = _apply(client, login(client, "alice"), world["software"].id).json()["id"]
    admin = login(client, "admin")
    response = client.patch(f"/api/applications/{app_id}", json={"status": "Matched"}, headers=admin)
    assert response.status_code == 200
    assert response.json()["status"] == "Matched"
    assert response.json()["position"]["available_slots"] == 1

    # The student sees the new status.
    mine = client.get("/api/students/me/applications", headers=login(client, "alice")).json()
    assert mine[0]["status"] == "Matched"


def test_matched_intern_appears_for_company(client, world):
    app_id = _apply(client, login(client, "alice"), world["software"].id).json()["id"]
    client.patch(f"/api/applications/{app_id}", json={"status": "Matched"}, headers=login(client, "admin"))
    rows = client.get("/api/company/positions", headers=login(client, "acme")).json()
    software = next(r for r in rows if r["position"]["title"] == "Software Intern")
    assert software["filled"] == 1
    assert [i["full_name"] for i in software["interns"]] == ["Alice Smith"]


def test_match_unknown_application_returns_404(client, world):
    response = client.patch("/api/applications/9999", json={"status": "Matched"}, headers=login(client, "admin"))
    assert response.status_code == 404


def test_match_with_invalid_status_returns_422(client, world):
    app_id = _apply(client, login(client, "alice"), world["software"].id).json()["id"]
    response = client.patch(f"/api/applications/{app_id}", json={"status": "Rejected"}, headers=login(client, "admin"))
    assert response.status_code == 422


def test_student_cannot_be_matched_twice(client, world):
    alice = login(client, "alice")
    first = _apply(client, alice, world["software"].id).json()["id"]
    second = _apply(client, alice, world["design"].id).json()["id"]
    admin = login(client, "admin")
    assert client.patch(f"/api/applications/{first}", json={"status": "Matched"}, headers=admin).status_code == 200
    response = client.patch(f"/api/applications/{second}", json={"status": "Matched"}, headers=admin)
    assert response.status_code == 409


def test_matched_student_cannot_apply_again(client, world):
    alice = login(client, "alice")
    app_id = _apply(client, alice, world["software"].id).json()["id"]
    client.patch(f"/api/applications/{app_id}", json={"status": "Matched"}, headers=login(client, "admin"))
    assert _apply(client, alice, world["design"].id).status_code == 409


def test_full_position_is_hidden_and_cannot_be_matched_again(client, world, session):
    # Design Intern has 1 slot. Fill it with Alice, then try Bob.
    alice_app = _apply(client, login(client, "alice"), world["design"].id).json()["id"]
    bob_app = make_application(session, world["bob"], world["design"])
    admin = login(client, "admin")
    assert client.patch(f"/api/applications/{alice_app}", json={"status": "Matched"}, headers=admin).status_code == 200

    response = client.patch(f"/api/applications/{bob_app.id}", json={"status": "Matched"}, headers=admin)
    assert response.status_code == 409
    titles = [p["title"] for p in client.get("/api/positions", headers=login(client, "bob")).json()]
    assert "Design Intern" not in titles

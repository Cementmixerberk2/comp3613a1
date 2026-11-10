"""Unit tests for the repositories, each run against its own empty in-memory database."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.internship import (
    ApplicationRepository,
    CompanyRepository,
    PositionRepository,
    StudentRepository,
)
from app.repositories.user import UserRepository
from app.schemas.user import RegularUserCreate
from tests.conftest import (
    make_application,
    make_company,
    make_position,
    make_student,
    make_user,
)

# ---------------------------------------------------------------- UserRepository

def test_user_repository_create_and_lookup(session):
    repo = UserRepository(session)
    user = repo.create(RegularUserCreate(username="dan", email="dan@example.com", password="hash", role="student"))
    assert user.id is not None
    assert repo.get_by_username("dan").id == user.id
    assert repo.get_by_id(user.id).email == "dan@example.com"


def test_user_repository_rejects_duplicate_username(session):
    repo = UserRepository(session)
    repo.create(RegularUserCreate(username="dan", email="dan@example.com", password="hash"))
    with pytest.raises(IntegrityError):
        repo.create(RegularUserCreate(username="dan", email="other@example.com", password="hash"))


def test_user_repository_unknown_username_returns_none(session):
    assert UserRepository(session).get_by_username("ghost") is None


# ---------------------------------------------------------------- Company / Student

def test_company_ensure_for_user_is_idempotent(session):
    user = make_user(session, "globex", "company")
    repo = CompanyRepository(session)
    first = repo.ensure_for_user(user.id, "Globex", user.email)
    second = repo.ensure_for_user(user.id, "Globex", user.email)
    assert first.id == second.id


def test_student_ensure_for_user_keeps_existing_profile(session):
    user, student = make_student(session, "erin", "Erin Lee")
    again = StudentRepository(session).ensure_for_user(user.id, "Other Name", "Math", 2.0)
    assert again.id == student.id
    assert again.full_name == "Erin Lee"


# ---------------------------------------------------------------- PositionRepository

def test_position_create_sets_available_slots_to_total(session):
    _, company = make_company(session)
    position = PositionRepository(session).create(company.id, "QA Intern", "Testing", 3)
    assert position.total_slots == 3
    assert position.available_slots == 3
    assert position.created_at is not None


def test_position_create_rejects_blank_title(session):
    _, company = make_company(session)
    with pytest.raises(ValueError):
        PositionRepository(session).create(company.id, "  ", "Testing", 1)


def test_position_list_open_hides_full_positions(session):
    _, company = make_company(session)
    open_pos = make_position(session, company, "Open", slots=1)
    make_position(session, company, "Full", slots=0)
    titles = [p.title for p in PositionRepository(session).list_open()]
    assert titles == [open_pos.title]


def test_position_list_by_company_only_returns_own(session):
    _, acme = make_company(session, "acme", "Acme")
    _, globex = make_company(session, "globex", "Globex")
    make_position(session, acme, "Acme Intern")
    make_position(session, globex, "Globex Intern")
    titles = [p.title for p in PositionRepository(session).list_by_company(acme.id)]
    assert titles == ["Acme Intern"]


# ---------------------------------------------------------------- ApplicationRepository

def test_application_create_defaults_to_submitted(session):
    _, company = make_company(session)
    _, student = make_student(session)
    position = make_position(session, company)
    app = ApplicationRepository(session).create(student.id, position.id, "  Hello  ")
    assert app.status == "Submitted"
    assert app.cover_note == "Hello"


def test_application_create_rejects_duplicate(session):
    _, company = make_company(session)
    _, student = make_student(session)
    position = make_position(session, company)
    repo = ApplicationRepository(session)
    repo.create(student.id, position.id, "")
    with pytest.raises(ValueError, match="already applied"):
        repo.create(student.id, position.id, "")


def test_application_match_sets_status_and_reduces_slots(session):
    _, company = make_company(session)
    _, student = make_student(session)
    position = make_position(session, company, slots=2)
    app = make_application(session, student, position)
    matched = ApplicationRepository(session).match(app.id)
    session.refresh(position)
    assert matched.status == "Matched"
    assert position.available_slots == 1


def test_student_has_matched_application(session):
    _, company = make_company(session)
    _, student = make_student(session)
    position = make_position(session, company)
    repo = ApplicationRepository(session)
    app = make_application(session, student, position)
    assert repo.student_has_matched_application(student.id) is False
    repo.match(app.id)
    assert repo.student_has_matched_application(student.id) is True

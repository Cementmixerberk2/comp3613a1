"""Unit tests for InternshipService business rules.

All four repositories are replaced with mocks, so each test checks one rule
of the service in isolation from the database.
"""

from unittest.mock import MagicMock

import pytest

from app.models.internship import Application, Company, Position, Student
from app.models.user import User
from app.services.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.services.internship_service import InternshipService


@pytest.fixture
def service():
    svc = InternshipService(MagicMock())
    svc.company_repo = MagicMock()
    svc.student_repo = MagicMock()
    svc.position_repo = MagicMock()
    svc.application_repo = MagicMock()
    return svc


def _user(role, user_id=1, username="user"):
    return User(id=user_id, username=username, email=f"{username}@example.com", password="x", role=role)


def _position(slots=2):
    return Position(id=10, company_id=3, title="Intern", description="Desc", total_slots=2, available_slots=slots)


# ---------------------------------------------------------------- create_position

def test_create_position_saves_trimmed_values(service):
    service.company_repo.get_by_user.return_value = Company(id=3, user_id=1, name="Acme", contact_email="a@a.com")
    service.create_position(_user("company"), "  Data Intern  ", "  Analyse data ", 2)
    service.position_repo.create.assert_called_once_with(3, "Data Intern", "Analyse data", 2)


@pytest.mark.parametrize("title, description", [("", "Desc"), ("   ", "Desc"), ("Title", ""), ("Title", "   ")])
def test_create_position_rejects_blank_fields(service, title, description):
    with pytest.raises(InvalidInputError):
        service.create_position(_user("company"), title, description, 1)
    service.position_repo.create.assert_not_called()


def test_create_position_creates_company_profile_when_missing(service):
    service.company_repo.get_by_user.return_value = None
    service.company_repo.ensure_for_user.return_value = Company(id=7, user_id=1, name="New", contact_email="n@n.com")
    service.create_position(_user("company"), "Title", "Desc", 1)
    service.company_repo.ensure_for_user.assert_called_once()
    service.position_repo.create.assert_called_once_with(7, "Title", "Desc", 1)


# ---------------------------------------------------------------- submit_application

@pytest.fixture
def student_ready(service):
    service.student_repo.get_by_user.return_value = Student(id=4, user_id=1, full_name="Alice", major="CS", gpa=3.5)
    service.position_repo.get_by_id.return_value = _position()
    service.application_repo.get_by_student_and_position.return_value = None
    service.application_repo.student_has_matched_application.return_value = False
    return service


def test_submit_application_creates_application(student_ready):
    student_ready.submit_application(_user("student"), 10, "Hire me")
    student_ready.application_repo.create.assert_called_once_with(4, 10, "Hire me")


def test_submit_application_rejects_non_student(student_ready):
    with pytest.raises(PermissionDeniedError):
        student_ready.submit_application(_user("company"), 10, "")


def test_submit_application_rejects_missing_position(student_ready):
    student_ready.position_repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        student_ready.submit_application(_user("student"), 99, "")


def test_submit_application_rejects_full_position(student_ready):
    student_ready.position_repo.get_by_id.return_value = _position(slots=0)
    with pytest.raises(ConflictError, match="no longer open"):
        student_ready.submit_application(_user("student"), 10, "")


def test_submit_application_rejects_duplicate(student_ready):
    student_ready.application_repo.get_by_student_and_position.return_value = Application(id=1, student_id=4, position_id=10)
    with pytest.raises(ConflictError, match="already applied"):
        student_ready.submit_application(_user("student"), 10, "")


def test_submit_application_rejects_already_matched_student(student_ready):
    student_ready.application_repo.student_has_matched_application.return_value = True
    with pytest.raises(ConflictError, match="already matched"):
        student_ready.submit_application(_user("student"), 10, "")
    student_ready.application_repo.create.assert_not_called()


# ---------------------------------------------------------------- match_application

@pytest.fixture
def match_ready(service):
    service.application_repo.get_by_id.return_value = Application(id=1, student_id=4, position_id=10, status="Submitted")
    service.application_repo.student_has_matched_application.return_value = False
    service.position_repo.get_by_id.return_value = _position()
    return service


def test_match_application_matches(match_ready):
    match_ready.match_application(_user("admin"), 1)
    match_ready.application_repo.match.assert_called_once_with(1)


def test_match_application_requires_admin(match_ready):
    with pytest.raises(PermissionDeniedError):
        match_ready.match_application(_user("company"), 1)
    match_ready.application_repo.match.assert_not_called()


def test_match_application_rejects_unknown_application(match_ready):
    match_ready.application_repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        match_ready.match_application(_user("admin"), 999)


def test_match_application_rejects_already_matched_application(match_ready):
    match_ready.application_repo.get_by_id.return_value = Application(id=1, student_id=4, position_id=10, status="Matched")
    with pytest.raises(ConflictError):
        match_ready.match_application(_user("admin"), 1)


def test_match_application_rejects_student_matched_elsewhere(match_ready):
    match_ready.application_repo.student_has_matched_application.return_value = True
    with pytest.raises(ConflictError, match="already matched"):
        match_ready.match_application(_user("admin"), 1)


def test_match_application_rejects_full_position(match_ready):
    match_ready.position_repo.get_by_id.return_value = _position(slots=0)
    with pytest.raises(ConflictError, match="no remaining slots"):
        match_ready.match_application(_user("admin"), 1)


# ---------------------------------------------------------------- ensure_role_profile

def test_ensure_role_profile_creates_student_profile(service):
    service.ensure_role_profile(_user("student", username="dan"))
    service.student_repo.ensure_for_user.assert_called_once_with(1, "Dan", "Undecided", 0.0)
    service.company_repo.ensure_for_user.assert_not_called()


def test_ensure_role_profile_creates_company_profile(service):
    service.ensure_role_profile(_user("company", username="globex"))
    service.company_repo.ensure_for_user.assert_called_once_with(1, "Globex", "globex@example.com")
    service.student_repo.ensure_for_user.assert_not_called()


def test_service_errors_are_value_errors_for_html_views():
    # The HTML routes catch ValueError, so every service error must still be one.
    for error in (InvalidInputError, PermissionDeniedError, NotFoundError, ConflictError):
        assert issubclass(error, ValueError)

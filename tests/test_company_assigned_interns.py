import asyncio

from starlette.requests import Request
from sqlmodel import Session, SQLModel, create_engine

from app.main import app
from app.models.internship import Application, Company, Position, Student
from app.models.user import User
from app.routers.internship import company_home_view


def _make_session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _make_request(tab: str = "interns") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/company",
        "headers": [],
        "query_string": f"tab={tab}".encode(),
        "client": ("testclient", 5000),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
        "app": app,
    }
    return Request(scope)


def test_company_assigned_interns_tab_renders_empty_state_for_its_own_positions():
    session = _make_session()
    try:
        company_user = User(username="company_alpha", email="alpha@example.com", password="pw", role="company")
        other_company_user = User(username="company_beta", email="beta@example.com", password="pw", role="company")
        student_user = User(username="student_one", email="student1@example.com", password="pw", role="student")
        other_student_user = User(username="student_two", email="student2@example.com", password="pw", role="student")
        session.add_all([company_user, other_company_user, student_user, other_student_user])
        session.commit()

        company = Company(user_id=company_user.id, name="Alpha Co", contact_email="alpha@example.com")
        other_company = Company(user_id=other_company_user.id, name="Beta Co", contact_email="beta@example.com")
        session.add_all([company, other_company])
        session.commit()

        pos1 = Position(company_id=company.id, title="Product Design Intern", description="UI design", total_slots=2, available_slots=1)
        pos2 = Position(company_id=other_company.id, title="Other Company Intern", description="Unrelated", total_slots=2, available_slots=1)
        session.add_all([pos1, pos2])
        session.commit()

        student = Student(user_id=student_user.id, full_name="Alice Smith", major="Computer Science", gpa=3.9)
        other_student = Student(user_id=other_student_user.id, full_name="Bob Jones", major="Math", gpa=3.5)
        session.add_all([student, other_student])
        session.commit()

        matched_for_other_company = Application(student_id=other_student.id, position_id=pos2.id, cover_note="Other company", status="Matched")
        session.add(matched_for_other_company)
        session.commit()

        response = asyncio.run(company_home_view(_make_request("interns"), company_user, session))
        html = response.body.decode()

        assert "Assigned Interns" in html
        assert "No interns assigned" in html
        assert "Alice Smith" not in html
        assert "Bob Jones" not in html
    finally:
        session.close()


def test_new_student_profile_defaults_to_undecided_major_and_zero_gpa():
    session = _make_session()
    try:
        user = User(username="new_student", email="newstudent@example.com", password="pw", role="student")
        session.add(user)
        session.commit()
        session.refresh(user)

        service = __import__("app.services.internship_service", fromlist=["InternshipService"]).InternshipService(session)
        profile = service.student_repo.get_by_user(user.id)
        if profile is None:
            profile = service.ensure_role_profile(user)[1]

        assert profile is not None
        assert profile.major == "Undecided"
        assert profile.gpa == 0.0
    finally:
        session.close()


def test_seed_catalog_uses_clean_internship_dataset():
    from app.seed_data import SEED_APPLICATIONS, SEED_POSITIONS, SEED_STUDENTS, SEED_USERS

    assert len(SEED_USERS) == 7
    assert sum(1 for username, _, _, role in SEED_USERS if role == "student") == 5
    assert any(username == "admin" for username, _, _, _ in SEED_USERS)
    assert any(username == "northwind" for username, _, _, _ in SEED_USERS)
    assert any(position[2] == 1 for position in SEED_POSITIONS)
    assert any(len(student_apps) > 1 for student_apps in SEED_APPLICATIONS if student_apps[0] == "ava_thompson")
    assert all(student_name in {student["full_name"] for student in SEED_STUDENTS.values()} for student_name in ["Ava Thompson", "Leo Martinez", "Mia Ross", "Noah Chen", "Sophia Nguyen"])

"""Shared pytest fixtures.

Every test gets its own empty in-memory SQLite database, so tests never touch
database.db and can run in any order.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models
from app.database import get_session
from app.main import app
from app.models.internship import Application, Company, Position, Student
from app.models.user import User
from app.utilities.security import encrypt_password

TESTS_DIR = Path(__file__).parent


def pytest_collection_modifyitems(config, items):
    """Tag tests by folder so `pytest -m unit` / `-m integration` work."""
    for item in items:
        path = Path(str(item.fspath))
        if "unit" in path.parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in path.parts:
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    def override_get_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    # Not used as a context manager, so the app lifespan (which creates the
    # real database file) does not run during tests.
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------- data helpers

PASSWORD = "pass123"


def make_user(session, username, role, password=PASSWORD):
    user = User(
        username=username,
        email=f"{username}@example.com",
        password=encrypt_password(password),
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def make_company(session, username="acme", name="Acme Ltd"):
    user = make_user(session, username, "company")
    company = Company(user_id=user.id, name=name, contact_email=user.email)
    session.add(company)
    session.commit()
    session.refresh(company)
    return user, company


def make_student(session, username="alice", full_name="Alice Smith"):
    user = make_user(session, username, "student")
    student = Student(user_id=user.id, full_name=full_name, major="Computer Science", gpa=3.5)
    session.add(student)
    session.commit()
    session.refresh(student)
    return user, student


def make_position(session, company, title="Software Intern", slots=2):
    position = Position(
        company_id=company.id,
        title=title,
        description="Build features",
        total_slots=slots,
        available_slots=slots,
    )
    session.add(position)
    session.commit()
    session.refresh(position)
    return position


def make_application(session, student, position, status="Submitted"):
    application = Application(student_id=student.id, position_id=position.id, cover_note="Hi", status=status)
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


@pytest.fixture
def world(session):
    """A small dataset: one admin, one company with two positions, two students."""
    admin = make_user(session, "admin", "admin")
    company_user, company = make_company(session)
    alice_user, alice = make_student(session, "alice", "Alice Smith")
    bob_user, bob = make_student(session, "bob", "Bob Jones")
    software = make_position(session, company, "Software Intern", slots=2)
    design = make_position(session, company, "Design Intern", slots=1)
    return {
        "admin": admin,
        "company_user": company_user,
        "company": company,
        "alice_user": alice_user,
        "alice": alice,
        "bob_user": bob_user,
        "bob": bob,
        "software": software,
        "design": design,
    }


def login(client, username, password=PASSWORD):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    client.cookies.clear()  # use the bearer header only, so each call says who it is
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

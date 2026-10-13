from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlmodel import Session, select

from app.models.internship import Application, Company, Position, Student


class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    def ensure_for_user(self, user_id: int, name: str, email: str) -> Company:
        normalized_name = (name or "").strip() or "Northwind Studio"
        if normalized_name.lower() in {"company", "company1"}:
            normalized_name = "Northwind Studio"

        company = self.db.exec(select(Company).where(Company.user_id == user_id)).one_or_none()
        if company is None:
            company = Company(user_id=user_id, name=normalized_name, contact_email=email)
            self.db.add(company)
            self.db.commit()
            self.db.refresh(company)
        elif company.name != normalized_name:
            company.name = normalized_name
            self.db.add(company)
            self.db.commit()
            self.db.refresh(company)
        return company

    def get_by_user(self, user_id: int) -> Company | None:
        return self.db.exec(select(Company).where(Company.user_id == user_id)).one_or_none()

    def get_by_id(self, company_id: int) -> Company | None:
        return self.db.get(Company, company_id)


class StudentRepository:
    def __init__(self, db: Session):
        self.db = db

    def ensure_for_user(self, user_id: int, full_name: str, major: str, gpa: float) -> Student:
        student = self.db.exec(select(Student).where(Student.user_id == user_id)).one_or_none()
        if student is None:
            student = Student(user_id=user_id, full_name=full_name, major=major, gpa=gpa)
            self.db.add(student)
            self.db.commit()
            self.db.refresh(student)
        return student

    def get_by_user(self, user_id: int) -> Student | None:
        return self.db.exec(select(Student).where(Student.user_id == user_id)).one_or_none()

    def get_by_id(self, student_id: int) -> Student | None:
        return self.db.get(Student, student_id)


class PositionRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _clean_title(value: str | None) -> str:
        return (value or "").strip()

    @staticmethod
    def _clean_description(value: str | None) -> str:
        return (value or "").strip()

    def create(self, company_id: int, title: str, description: str, total_slots: int) -> Position:
        cleaned_title = self._clean_title(title)
        cleaned_description = self._clean_description(description)
        if not cleaned_title:
            raise ValueError("Title cannot be blank. Please enter a position title.")
        if not cleaned_description:
            raise ValueError("Description cannot be blank. Please add a short description.")

        position = Position(
            company_id=company_id,
            title=cleaned_title,
            description=cleaned_description,
            total_slots=max(1, int(total_slots)),
            available_slots=max(1, int(total_slots)),
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        return position

    def get_by_id(self, position_id: int) -> Position | None:
        return self.db.get(Position, position_id)

    def list_all(self) -> list[Position]:
        return self.db.exec(select(Position).order_by(Position.created_at.desc())).all()

    def list_by_company(self, company_id: int) -> list[Position]:
        positions = self.db.exec(select(Position).where(Position.company_id == company_id).order_by(Position.created_at.desc())).all()
        return [position for position in positions if self._clean_title(position.title) and self._clean_description(position.description)]

    def list_open(self) -> list[Position]:
        positions = self.db.exec(select(Position).where(Position.available_slots > 0).order_by(Position.created_at.desc())).all()
        return [position for position in positions if self._clean_title(position.title) and self._clean_description(position.description)]

    def reduce_available_slot(self, position_id: int) -> Position:
        position = self.db.get(Position, position_id)
        if position is None:
            raise ValueError("Position not found")
        position.available_slots = max(0, position.available_slots - 1)
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        return position


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_student_and_position(self, student_id: int, position_id: int) -> Application | None:
        return self.db.exec(
            select(Application).where(Application.student_id == student_id, Application.position_id == position_id)
        ).one_or_none()

    def create(self, student_id: int, position_id: int, cover_note: str) -> Application:
        existing = self.get_by_student_and_position(student_id, position_id)
        if existing is not None:
            raise ValueError("You have already applied for this position.")

        app = Application(
            student_id=student_id,
            position_id=position_id,
            cover_note=(cover_note or "").strip(),
            status="Submitted",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        return app

    def get_by_id(self, application_id: int) -> Application | None:
        return self.db.get(Application, application_id)

    def list_by_student(self, student_id: int) -> list[Application]:
        return self.db.exec(select(Application).where(Application.student_id == student_id).order_by(Application.created_at.desc())).all()

    def list_all(self) -> list[Application]:
        return self.db.exec(select(Application).order_by(Application.created_at.desc())).all()

    def match(self, application_id: int) -> Application:
        app = self.db.get(Application, application_id)
        if app is None:
            raise ValueError("Application not found")
        if app.status == "Matched":
            return app

        position = self.db.get(Position, app.position_id)
        if position is None:
            raise ValueError("Position not found")
        if position.available_slots <= 0:
            raise ValueError("This position has no remaining slots.")

        app.status = "Matched"
        position.available_slots = max(0, position.available_slots - 1)

        self.db.add(app)
        self.db.add(position)
        self.db.commit()
        self.db.refresh(app)
        self.db.refresh(position)
        return app

    def student_has_matched_application(self, student_id: int) -> bool:
        match = self.db.exec(
            select(Application).where(Application.student_id == student_id, Application.status == "Matched")
        ).first()
        return match is not None

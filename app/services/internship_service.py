from __future__ import annotations

from sqlmodel import Session, select

from app.models.internship import Position
from app.models.user import User
from app.repositories.internship import (
    ApplicationRepository,
    CompanyRepository,
    PositionRepository,
    StudentRepository,
)


class InternshipService:
    def __init__(self, db: Session):
        self.db = db
        self.company_repo = CompanyRepository(db)
        self.student_repo = StudentRepository(db)
        self.position_repo = PositionRepository(db)
        self.application_repo = ApplicationRepository(db)

    def ensure_role_profile(self, user: User):
        company = None
        student = None
        if user.role == "company":
            company = self.company_repo.ensure_for_user(user.id, user.username.title(), user.email)
        elif user.role == "student":
            student = self.student_repo.ensure_for_user(user.id, user.username.title(), "Undecided", 0.0)
        return company, student

    def create_position(self, user: User, title: str, description: str, total_slots: int):
        cleaned_title = (title or "").strip()
        cleaned_description = (description or "").strip()
        if not cleaned_title:
            raise ValueError("Title cannot be blank. Please enter a position title.")
        if not cleaned_description:
            raise ValueError("Description cannot be blank. Please add a short description.")

        company = self.company_repo.get_by_user(user.id)
        if company is None:
            company = self.company_repo.ensure_for_user(user.id, user.username.title(), user.email)
        return self.position_repo.create(company.id, cleaned_title, cleaned_description, total_slots)

    def list_company_positions(self, user: User):
        company = self.company_repo.get_by_user(user.id)
        if company is None:
            company = self.company_repo.ensure_for_user(user.id, user.username.title(), user.email)
        positions = self.position_repo.list_by_company(company.id)
        assigned = []
        for position in positions:
            for app in self.application_repo.list_all():
                if app.position_id == position.id and app.status == "Matched":
                    student = self.student_repo.get_by_id(app.student_id)
                    assigned.append({"position": position, "application": app, "student": student})
        return company, positions, assigned

    def list_open_positions(self):
        positions = self.position_repo.list_open()
        items = []
        for position in positions:
            company = self.company_repo.get_by_id(position.company_id)
            items.append({
                "position": position,
                "company": company,
            })
        return items

    def submit_application(self, user: User, position_id: int, cover_note: str):
        if user.role not in {"student", "regular_user"}:
            raise ValueError("Only a student account can apply.")
        student = self.student_repo.get_by_user(user.id)
        if student is None:
            student = self.student_repo.ensure_for_user(user.id, user.username.title(), "Undecided", 0.0)
        position = self.position_repo.get_by_id(position_id)
        if position is None:
            raise ValueError("Position not found.")
        if position.available_slots <= 0:
            raise ValueError("This position is no longer open.")
        if self.application_repo.get_by_student_and_position(student.id, position.id) is not None:
            raise ValueError("You have already applied for this position.")
        if self.application_repo.student_has_matched_application(student.id):
            raise ValueError("This student is already matched to another internship.")
        return self.application_repo.create(student.id, position.id, cover_note)

    def list_student_applications(self, user: User):
        student = self.student_repo.get_by_user(user.id)
        if student is None:
            student = self.student_repo.ensure_for_user(user.id, user.username.title(), "Undecided", 0.0)
        applications = self.application_repo.list_by_student(student.id)
        detailed = []
        for app in applications:
            position = self.position_repo.get_by_id(app.position_id)
            company = self.company_repo.get_by_id(position.company_id) if position else None
            detailed.append({"application": app, "position": position, "company": company})
        return student, detailed

    def match_application(self, user: User, application_id: int):
        if user.role != "admin":
            raise ValueError("Only admins can match applicants.")
        app = self.application_repo.get_by_id(application_id)
        if app is None:
            raise ValueError("Application not found.")
        if self.application_repo.student_has_matched_application(app.student_id):
            raise ValueError("The student is already matched to another position.")
        return self.application_repo.match(application_id)

    def admin_dashboard(self):
        positions = self.position_repo.list_all()
        all_applications = self.application_repo.list_all()
        matched_student_ids = {
            app.student_id
            for app in all_applications
            if app.status == "Matched"
        }
        application_rows = []
        for app in all_applications:
            position = self.position_repo.get_by_id(app.position_id)
            student = self.student_repo.get_by_id(app.student_id)
            company = self.company_repo.get_by_id(position.company_id) if position else None
            application_rows.append(
                {
                    "application": app,
                    "position": position,
                    "student": student,
                    "company": company,
                    "already_matched": (
                        app.status != "Matched"
                        and student is not None
                        and student.id in matched_student_ids
                    ),
                }
            )
        return positions, application_rows

    def _collect_position_assignments(self, position_id: int):
        assignments = []
        for app in self.application_repo.list_all():
            if app.position_id == position_id and app.status == "Matched":
                student = self.student_repo.get_by_id(app.student_id)
                assignments.append({"application": app, "student": student})
        return assignments

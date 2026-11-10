from datetime import datetime
from typing import Literal

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class LoginRequest(SQLModel):
    username: str
    password: str


class RegisterRequest(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6)
    role: Literal["student", "company"] = "student"


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class CurrentUserResponse(SQLModel):
    id: int
    username: str
    email: str
    role: str


class PositionCreate(SQLModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    total_slots: int = Field(ge=1, le=100)


class CompanySummary(SQLModel):
    id: int
    name: str
    contact_email: str


class PositionResponse(SQLModel):
    id: int
    company_id: int
    title: str
    description: str
    total_slots: int
    available_slots: int
    created_at: datetime | None = None
    company: CompanySummary | None = None


class StudentSummary(SQLModel):
    id: int
    full_name: str
    major: str
    gpa: float


class ApplicationCreate(SQLModel):
    cover_note: str = Field(default="", max_length=2000)


class ApplicationUpdate(SQLModel):
    status: Literal["Matched"]


class ApplicationResponse(SQLModel):
    id: int
    student_id: int
    position_id: int
    cover_note: str
    status: str
    created_at: datetime | None = None
    position: PositionResponse | None = None
    student: StudentSummary | None = None


class AssignedPositionResponse(SQLModel):
    position: PositionResponse
    filled: int
    interns: list[StudentSummary]

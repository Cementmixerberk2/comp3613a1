from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", unique=True)
    name: str = Field(index=True)
    contact_email: str


class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", unique=True)
    full_name: str = Field(index=True)
    major: str
    gpa: float


class Position(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    title: str = Field(index=True)
    description: str
    total_slots: int
    available_slots: int
    created_at: datetime | None = Field(default=None, nullable=True)


class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id")
    position_id: int = Field(foreign_key="position.id")
    cover_note: str = ""
    status: str = "Submitted"
    created_at: datetime | None = Field(default=None, nullable=True)

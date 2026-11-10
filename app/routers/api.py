"""JSON REST API for the internship platform.

Authentication: call POST /api/auth/login to get a JWT, then send it as
``Authorization: Bearer <token>``. The ``access_token`` cookie set by the
web login form is accepted too.

Status codes: 200 OK, 201 Created, 400 bad input, 401 not logged in,
403 wrong role, 404 not found, 409 business rule conflict, 422 invalid body.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from app.dependencies.auth import ApiAdminDep, ApiCompanyDep, ApiStudentDep, AuthDep
from app.dependencies.session import SessionDep
from app.models.internship import Application, Company, Position, Student
from app.repositories.user import UserRepository
from app.schemas.internship import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
    AssignedPositionResponse,
    CompanySummary,
    CurrentUserResponse,
    LoginRequest,
    PositionCreate,
    PositionResponse,
    RegisterRequest,
    StudentSummary,
    TokenResponse,
)
from app.services.auth_service import AuthService
from app.services.errors import ServiceError
from app.services.internship_service import InternshipService

from . import api_router


def _raise_http(exc: ServiceError):
    raise HTTPException(status_code=exc.status_code, detail=str(exc))


def _position_out(position: Position, company: Company | None = None) -> PositionResponse:
    data = position.model_dump()
    if company is not None:
        data["company"] = CompanySummary(id=company.id, name=company.name, contact_email=company.contact_email)
    return PositionResponse(**data)


def _student_out(student: Student | None) -> StudentSummary | None:
    if student is None:
        return None
    return StudentSummary(id=student.id, full_name=student.full_name, major=student.major, gpa=student.gpa)


def _application_out(
    application: Application,
    position: Position | None = None,
    company: Company | None = None,
    student: Student | None = None,
) -> ApplicationResponse:
    data = application.model_dump()
    data["position"] = _position_out(position, company) if position is not None else None
    data["student"] = _student_out(student)
    return ApplicationResponse(**data)


# ---------------------------------------------------------------- auth

@api_router.post("/auth/register", response_model=CurrentUserResponse, status_code=status.HTTP_201_CREATED)
def api_register(payload: RegisterRequest, db: SessionDep):
    repo = UserRepository(db)
    if repo.get_by_username(payload.username) is not None or repo.get_by_email(payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")
    user = AuthService(repo).register_user(payload.username, payload.email, payload.password, role=payload.role)
    InternshipService(db).ensure_role_profile(user)
    return CurrentUserResponse(id=user.id, username=user.username, email=user.email, role=user.role)


@api_router.post("/auth/login", response_model=TokenResponse)
def api_login(payload: LoginRequest, db: SessionDep):
    repo = UserRepository(db)
    token = AuthService(repo).authenticate_user(payload.username, payload.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    user = repo.get_by_username(payload.username) or AuthService.resolve_alias(repo, payload.username)
    return TokenResponse(access_token=token, role=user.role)


@api_router.get("/auth/me", response_model=CurrentUserResponse)
def api_me(user: AuthDep):
    return CurrentUserResponse(id=user.id, username=user.username, email=user.email, role=user.role)


# ---------------------------------------------------------------- positions

@api_router.get("/positions", response_model=list[PositionResponse])
def list_open_positions(user: AuthDep, db: SessionDep):
    items = InternshipService(db).list_open_positions()
    return [_position_out(item["position"], item["company"]) for item in items]


@api_router.get("/positions/{position_id}", response_model=PositionResponse)
def get_position(position_id: int, user: AuthDep, db: SessionDep):
    service = InternshipService(db)
    position = service.position_repo.get_by_id(position_id)
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found.")
    return _position_out(position, service.company_repo.get_by_id(position.company_id))


@api_router.post("/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
def create_position(payload: PositionCreate, user: ApiCompanyDep, db: SessionDep):
    service = InternshipService(db)
    try:
        position = service.create_position(user, payload.title, payload.description, payload.total_slots)
    except ServiceError as exc:
        _raise_http(exc)
    return _position_out(position, service.company_repo.get_by_id(position.company_id))


@api_router.get("/company/positions", response_model=list[AssignedPositionResponse])
def list_company_positions(user: ApiCompanyDep, db: SessionDep):
    company, positions, assigned = InternshipService(db).list_company_positions(user)
    result = []
    for position in positions:
        interns = [_student_out(item["student"]) for item in assigned if item["position"].id == position.id]
        result.append(
            AssignedPositionResponse(
                position=_position_out(position, company),
                filled=len(interns),
                interns=[i for i in interns if i is not None],
            )
        )
    return result


# ---------------------------------------------------------------- applications

@api_router.post(
    "/positions/{position_id}/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_position(position_id: int, payload: ApplicationCreate, user: ApiStudentDep, db: SessionDep):
    service = InternshipService(db)
    try:
        application = service.submit_application(user, position_id, payload.cover_note)
    except ServiceError as exc:
        _raise_http(exc)
    position = service.position_repo.get_by_id(application.position_id)
    company = service.company_repo.get_by_id(position.company_id) if position else None
    return _application_out(application, position, company)


@api_router.get("/students/me/applications", response_model=list[ApplicationResponse])
def list_my_applications(user: ApiStudentDep, db: SessionDep):
    student, rows = InternshipService(db).list_student_applications(user)
    return [_application_out(row["application"], row["position"], row["company"], student) for row in rows]


@api_router.get("/applications", response_model=list[ApplicationResponse])
def list_all_applications(
    user: ApiAdminDep,
    db: SessionDep,
    position_id: int | None = None,
    status_filter: str | None = None,
):
    _, rows = InternshipService(db).admin_dashboard()
    if position_id is not None:
        rows = [r for r in rows if r["position"] is not None and r["position"].id == position_id]
    if status_filter:
        rows = [r for r in rows if r["application"].status.lower() == status_filter.lower()]
    return [_application_out(r["application"], r["position"], r["company"], r["student"]) for r in rows]


@api_router.patch("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(application_id: int, payload: ApplicationUpdate, user: ApiAdminDep, db: SessionDep):
    service = InternshipService(db)
    try:
        application = service.match_application(user, application_id)
    except ServiceError as exc:
        _raise_http(exc)
    position = service.position_repo.get_by_id(application.position_id)
    company = service.company_repo.get_by_id(position.company_id) if position else None
    student = service.student_repo.get_by_id(application.student_id)
    return _application_out(application, position, company, student)

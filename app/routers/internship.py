from __future__ import annotations

from urllib.parse import urlencode

from fastapi import Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AdminDep, AuthDep
from app.dependencies.session import SessionDep
from app.services.internship_service import InternshipService
from app.utilities.flash import flash
from . import router, templates


@router.get("/company", response_class=HTMLResponse, name="company_home_view")
async def company_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    tab: str | None = None,
):
    if user.role != "company":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company access required")

    selected_tab = tab or request.query_params.get("tab", "post")
    service = InternshipService(db)
    company, positions, assigned = service.list_company_positions(user)
    assigned_by_position = []
    for position in positions:
        matches = [item for item in assigned if item["position"].id == position.id]
        assigned_by_position.append(
            {
                "position": position,
                "filled": len(matches),
                "students": [
                    {"student": item["student"], "application": item["application"]}
                    for item in matches
                ],
            }
        )

    error_message = request.query_params.get("error")
    messages = []
    if error_message:
        messages.append({"message": error_message, "type": "danger"})
    return templates.TemplateResponse(
        request=request,
        name="company_dashboard.html",
        context={
            "user": user,
            "company": company,
            "positions": positions,
            "assigned": assigned,
            "assigned_by_position": assigned_by_position,
            "selected_tab": selected_tab,
            "messages": messages,
        },
    )


@router.post("/company/positions", name="create_position_action")
async def create_position_action(
    request: Request,
    db: SessionDep,
    user: AuthDep,
    title: str = Form(...),
    description: str = Form(...),
    total_slots: int = Form(...),
):
    if user.role != "company":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company access required")

    cleaned_title = (title or "").strip()
    cleaned_description = (description or "").strip()
    service = InternshipService(db)
    try:
        service.create_position(user, cleaned_title, cleaned_description, total_slots)
        flash(request, "Position posted successfully.", "success")
        return RedirectResponse(url=request.url_for("company_home_view"), status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as exc:
        redirect_url = request.url_for("company_home_view")
        params = urlencode({"error": str(exc)})
        return RedirectResponse(url=f"{redirect_url}?{params}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/student", response_class=HTMLResponse, name="student_home_view")
async def student_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    tab: str | None = None,
    position_id: int | None = None,
):
    if user.role not in {"student", "regular_user"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")

    selected_tab = tab or request.query_params.get("tab", "browse")
    selected_id = position_id if position_id is not None else request.query_params.get("position_id")
    error_message = request.query_params.get("error")
    messages = []
    if error_message:
        messages.append({"message": error_message, "type": "danger"})
    service = InternshipService(db)
    student, applications = service.list_student_applications(user)
    open_positions = service.list_open_positions()

    selected_position = None
    selected_company = None
    selected_position_status = None
    if selected_tab == "browse":
        try:
            selected_id_int = int(selected_id) if selected_id else None
        except ValueError:
            selected_id_int = None

        for item in open_positions:
            if selected_id_int is not None and item["position"].id == selected_id_int:
                selected_position = item["position"]
                selected_company = item["company"]
                break
        if selected_position is None and open_positions:
            selected_position = open_positions[0]["position"]
            selected_company = open_positions[0]["company"]

        if selected_position is not None:
            selected_position_status = None
            for app in applications:
                if app["position"] and app["position"].id == selected_position.id:
                    selected_position_status = app["application"].status
                    break

    return templates.TemplateResponse(
        request=request,
        name="student_dashboard.html",
        context={
            "user": user,
            "student": student,
            "applications": applications,
            "open_positions": open_positions,
            "selected_tab": selected_tab,
            "selected_position": selected_position,
            "selected_company": selected_company,
            "selected_position_status": selected_position_status,
            "messages": messages,
        },
    )


@router.post("/student/positions/{position_id}/apply", name="apply_position_action")
async def apply_position_action(
    request: Request,
    db: SessionDep,
    user: AuthDep,
    position_id: int,
    cover_note: str = Form(default=""),
):
    if user.role not in {"student", "regular_user"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")

    service = InternshipService(db)
    try:
        service.submit_application(user, position_id, cover_note)
        flash(request, "Application submitted successfully.", "success")
        redirect_url = request.url_for("student_home_view")
        params = urlencode({"tab": "browse", "position_id": str(position_id)})
        return RedirectResponse(url=f"{redirect_url}?{params}", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as exc:
        redirect_url = request.url_for("student_home_view")
        params = urlencode({"tab": "browse", "position_id": str(position_id), "error": str(exc)})
        return RedirectResponse(url=f"{redirect_url}?{params}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin", response_class=HTMLResponse, name="admin_home_view")
async def admin_home_view(request: Request, user: AdminDep, db: SessionDep):
    service = InternshipService(db)
    positions, application_rows = service.admin_dashboard()
    error_message = request.query_params.get("error")
    messages = []
    if error_message:
        messages.append({"message": error_message, "type": "danger"})

    selected_position_id = request.query_params.get("position_id")
    selected_position = None
    if selected_position_id is not None:
        try:
            selected_position_id_int = int(selected_position_id)
        except ValueError:
            selected_position_id_int = None
        if selected_position_id_int is not None:
            selected_position = next((p for p in positions if p.id == selected_position_id_int), None)
    if selected_position is None and positions:
        selected_position = positions[0]

    visible_application_rows = []
    if selected_position is not None:
        visible_application_rows = [
            row for row in application_rows if row["position"] is not None and row["position"].id == selected_position.id
        ]
    else:
        visible_application_rows = list(application_rows)

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "user": user,
            "positions": positions,
            "application_rows": visible_application_rows,
            "selected_position": selected_position,
            "messages": messages,
        },
    )


@router.post("/admin/applications/{application_id}/match", name="match_application_action")
async def match_application_action(
    request: Request,
    db: SessionDep,
    user: AdminDep,
    application_id: int,
):
    service = InternshipService(db)
    try:
        service.match_application(user, application_id)
        flash(request, "Application matched successfully.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(url=request.url_for("admin_home_view"), status_code=status.HTTP_303_SEE_OTHER)

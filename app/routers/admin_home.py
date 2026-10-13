from fastapi import Request
from fastapi.responses import HTMLResponse

from app.dependencies.auth import AdminDep
from app.dependencies.session import SessionDep
from . import router, templates


@router.get("/legacy-admin", response_class=HTMLResponse)
async def legacy_admin_home_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "user": user,
        },
    )

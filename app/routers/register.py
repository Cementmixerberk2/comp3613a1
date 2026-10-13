from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request, status, Form, HTTPException
from app.dependencies import SessionDep
from app.schemas.auth import SignupRequest
from app.services.auth_service import AuthService
from app.services.internship_service import InternshipService
from app.repositories.user import UserRepository
from app.utilities.flash import flash
from . import router, templates

# View route (loads the page)
@router.get("/register", response_class=HTMLResponse)
async def register_view(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="register.html",
    )

# Action route (performs an action)
@router.post('/register', response_class=HTMLResponse, status_code=status.HTTP_201_CREATED, name="register_action")
def signup_user(
    request: Request,
    db: SessionDep,
    username: str = Form(),
    email: str = Form(),
    password: str = Form(),
    role: str = Form(default="student"),
):
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    normalized_role = role if role in {"student", "company"} else "student"
    try:
        user = auth_service.register_user(username, email, password, role=normalized_role)
        InternshipService(db).ensure_role_profile(user)
        flash(request, "Registration completed! Sign in now!")
        return RedirectResponse(url=request.url_for("login_view"), status_code=status.HTTP_303_SEE_OTHER)
    except Exception:
        flash(request, "Username or email already exists", "danger")
        return RedirectResponse(url=request.url_for("register_view"), status_code=status.HTTP_303_SEE_OTHER)

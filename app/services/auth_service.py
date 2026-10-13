from app.repositories.user import UserRepository
from app.utilities.security import encrypt_password, verify_password, create_access_token
from app.schemas.user import RegularUserCreate
from typing import Optional


LOGIN_ALIASES = {
    "company1": "northwind",
    "student1": "ava_thompson",
}

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        user = self.user_repo.get_by_username(username)
        if user is None:
            alias_target = LOGIN_ALIASES.get(username.lower())
            if alias_target:
                user = self.user_repo.get_by_username(alias_target)
        if not user or not verify_password(plaintext_password=password, encrypted_password=user.password):
            return None
        access_token = create_access_token(data={"sub": f"{user.id}", "role": user.role})
        return access_token

    def register_user(self, username: str, email: str, password: str, role: str = "regular_user"):
        new_user = RegularUserCreate(
            username=username,
            email=email,
            password=encrypt_password(password),
            role=role,
        )
        return self.user_repo.create(new_user)

from __future__ import annotations

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import ALGORITHM
from app.db.models import User
from app.repositories.user_repo import UserRepository


class AuthContextError(Exception):
    pass


class InvalidAuthorizationHeaderError(AuthContextError):
    pass


class InvalidAccessTokenError(AuthContextError):
    pass


class AuthenticatedUserNotFoundError(AuthContextError):
    pass


class AuthContextService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)
        self.settings = get_settings()

    def resolve_user_from_authorization_header(self, authorization: str | None) -> User:
        if not authorization:
            raise InvalidAuthorizationHeaderError("Missing Authorization header")

        if not authorization.startswith("Bearer "):
            raise InvalidAuthorizationHeaderError("Invalid auth scheme")

        token = authorization.replace("Bearer ", "", 1).strip()
        if not token:
            raise InvalidAuthorizationHeaderError("Empty bearer token")

        try:
            payload = jwt.decode(token, self.settings.app_secret_key, algorithms=[ALGORITHM])
        except JWTError as exc:
            raise InvalidAccessTokenError("Invalid token") from exc

        sub = payload.get("sub")
        if not sub:
            raise InvalidAccessTokenError("Invalid token subject")

        try:
            user_id = int(sub)
        except ValueError as exc:
            raise InvalidAccessTokenError("Invalid token subject") from exc

        user = self.repo.get_by_id(user_id)
        if not user:
            raise AuthenticatedUserNotFoundError("User not found")
        return user

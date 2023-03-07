from typing import Any

from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from jose import jwt
from prisma.models import User
from uvicorn.main import logger

from store_service.core.config import settings
from store_service.api.api_v1.deps.custom_exception import (
    BadCredentialsException,
    PermissionDeniedException,
)

oauth2Scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_prefix}/login/access-token"
)


async def get_current_user(
    token: str = Depends(oauth2Scheme),
) -> User:
    try:
        payload = jwt.decode(
            token=token,
            key=settings.JWT_SECRET_KEY,
            algorithms=settings.JWT_ALGORITHM,
            options={"verify_aud": False},
        )
        sub = payload.get("sub")
        if not sub:
            raise BadCredentialsException
    except JWTError:
        raise BadCredentialsException

    user = await User.prisma().find_unique(
        where={"id": str(sub)}, include={"orders": True}
    )
    if user is None:
        raise BadCredentialsException
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400,
            detail="This user doesn't have enough privileges",
        )
    return current_user


class RoleChecker:
    def __init__(
        self,
        resource: Any | None = None,
        roles: list = None,
    ):
        self.resource = resource
        self.roles = roles

    async def __call__(self, current_user: User = Depends(get_current_active_user)):
        if settings.enable_rbac and self.roles:
            if current_user.role not in self.roles:
                msg = f"User with role '{current_user.role}' doesn`t have access to '{self.resource.__name__}'"
                logger.info(msg)
                if settings.DEBUG:
                    logger.info(
                        f"Details: current_user role is '{current_user.role}', required roles: {self.roles}"
                    )
                raise PermissionDeniedException

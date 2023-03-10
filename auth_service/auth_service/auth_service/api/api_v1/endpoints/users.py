from typing import Any
from typing import List

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi.encoders import jsonable_encoder
from pydantic.networks import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service import crud
from auth_service import models
from auth_service import schemas
from auth_service.api.dependencies import auth
from auth_service.api.dependencies import database
from auth_service.api.dependencies import params
from auth_service.models.user import User

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
async def read_users(
    response: Response,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user),  # noqa
    request_params: models.RequestParams = Depends(
        params.parse_react_admin_params(User),
    ),
) -> Any:
    """
    Retrieve users.
    """
    users, total = await crud.user.get_multi(db, request_params)
    response.headers[
        "Content-Range"
    ] = f"{request_params.skip}-{request_params.skip + len(users)}/{total}"
    return users


@router.post("/", response_model=schemas.User)
async def create_user(
    *,
    db: AsyncSession = Depends(database.get_db),
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
) -> Any:
    """
    Create new user.
    """

    user = await crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="privelegies error",
        )
    new_user = await crud.user.create(db, obj_in=user_in)
    return new_user


@router.put("/me", response_model=schemas.User)
async def update_user_me(
    *,
    db: AsyncSession = Depends(database.get_db),
    password: str = Body(None),
    email: EmailStr = Body(None),
    current_user: models.User = Depends(auth.get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    current_user_data = jsonable_encoder(current_user)
    user_in = schemas.UserUpdate(**current_user_data)
    if password:
        user_in.password = password
    if email:
        user_in.email = email
    user = await crud.user.update(db, db_obj=current_user, obj_in=user_in)
    return user


@router.get("/me", response_model=schemas.User)
async def read_user_me(
    response: Response,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    user = await crud.user.get(db, current_user.id)
    response.headers["Content-Range"] = f"{0}-{1}/{1}"
    return user


@router.get("/{id}", response_model=schemas.User)
async def read_user_by_id(
    id: str,
    current_user: models.User = Depends(auth.get_current_active_user),  # noqa
    db: AsyncSession = Depends(database.get_db),
) -> Any:
    """
    Get a specific user.
    """
    user = await crud.user.get(db, id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user does not exist",
        )
    return user


@router.put("/{id}", response_model=schemas.User)
async def update_user(
    *,
    id: str,
    db: AsyncSession = Depends(database.get_db),
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(
        auth.get_current_active_superuser
    ),  # noqa
) -> Any:
    """
    Update a user.
    """
    user = await crud.user.get(db, id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist",
        )
    user = await crud.user.update(db, db_obj=user, obj_in=user_in)
    return user


@router.delete("/{id}", response_model=schemas.User)
async def delete_user(
    *,
    id: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user),  # noqa
) -> Any:
    """
    Delete user.
    """
    user = await crud.user.get(db, id)
    if not user:
        raise HTTPException(status_code=404, detail="Item not found")
    if user.is_active:
        raise HTTPException(
            status_code=404, detail="Acive user cannot be removed"
        )
    if user.is_superuser:
        raise HTTPException(
            status_code=404, detail="Superuser cannot be removed"
        )

    user = await crud.user.remove(db=db, id=id)
    return user
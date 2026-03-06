import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserCreate as UserCreateModel
from app.schemas.auth import UserCreate, UserLogin, TokenResponse, UserResponse
from app.services.auth_service import (
    register_user,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.config import get_settings
from app.models.user import User
from app.database import get_async_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """Register a new user account and return a JWT access token."""
    db_user = await register_user(db, UserCreateModel(**user_create.model_dump()))

    settings = get_settings()
    token_data = {"sub": str(db_user.id), "email": db_user.email}
    access_token = create_access_token(data=token_data)
    logger.info("User registered: id=%s email=%s", db_user.id, db_user.email)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration_seconds,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT token",
)
async def login(
    user_login: UserLogin,
    db: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """Authenticate with email + password and return a JWT access token."""
    user = await authenticate_user(db, user_login.email, user_login.password)

    if not user:
        # Return 401 — do NOT reveal whether the email exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(data=token_data)
    logger.info("User logged in: id=%s", user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration_seconds,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Validate the current JWT token and return the authenticated user's profile.
    Useful for the frontend to verify a stored token on page load.
    Returns 401 if the token is missing, expired, or invalid.
    """
    return UserResponse(id=str(current_user.id), email=current_user.email)

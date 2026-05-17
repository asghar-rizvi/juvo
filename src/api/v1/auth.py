"""
Authentication endpoints - Fixed version
/api/v1/auth/*
"""
from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.models.auth import (
    UserRegisterRequest, ProviderRegisterRequest,
    LoginRequest, RefreshTokenRequest,
    AuthResponse, TokenResponse, UserResponse, ProviderResponse
)
from src.services.auth_service import AuthService
from src.api.dependencies import get_db, CurrentUser, CurrentProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================
# User Authentication
# ============================================

@router.post(
    "/register/user",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new customer account"
)
def register_user(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    **Requirements:**
    - Unique email and phone number
    - Pakistani phone format (+92XXXXXXXXXX)
    - Strong password (8+ chars, uppercase, lowercase, digit)
    """
    auth_service = AuthService(db)
    return auth_service.register_user(request)


@router.post(
    "/login/user",
    response_model=AuthResponse,
    summary="User login"
)
def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login as a customer. Returns tokens and user profile."""
    auth_service = AuthService(db)
    return auth_service.login_user(request.email, request.password)


# ============================================
# Provider Authentication
# ============================================

@router.post(
    "/register/provider",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register service provider"
)
def register_provider(
    request: ProviderRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new service provider.

    Creates both a Provider (business profile) and
    ProviderAccount (login credentials).
    """
    auth_service = AuthService(db)
    return auth_service.register_provider(request)


@router.post(
    "/login/provider",
    response_model=AuthResponse,
    summary="Provider login"
)
def login_provider(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login as a service provider. Returns tokens and provider profile."""
    auth_service = AuthService(db)
    return auth_service.login_provider(request.email, request.password)


# ============================================
# Token Management
# ============================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token"
)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Get a new access token using a valid refresh token."""
    auth_service = AuthService(db)
    return auth_service.refresh_access_token(request.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout - revoke refresh token"
)
def logout(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Logout by revoking refresh token.

    Access token remains valid until expiry (30 min).
    Refresh token is immediately invalidated.
    """
    auth_service = AuthService(db)
    auth_service.logout(request.refresh_token)
    # 204 = No Content, no body returned


# ============================================
# Current User Profiles
# ============================================

@router.get(
    "/me/user",
    response_model=UserResponse,
    summary="Get current user profile"
)
def get_current_user_profile(current_user: CurrentUser):
    """
    Get authenticated user's profile.

    **Requires:** `Authorization: Bearer <user_access_token>`
    """
    return UserResponse.model_validate(current_user)


@router.get(
    "/me/provider",
    response_model=ProviderResponse,
    summary="Get current provider profile"
)
def get_current_provider_profile(current_provider: CurrentProvider):
    """
    Get authenticated provider's profile.

    **Requires:** `Authorization: Bearer <provider_access_token>`
    """
    provider = current_provider.provider
    return ProviderResponse(
        id=current_provider.id,
        email=current_provider.email,
        provider_id=provider.id,
        provider_name=provider.name,
        phone=provider.phone,
        service_category=provider.service_category.name_en,
        address_text=provider.address_text,
        rating=float(provider.rating),
        total_reviews=provider.total_reviews,
        is_verified=current_provider.is_verified,
        created_at=current_provider.created_at
    )
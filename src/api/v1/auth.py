"""
Authentication endpoints
/api/v1/auth/*
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.models.auth import (
    UserRegisterRequest, ProviderRegisterRequest,
    LoginRequest, RefreshTokenRequest,
    AuthResponse, TokenResponse
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
    description="Create a new customer account in the Juvo app"
)
def register_user(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    **Requirements:**
    - Unique email
    - Unique phone number (Pakistani format: +92XXXXXXXXXX)
    - Strong password (min 8 chars, uppercase, lowercase, digit)
    
    **Returns:**
    - User profile data
    - Access token (valid for 30 minutes)
    - Refresh token (valid for 30 days)
    """
    auth_service = AuthService(db)
    return auth_service.register_user(request)


@router.post(
    "/login/user",
    response_model=AuthResponse,
    summary="User login",
    description="Login with email and password"
)
def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login as a customer.
    
    **Returns:**
    - User profile data
    - Access token
    - Refresh token
    """
    auth_service = AuthService(db)
    return auth_service.login_user(request.email, request.password)


# ============================================
# Provider Authentication
# ============================================

@router.post(
    "/register/provider",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new service provider",
    description="Create a new service provider account"
)
def register_provider(
    request: ProviderRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new service provider.
    
    **Requirements:**
    - Unique email
    - Unique phone number
    - Valid service category
    - Valid address (will be geocoded)
    
    **Returns:**
    - Provider profile data
    - Access token
    - Refresh token
    """
    auth_service = AuthService(db)
    return auth_service.register_provider(request)


@router.post(
    "/login/provider",
    response_model=AuthResponse,
    summary="Provider login",
    description="Login as service provider"
)
def login_provider(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login as a service provider.
    
    **Returns:**
    - Provider profile data
    - Access token
    - Refresh token
    """
    auth_service = AuthService(db)
    return auth_service.login_provider(request.email, request.password)


# ============================================
# Token Management
# ============================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token.
    
    Use this endpoint when access token expires.
    Provide the refresh token to get a new access token.
    
    **Returns:**
    - New access token
    - New refresh token
    """
    auth_service = AuthService(db)
    return auth_service.refresh_access_token(request.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Revoke refresh token (logout)"
)
def logout(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Logout by revoking refresh token.
    
    After logout, the refresh token cannot be used.
    Access token will still be valid until expiry.
    """
    auth_service = AuthService(db)
    auth_service.logout(request.refresh_token)
    return {"message": "Logged out successfully"}


# ============================================
# Current User Info
# ============================================

@router.get(
    "/me/user",
    response_model=dict,
    summary="Get current user profile",
    description="Get authenticated user's profile"
)
def get_current_user_profile(current_user: CurrentUser):
    """
    Get current authenticated user's profile.
    
    **Requires:** Valid access token in Authorization header
    
    **Returns:**
    - User profile data
    """
    from src.models.auth import UserResponse
    return UserResponse.model_validate(current_user).model_dump()


@router.get(
    "/me/provider",
    response_model=dict,
    summary="Get current provider profile",
    description="Get authenticated provider's profile"
)
def get_current_provider_profile(current_provider: CurrentProvider):
    """
    Get current authenticated provider's profile.
    
    **Requires:** Valid provider access token
    
    **Returns:**
    - Provider profile data
    """
    provider = current_provider.provider
    return {
        "id": current_provider.id,
        "email": current_provider.email,
        "provider_id": provider.id,
        "provider_name": provider.name,
        "phone": provider.phone,
        "service_category": provider.service_category.name_en,
        "rating": float(provider.rating),
        "total_reviews": provider.total_reviews,
        "is_verified": current_provider.is_verified
    }
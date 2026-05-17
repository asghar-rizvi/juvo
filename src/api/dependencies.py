"""
FastAPI dependencies for authentication and authorization
"""
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Annotated
from datetime import datetime

from src.database.connection import get_db_session
from src.database.models import User, ProviderAccount, RefreshToken
from src.core.security import decode_token
from src.core.permissions import UserRole, Permission, has_permission
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer()


# ============================================
# Database Dependency
# ============================================

def get_db():
    """Get database session"""
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


# ============================================
# Token Extraction
# ============================================

async def get_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract JWT token from Authorization header
    
    Args:
        credentials: HTTP Bearer credentials
    
    Returns:
        JWT token string
    
    Raises:
        HTTPException: If token is missing or invalid format
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return credentials.credentials


# ============================================
# Current User Dependencies
# ============================================

async def get_current_user(
    token: str = Depends(get_token),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        token: JWT access token
        db: Database session
    
    Returns:
        Current user object
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Decode token
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user ID
    user_id = payload.get("sub")
    role = payload.get("role")
    
    if not user_id or role != "user":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Fetch user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    logger.debug(f"Authenticated user: {user.email}")
    
    return user


async def get_current_provider(
    token: str = Depends(get_token),
    db: Session = Depends(get_db)
) -> ProviderAccount:
    """
    Get current authenticated service provider from JWT token
    
    Args:
        token: JWT access token
        db: Database session
    
    Returns:
        Current provider account object
    
    Raises:
        HTTPException: If token is invalid or provider not found
    """
    # Decode token
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # Get provider ID
    provider_account_id = payload.get("sub")
    role = payload.get("role")
    
    if not provider_account_id or role != "provider":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Fetch provider from database
    provider = db.query(ProviderAccount).filter(
        ProviderAccount.id == int(provider_account_id)
    ).first()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provider not found"
        )
    
    # Check if provider is active
    if not provider.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider account is inactive"
        )
    
    logger.debug(f"Authenticated provider: {provider.email}")
    
    return provider


# ============================================
# Optional Authentication
# ============================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None
    Useful for endpoints that work with or without auth
    
    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session
    
    Returns:
        User object or None
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_token(token)
        
        if not payload or payload.get("type") != "access":
            return None
        
        user_id = payload.get("sub")
        role = payload.get("role")
        
        if not user_id or role != "user":
            return None
        
        user = db.query(User).filter(
            User.id == int(user_id),
            User.is_active == True
        ).first()
        
        return user
        
    except Exception as e:
        logger.warning(f"Optional auth failed: {str(e)}")
        return None


# ============================================
# Permission Checking
# ============================================

class PermissionChecker:
    """Dependency for checking user permissions"""
    
    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission
    
    def __call__(self, current_user: User = Depends(get_current_user)):
        """
        Check if current user has required permission
        
        Args:
            current_user: Current authenticated user
        
        Raises:
            HTTPException: If user doesn't have permission
        """
        # Get user role (for now, all users have USER role)
        user_role = UserRole.USER
        
        if not has_permission(user_role, self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.required_permission.value} required"
            )


class ProviderPermissionChecker:
    """Dependency for checking provider permissions"""
    
    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission
    
    def __call__(
        self,
        current_provider: ProviderAccount = Depends(get_current_provider)
    ):
        """Check if provider has required permission"""
        provider_role = UserRole.PROVIDER
        
        if not has_permission(provider_role, self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.required_permission.value} required"
            )


# ============================================
# Verified User Dependency
# ============================================

async def get_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and ensure they are verified
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Verified user
    
    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email."
        )
    
    return current_user


# ============================================
# Type Aliases for Cleaner Code
# ============================================

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentProvider = Annotated[ProviderAccount, Depends(get_current_provider)]
VerifiedUser = Annotated[User, Depends(get_verified_user)]
OptionalUser = Annotated[Optional[User], Depends(get_current_user_optional)]
DatabaseSession = Annotated[Session, Depends(get_db)]
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Tuple
import hashlib

from src.database.models import User, ProviderAccount, RefreshToken, Provider
from src.models.auth import (
    UserRegisterRequest, ProviderRegisterRequest,
    UserResponse, ProviderResponse, TokenResponse, AuthResponse
)
from src.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    hash_token
)
from src.core.config import settings
from src.utils.logger import get_logger
from src.utils.maps_client import get_maps_client

from fastapi import HTTPException, status

logger = get_logger(__name__)


class AuthService:
    """Authentication service with business logic"""
    
    def __init__(self, db: Session):
        self.db = db
        self.maps = get_maps_client()
    
    # ============================================
    # User Registration & Login
    # ============================================
    
    def register_user(self, request: UserRegisterRequest) -> AuthResponse:
        """
        Register a new user account
        
        Args:
            request: User registration data
        
        Returns:
            AuthResponse with user data and tokens
        
        Raises:
            HTTPException: If email or phone already exists
        """
        # Check if email already exists
        existing_user = self.db.query(User).filter(
            User.email == request.email
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if phone already exists
        existing_phone = self.db.query(User).filter(
            User.phone == request.phone
        ).first()
        
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Geocode address if provided
        location_wkt = None
        if request.address and request.city:
            try:
                geocode = self.maps.geocode_location(f"{request.address}, {request.city}")
                if geocode:
                    location_wkt = f"SRID=4326;POINT({geocode['longitude']} {geocode['latitude']})"
            except Exception as e:
                logger.warning(f"Geocoding failed during user registration: {str(e)}")
        
        # Create user
        user = User(
            email=request.email,
            phone=request.phone,
            password_hash=password_hash,
            full_name=request.full_name,
            city=request.city,
            address=request.address,
            location=location_wkt,
            is_active=True,
            is_verified=False  # Require email verification
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"New user registered: {user.email}")
        
        # Generate tokens
        tokens = self._create_tokens_for_user(user)
        
        # Create response
        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=tokens
        )
    
    def login_user(self, email: str, password: str) -> AuthResponse:
        """
        Login user with email and password
        
        Args:
            email: User email
            password: User password
        
        Returns:
            AuthResponse with user data and tokens
        
        Raises:
            HTTPException: If credentials are invalid
        """
        # Find user
        user = self.db.query(User).filter(User.email == email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"User logged in: {user.email}")
        
        # Generate tokens
        tokens = self._create_tokens_for_user(user)
        
        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=tokens
        )
    
    # ============================================
    # Provider Registration & Login
    # ============================================
    
    def register_provider(self, request: ProviderRegisterRequest) -> AuthResponse:
        """
        Register a new service provider account
        
        Args:
            request: Provider registration data
        
        Returns:
            AuthResponse with provider data and tokens
        
        Raises:
            HTTPException: If email/phone exists or validation fails
        """
        # Check if email already exists
        existing_email = self.db.query(ProviderAccount).filter(
            ProviderAccount.email == request.email
        ).first()
        
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if phone already exists in providers
        existing_phone = self.db.query(Provider).filter(
            Provider.phone == request.phone
        ).first()
        
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Geocode address
        location_wkt = None
        if request.latitude and request.longitude:
            location_wkt = f"SRID=4326;POINT({request.longitude} {request.latitude})"
        else:
            try:
                geocode = self.maps.geocode_location(f"{request.address_text}, {request.city}")
                if geocode:
                    location_wkt = f"SRID=4326;POINT({geocode['longitude']} {geocode['latitude']})"
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Could not geocode address. Please provide coordinates."
                    )
            except Exception as e:
                logger.error(f"Geocoding failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid address. Could not determine location."
                )
        
        # Create Provider entry
        provider = Provider(
            name=request.name,
            phone=request.phone,
            service_category_id=request.service_category_id,
            location=location_wkt,
            address_text=request.address_text,
            rating=0.0,
            total_reviews=0,
            is_available=True,
            is_verified=False,
            years_experience=request.years_experience,
            price_range=request.price_range
        )
        
        self.db.add(provider)
        self.db.flush()  # Get provider.id
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create ProviderAccount
        provider_account = ProviderAccount(
            provider_id=provider.id,
            email=request.email,
            password_hash=password_hash,
            is_active=True,
            is_verified=False
        )
        
        self.db.add(provider_account)
        self.db.commit()
        self.db.refresh(provider_account)
        
        logger.info(f"New provider registered: {provider_account.email}")
        
        # Generate tokens
        tokens = self._create_tokens_for_provider(provider_account)
        
        # Create response
        provider_response = ProviderResponse(
            id=provider_account.id,
            email=provider_account.email,
            provider_id=provider.id,
            provider_name=provider.name,
            phone=provider.phone,
            service_category=provider.service_category.name_en,
            address_text=provider.address_text,
            rating=float(provider.rating),
            total_reviews=provider.total_reviews,
            is_verified=provider_account.is_verified,
            created_at=provider_account.created_at
        )
        
        return AuthResponse(
            provider=provider_response,
            tokens=tokens
        )
    
    def login_provider(self, email: str, password: str) -> AuthResponse:
        """
        Login service provider with email and password
        
        Args:
            email: Provider email
            password: Provider password
        
        Returns:
            AuthResponse with provider data and tokens
        
        Raises:
            HTTPException: If credentials are invalid
        """
        # Find provider account
        provider_account = self.db.query(ProviderAccount).filter(
            ProviderAccount.email == email
        ).first()
        
        if not provider_account:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(password, provider_account.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if active
        if not provider_account.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Update last login
        provider_account.last_login_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Provider logged in: {provider_account.email}")
        
        # Generate tokens
        tokens = self._create_tokens_for_provider(provider_account)
        
        # Get provider details
        provider = provider_account.provider
        
        provider_response = ProviderResponse(
            id=provider_account.id,
            email=provider_account.email,
            provider_id=provider.id,
            provider_name=provider.name,
            phone=provider.phone,
            service_category=provider.service_category.name_en,
            address_text=provider.address_text,
            rating=float(provider.rating),
            total_reviews=provider.total_reviews,
            is_verified=provider_account.is_verified,
            created_at=provider_account.created_at
        )
        
        return AuthResponse(
            provider=provider_response,
            tokens=tokens
        )
    
    # ============================================
    # Token Management
    # ============================================
    
    def _create_tokens_for_user(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for user"""
        # Access token payload
        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": "user",
            "full_name": user.full_name
        }
        
        # Refresh token payload
        refresh_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": "user"
        }
        
        # Create tokens
        access_token = create_access_token(access_payload)
        refresh_token = create_refresh_token(refresh_payload)
        
        # Store refresh token in database
        self._store_refresh_token(refresh_token, user_id=user.id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def _create_tokens_for_provider(
        self,
        provider_account: ProviderAccount
    ) -> TokenResponse:
        """Create access and refresh tokens for provider"""
        # Access token payload
        access_payload = {
            "sub": str(provider_account.id),
            "email": provider_account.email,
            "role": "provider",
            "provider_id": provider_account.provider_id
        }
        
        # Refresh token payload
        refresh_payload = {
            "sub": str(provider_account.id),
            "email": provider_account.email,
            "role": "provider"
        }
        
        # Create tokens
        access_token = create_access_token(access_payload)
        refresh_token = create_refresh_token(refresh_payload)
        
        # Store refresh token
        self._store_refresh_token(
            refresh_token,
            provider_account_id=provider_account.id
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def _store_refresh_token(
        self,
        token: str,
        user_id: Optional[int] = None,
        provider_account_id: Optional[int] = None
    ):
        """Store refresh token in database"""
        token_hash_value = hash_token(token)
        
        expires_at = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        refresh_token_record = RefreshToken(
            user_id=user_id,
            provider_account_id=provider_account_id,
            token_hash=token_hash_value,
            expires_at=expires_at,
            is_revoked=False
        )
        
        self.db.add(refresh_token_record)
        self.db.commit()
    
    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token: JWT refresh token
        
        Returns:
            New TokenResponse
        
        Raises:
            HTTPException: If refresh token is invalid or revoked
        """
        # Decode refresh token
        from src.core.security import decode_token
        payload = decode_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if token is in database and not revoked
        token_hash_value = hash_token(refresh_token)
        
        stored_token = self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash_value,
            RefreshToken.is_revoked == False
        ).first()
        
        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or revoked"
            )
        
        # Check expiration
        if stored_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # Generate new access token
        role = payload.get("role")
        user_id = payload.get("sub")
        
        if role == "user":
            user = self.db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            return self._create_tokens_for_user(user)
        
        elif role == "provider":
            provider = self.db.query(ProviderAccount).filter(
                ProviderAccount.id == int(user_id)
            ).first()
            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Provider not found"
                )
            return self._create_tokens_for_provider(provider)
        
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token role"
            )
    
    def logout(self, refresh_token: str):
        """
        Logout by revoking refresh token
        
        Args:
            refresh_token: JWT refresh token to revoke
        """
        token_hash_value = hash_token(refresh_token)
        
        stored_token = self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash_value
        ).first()
        
        if stored_token:
            stored_token.is_revoked = True
            stored_token.revoked_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Refresh token revoked: {stored_token.id}")
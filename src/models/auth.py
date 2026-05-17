"""
Pydantic models for authentication requests and responses
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re

from src.core.security import validate_password_strength


# ============================================
# Request Models
# ============================================

class UserRegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User email address")
    phone: str = Field(..., description="Pakistani phone number (+92XXXXXXXXXX)")
    password: str = Field(..., min_length=8, description="Password")
    full_name: str = Field(..., min_length=2, max_length=200, description="Full name")
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate Pakistani phone number"""
        cleaned = re.sub(r'[\s\-]', '', v)
        
        if cleaned.startswith('0'):
            cleaned = '+92' + cleaned[1:]
        elif cleaned.startswith('92'):
            cleaned = '+' + cleaned
        elif not cleaned.startswith('+92'):
            raise ValueError("Invalid Pakistani phone number")
        
        if not re.match(r'^\+92[0-9]{10}$', cleaned):
            raise ValueError("Phone number must be in format +92XXXXXXXXXX")
        
        return cleaned
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "ahmed@example.com",
                "phone": "+923001234567",
                "password": "SecurePass123",
                "full_name": "Ahmed Khan",
                "city": "Islamabad",
                "address": "House #123, G-13/1"
            }
        }
    }


class ProviderRegisterRequest(BaseModel):
    """Service provider registration request"""
    # Account credentials
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    # Provider details
    name: str = Field(..., min_length=2, max_length=200)
    phone: str
    service_category_id: int = Field(..., gt=0)
    address_text: str = Field(..., min_length=5)
    city: str = Field(..., max_length=100)
    
    # Location (optional, will geocode from address if not provided)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    # Optional details
    years_experience: Optional[int] = Field(None, ge=0, le=50)
    price_range: Optional[str] = Field(None, max_length=50)
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number"""
        cleaned = re.sub(r'[\s\-]', '', v)
        if cleaned.startswith('0'):
            cleaned = '+92' + cleaned[1:]
        elif cleaned.startswith('92'):
            cleaned = '+' + cleaned
        elif not cleaned.startswith('+92'):
            raise ValueError("Invalid Pakistani phone number")
        if not re.match(r'^\+92[0-9]{10}$', cleaned):
            raise ValueError("Phone number must be in format +92XXXXXXXXXX")
        return cleaned
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password"""
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "ali.ac@example.com",
                "password": "SecurePass123",
                "name": "Ali AC Services",
                "phone": "+923001234567",
                "service_category_id": 1,
                "address_text": "Shop #45, Main Market, G-13/1, Islamabad",
                "city": "Islamabad",
                "years_experience": 8,
                "price_range": "Rs. 1500-3000"
            }
        }
    }


class LoginRequest(BaseModel):
    """Login request (email + password)"""
    email: EmailStr
    password: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "ahmed@example.com",
                "password": "SecurePass123"
            }
        }
    }


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="JWT refresh token")


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password"""
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


# ============================================
# Response Models
# ============================================

class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
    }


class UserResponse(BaseModel):
    """User profile response"""
    id: int
    email: str
    phone: str
    full_name: str
    profile_picture_url: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    preferred_language: str
    is_verified: bool
    is_phone_verified: bool
    created_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "email": "ahmed@example.com",
                "phone": "+923001234567",
                "full_name": "Ahmed Khan",
                "city": "Islamabad",
                "preferred_language": "en",
                "is_verified": True,
                "is_phone_verified": True,
                "created_at": "2024-01-01T10:00:00"
            }
        }
    }


class ProviderResponse(BaseModel):
    """Provider profile response"""
    id: int
    email: str
    provider_id: int
    provider_name: str
    phone: str
    service_category: str
    address_text: str
    rating: float
    total_reviews: int
    is_verified: bool
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class AuthResponse(BaseModel):
    """Complete authentication response"""
    user: Optional[UserResponse] = None
    provider: Optional[ProviderResponse] = None
    tokens: TokenResponse
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user": {
                    "id": 1,
                    "email": "ahmed@example.com",
                    "full_name": "Ahmed Khan"
                },
                "tokens": {
                    "access_token": "eyJhbGci...",
                    "refresh_token": "eyJhbGci...",
                    "token_type": "bearer",
                    "expires_in": 1800
                }
            }
        }
    }
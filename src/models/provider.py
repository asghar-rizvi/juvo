"""
Pydantic models for provider dashboard operations
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time as time_type
from decimal import Decimal
import re


# ============================================
# Time Slot Models
# ============================================

class TimeSlotCreateRequest(BaseModel):
    """Create time slots for a day"""
    slot_date: date = Field(..., description="Date for the slots")
    start_time: time_type = Field(..., description="Start time (HH:MM:SS)")
    end_time: time_type = Field(..., description="End time (HH:MM:SS)")
    duration_minutes: int = Field(default=60, ge=15, le=480, description="Slot duration in minutes")

    @field_validator('slot_date')
    @classmethod
    def validate_future_date(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Cannot create slots for past dates")
        return v

    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v: time_type, info) -> time_type:
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError("end_time must be after start_time")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "slot_date": "2024-01-15",
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "duration_minutes": 60
            }
        }
    }


class TimeSlotResponse(BaseModel):
    """Individual time slot response"""
    id: int
    date: str
    time: str
    duration_minutes: int
    is_booked: bool
    booking_id: Optional[int] = None

    model_config = {"from_attributes": True}


class TimeSlotListResponse(BaseModel):
    """List of time slots"""
    slots: List[TimeSlotResponse]
    total_count: int
    available_count: int
    booked_count: int


# ============================================
# Provider Profile Models
# ============================================

class ProviderProfileUpdateRequest(BaseModel):
    """Update provider profile"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    phone: Optional[str] = None
    address_text: Optional[str] = Field(None, min_length=5)
    years_experience: Optional[int] = Field(None, ge=0, le=50)
    price_range: Optional[str] = Field(None, max_length=50)
    is_available: Optional[bool] = None
    profile_image_url: Optional[str] = None

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
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

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Ali AC Services - Updated",
                "price_range": "Rs. 2000-4000",
                "is_available": True,
                "years_experience": 10
            }
        }
    }


class ProviderProfileResponse(BaseModel):
    """Provider profile response"""
    id: int
    name: str
    phone: str
    email: str
    service_category: str
    address_text: Optional[str]
    rating: float
    total_reviews: int
    is_available: bool
    is_verified: bool
    years_experience: Optional[int]
    price_range: Optional[str]
    profile_image_url: Optional[str]

    model_config = {"from_attributes": True}


# ============================================
# Analytics Models
# ============================================

class ProviderAnalyticsResponse(BaseModel):
    """Provider analytics data"""
    total_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    pending_bookings: int
    completion_rate: float
    cancellation_rate: float
    current_month_bookings: int
    average_rating: float
    total_reviews: int
    total_slots: int
    available_slots: int
    booked_slots: int
    utilization_rate: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_bookings": 50,
                "completed_bookings": 40,
                "cancelled_bookings": 5,
                "pending_bookings": 5,
                "completion_rate": 80.0,
                "cancellation_rate": 10.0,
                "current_month_bookings": 12,
                "average_rating": 4.5,
                "total_reviews": 38,
                "total_slots": 100,
                "available_slots": 60,
                "booked_slots": 40,
                "utilization_rate": 40.0
            }
        }
    }


# ============================================
# Provider Booking Status Update
# ============================================

class BookingStatusUpdateRequest(BaseModel):
    """Update booking status - provider only"""
    status: str = Field(
        ...,
        description="New status: confirmed, in_progress, completed, cancelled"
    )
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {'confirmed', 'in_progress', 'completed', 'cancelled'}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "in_progress",
                "notes": "On my way to customer"
            }
        }
    }


# ============================================
# Provider Dashboard Summary
# ============================================

class ProviderDashboardResponse(BaseModel):
    """Complete provider dashboard data"""
    profile: ProviderProfileResponse
    analytics: ProviderAnalyticsResponse
    upcoming_bookings_count: int
    today_slots_count: int
    today_booked_count: int
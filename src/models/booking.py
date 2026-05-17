"""
Pydantic models for booking operations
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional, List
from datetime import datetime, date, time as time_type
from decimal import Decimal


class BookingCreateRequest(BaseModel):
    """Create booking directly (without HTL)"""
    provider_id: int = Field(..., gt=0)
    service_category_id: int = Field(..., gt=0)
    time_slot_id: int = Field(..., gt=0)
    special_instructions: Optional[str] = Field(None, max_length=500)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "provider_id": 1,
                "service_category_id": 1,
                "time_slot_id": 42,
                "special_instructions": "Please call before arriving"
            }
        }
    }


class BookingResponse(BaseModel):
    """Booking details response"""
    id: int
    booking_reference: str
    user_id: int
    user_name: Optional[str]
    user_phone: str
    provider_id: int
    provider_name: str
    service_type: str
    scheduled_date: date
    scheduled_time: time_type
    location: Optional[str]
    status: str
    special_instructions: Optional[str]
    estimated_price: Optional[Decimal]
    created_at: datetime
    confirmed_at: Optional[datetime]
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "booking_reference": "BK20240115-000001",
                "user_id": 1,
                "user_name": "Ahmed Khan",
                "user_phone": "+923001234567",
                "provider_id": 1,
                "provider_name": "Ali AC Services",
                "service_type": "AC Technician",
                "scheduled_date": "2024-01-15",
                "scheduled_time": "10:00:00",
                "status": "confirmed",
                "created_at": "2024-01-14T15:30:00"
            }
        }
    }


class BookingListResponse(BaseModel):
    """List of bookings"""
    bookings: List[BookingResponse]
    total_count: int
    page: int = 1
    page_size: int = 10


class BookingCancelRequest(BaseModel):
    """Cancel booking request"""
    cancellation_reason: Optional[str] = Field(None, max_length=500)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "cancellation_reason": "Provider not available"
            }
        }
    }


class ReviewCreateRequest(BaseModel):
    """Add review for completed booking"""
    rating: float = Field(..., ge=0, le=5)
    review_text: Optional[str] = Field(None, max_length=1000)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "rating": 4.5,
                "review_text": "Excellent service, very professional"
            }
        }
    }


class ProviderBookingResponse(BaseModel):
    """Booking details for provider view"""
    id: int
    booking_reference: str
    user_name: Optional[str]
    user_phone: str
    service_type: str
    scheduled_date: date
    scheduled_time: time_type
    location: Optional[str]
    status: str
    special_instructions: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class BookingStatusUpdateRequest(BaseModel):
    """Update booking status (provider only)"""
    status: str = Field(
        ...,
        pattern="^(confirmed|in_progress|completed|cancelled)$"
    )
    notes: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "in_progress",
                "notes": "On my way"
            }
        }
    }
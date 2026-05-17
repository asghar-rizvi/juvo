"""
Pydantic models for HTL (Hold-to-Lock) reservations
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional
from datetime import datetime


class HTLReserveRequest(BaseModel):
    """Request to reserve a time slot"""
    session_id: UUID4 = Field(..., description="Chat session ID")
    provider_id: int = Field(..., gt=0)
    time_slot_id: int = Field(..., gt=0)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "provider_id": 1,
                "time_slot_id": 42
            }
        }
    }


class HTLConfirmRequest(BaseModel):
    """Confirm HTL reservation and create booking"""
    htl_reservation_id: int = Field(..., gt=0)
    special_instructions: Optional[str] = Field(None, max_length=500)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "htl_reservation_id": 123,
                "special_instructions": "Please bring ladder"
            }
        }
    }


class HTLReservationResponse(BaseModel):
    """HTL reservation details"""
    id: int
    session_id: UUID4
    provider_id: int
    provider_name: str
    time_slot_id: int
    slot_date: str
    slot_time: str
    reserved_at: datetime
    expires_at: datetime
    time_remaining_seconds: int
    is_confirmed: bool
    is_expired: bool
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 123,
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "provider_id": 1,
                "provider_name": "Ali AC Services",
                "time_slot_id": 42,
                "slot_date": "2024-01-15",
                "slot_time": "10:00:00",
                "reserved_at": "2024-01-14T15:30:00",
                "expires_at": "2024-01-14T15:35:00",
                "time_remaining_seconds": 240,
                "is_confirmed": False,
                "is_expired": False
            }
        }
    }


class HTLListResponse(BaseModel):
    """List of active HTL reservations"""
    active_reservations: list[HTLReservationResponse]
    total_count: int
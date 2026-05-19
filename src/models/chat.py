"""
Pydantic models for chat/agent interactions
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from datetime import date, time as time_type


class ChatStep(str, Enum):
    """Chat conversation steps"""
    INITIAL = "initial"
    INTENT_EXTRACTED = "intent_extracted"
    PROVIDERS_SHOWN = "providers_shown"
    PROVIDER_SELECTED = "provider_selected"
    HTL_RESERVED = "htl_reserved"
    BOOKING_CONFIRMED = "booking_confirmed"
    COMPLETED = "completed"
    CONFIRMING = "confirming"


class ChatStartRequest(BaseModel):
    """Start a new chat session"""
    initial_message: Optional[str] = Field(
        None,
        description="Optional first message from user"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "initial_message": "Mujhe kal AC technician chahiye G-13 mein"
            }
        }
    }


class ChatMessageRequest(BaseModel):
    """Send message in existing chat"""
    session_id: UUID4 = Field(..., description="Chat session ID")
    message: str = Field(..., min_length=1, max_length=1000)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Haan, pehla provider theek hai"
            }
        }
    }


class TimeSlotOption(BaseModel):
    slot_id: int
    slot_date: date
    slot_time: time_type
    duration_minutes: int

class ProviderOption(BaseModel):
    """Provider option shown to user with time slots"""
    provider_id: int
    name: str
    distance_km: float
    rating: float
    total_reviews: int
    phone: str
    price_range: Optional[str]
    available_slots_count: int
    time_slots: List[TimeSlotOption] = [] 


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    session_id: UUID4
    current_step: ChatStep
    agent_message: str
    intent: Optional[Dict[str, Any]] = None
    providers: Optional[List[ProviderOption]] = None
    htl_reservation_id: Optional[int] = None
    booking_id: Optional[int] = None
    next_action: Optional[str] = None  # What user should do next
    
    
    booking_id: Optional[int] = None
    booking_reference: Optional[str] = None
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    provider_phone: Optional[str] = None
    provider_rating: Optional[float] = None
    provider_reviews: Optional[int] = None
    provider_price_range: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    
    next_action: Optional[str] = None
    context_data: Optional[Dict] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "current_step": "providers_shown",
                "agent_message": "میں نے آپ کے لیے 2 AC Technician ڈھونڈے ہیں",
                "providers": [],
                "next_action": "Select a provider by number (1, 2) or type 'cancel'"
            }
        }
    }


class ChatHistoryResponse(BaseModel):
    """Chat conversation history"""
    session_id: UUID4
    user_id: int
    started_at: datetime
    current_step: ChatStep
    is_active: bool
    messages: List[Dict[str, Any]]
    
    model_config = {"from_attributes": True}
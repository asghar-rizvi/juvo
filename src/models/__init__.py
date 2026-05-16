from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime, date, time as time_type
from decimal import Decimal
from enum import Enum
import re


# Enums
class Language(str, Enum):
    """Supported languages"""
    URDU = "ur"
    ROMAN_URDU = "roman_ur"
    ENGLISH = "en"


class BookingStatusEnum(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Request/Response Models
class ServiceIntent(BaseModel):
    """
    Extracted user intent from natural language input
    Used by Intent Understanding Agent
    """
    service_type: str = Field(
        ..., 
        description="Service requested (e.g., 'AC Technician', 'Plumber')",
        min_length=2,
        max_length=100
    )
    location: str = Field(
        ..., 
        description="Location/area requested (e.g., 'G-13', 'F-7 Islamabad')",
        min_length=2,
        max_length=200
    )
    preferred_date: date = Field(
        ...,
        description="Requested service date"
    )
    preferred_time: Optional[str] = Field(
        None,
        description="Preferred time (e.g., 'morning', '10 AM', 'afternoon')",
        max_length=50
    )
    language_detected: Language = Field(
        ...,
        description="Detected input language"
    )
    original_input: Optional[str] = Field(
        None,
        description="Original user message"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "service_type": "AC Technician",
                "location": "G-13, Islamabad",
                "preferred_date": "2024-01-15",
                "preferred_time": "morning",
                "language_detected": "roman_ur",
                "original_input": "Mujhe kal subah G-13 mein AC technician chahiye"
            }
        }
    )
    
    @field_validator('preferred_date')
    @classmethod
    def validate_future_date(cls, v: date) -> date:
        """Ensure date is not in the past"""
        if v < date.today():
            raise ValueError("Service date cannot be in the past")
        return v
    
    @field_validator('location')
    @classmethod
    def clean_location(cls, v: str) -> str:
        """Clean and normalize location string"""
        return v.strip().title()


class GeoLocation(BaseModel):
    """Geographical coordinates"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": 33.6844,
                "longitude": 73.0479
            }
        }
    )


class ProviderMatch(BaseModel):
    provider_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=200)
    phone: str
    service_category: str
    distance_km: float = Field(..., ge=0)
    rating: Decimal = Field(..., ge=0, le=5)
    total_reviews: int = Field(default=0, ge=0)
    years_experience: Optional[int] = Field(None, ge=0)
    price_range: Optional[str] = None
    available_slots_count: int = Field(default=0, ge=0)
    is_verified: bool = False
    location: Optional[GeoLocation] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider_id": 1,
                "name": "Ali AC Services",
                "phone": "+923001234567",
                "service_category": "AC Technician",
                "distance_km": 2.5,
                "rating": 4.8,
                "total_reviews": 156,
                "years_experience": 8,
                "price_range": "Rs. 1500-3000",
                "available_slots_count": 12,
                "is_verified": True
            }
        }
    )


class AvailableSlot(BaseModel):
    """Available time slot for a provider"""
    slot_id: int
    slot_date: date
    slot_time: time_type
    duration_minutes: int = 60
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "slot_id": 42,
                "slot_date": "2024-01-15",
                "slot_time": "10:00:00",
                "duration_minutes": 60
            }
        }
    )


class BookingRequest(BaseModel):
    user_phone: str = Field(
        ...,
        description="User phone number in international format"
    )
    user_name: Optional[str] = Field(None, max_length=200)
    provider_id: int = Field(..., gt=0)
    service_category_id: int = Field(..., gt=0)
    time_slot_id: int = Field(..., gt=0)
    location_requested: Optional[GeoLocation] = None
    address_requested: Optional[str] = Field(None, max_length=500)
    special_instructions: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('user_phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove spaces and dashes
        cleaned = re.sub(r'[\s\-]', '', v)
        
        # Add +92 if missing
        if cleaned.startswith('0'):
            cleaned = '+92' + cleaned[1:]
        elif cleaned.startswith('92'):
            cleaned = '+' + cleaned
        elif not cleaned.startswith('+92'):
            raise ValueError("Invalid Pakistani phone number")
        
        # Validate format
        if not re.match(r'^\+92[0-9]{10}$', cleaned):
            raise ValueError("Phone number must be in format +92XXXXXXXXXX")
        
        return cleaned
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_phone": "+923001234567",
                "user_name": "Ahmed Khan",
                "provider_id": 1,
                "service_category_id": 1,
                "time_slot_id": 42,
                "address_requested": "House #123, Street 5, G-13/1, Islamabad",
                "special_instructions": "Please bring ladder for ceiling unit"
            }
        }
    )


class BookingConfirmation(BaseModel):
    booking_id: int
    booking_reference: str
    provider_name: str
    service_type: str
    scheduled_date: date
    scheduled_time: time_type
    provider_phone: str
    estimated_price: Optional[Decimal] = None
    confirmation_message: str
    status: BookingStatusEnum = BookingStatusEnum.CONFIRMED
    created_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "booking_id": 123,
                "booking_reference": "BK20240115-000123",
                "provider_name": "Ali AC Services",
                "service_type": "AC Technician",
                "scheduled_date": "2024-01-15",
                "scheduled_time": "10:00:00",
                "provider_phone": "+923001234567",
                "estimated_price": 2500.00,
                "confirmation_message": "Your booking is confirmed! Ali will arrive at 10:00 AM tomorrow.",
                "status": "confirmed",
                "created_at": "2024-01-14T15:30:00"
            }
        }
    )


class ProviderRanking(BaseModel):
    providers: List[ProviderMatch]
    ranking_criteria: dict = Field(
        default={
            "distance_weight": 0.4,
            "rating_weight": 0.35,
            "availability_weight": 0.25
        }
    )
    reasoning: str = Field(
        ...,
        description="Explanation of why providers were ranked this way"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "providers": [],
                "ranking_criteria": {
                    "distance_weight": 0.4,
                    "rating_weight": 0.35,
                    "availability_weight": 0.25
                },
                "reasoning": "Top provider selected based on: closest distance (2.5 km), high rating (4.8/5), and immediate availability (12 slots)"
            }
        }
    )


class NearbyProviderQuery(BaseModel):
    """Parameters for nearby provider search"""
    service_category: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    max_distance_km: float = Field(default=10.0, gt=0, le=50)
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    limit: int = Field(default=5, gt=0, le=20)


class NearbyProviderResult(BaseModel):
    """Result from nearby provider search"""
    provider_id: int
    provider_name: str
    phone: str
    rating: Decimal
    distance_km: float
    available_slots_count: int
    
    model_config = ConfigDict(from_attributes=True)


class ConversationLogEntry(BaseModel):
    session_id: str
    user_input: Optional[str] = None
    user_input_language: Optional[Language] = None
    extracted_intent: Optional[dict] = None
    agent_name: Optional[str] = None
    agent_response: Optional[str] = None
    tool_calls: Optional[dict] = None
    reasoning: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_input": "Mujhe kal AC technician chahiye",
                "user_input_language": "roman_ur",
                "extracted_intent": {
                    "service": "AC Technician",
                    "time": "tomorrow"
                },
                "agent_name": "IntentAgent",
                "agent_response": "I understand you need an AC technician tomorrow.",
                "tool_calls": {"function": "extract_intent", "success": True},
                "reasoning": "Detected Roman Urdu input, extracted service and time",
                "created_at": "2024-01-14T15:30:00"
            }
        }
    )
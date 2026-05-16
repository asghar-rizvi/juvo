from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DECIMAL, 
    TIMESTAMP, Date, Time, ForeignKey, ARRAY, Enum as SQLEnum,
    CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geography
from datetime import datetime
import enum
from src.database.connection import Base


# enums that i setup in psql
class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LanguageCode(str, enum.Enum):
    URDU = "ur"
    ROMAN_URDU = "roman_ur"
    ENGLISH = "en"



#models
class ServiceCategory(Base):
    __tablename__ = "service_categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name_en = Column(String(100), nullable=False, unique=True)
    name_ur = Column(String(100), nullable=False)
    name_roman_ur = Column(String(100))
    keywords = Column(ARRAY(Text), default=[])
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    

    providers = relationship("Provider", back_populates="service_category", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="service_category")
        
    def __repr__(self):
        return f"<ServiceCategory(id={self.id}, name_en='{self.name_en}')>"


class Provider(Base):
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    service_category_id = Column(Integer, ForeignKey("service_categories.id", ondelete="CASCADE"), nullable=False)
    location = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    address_text = Column(Text)
    rating = Column(DECIMAL(3, 2), default=0.00)
    total_reviews = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    years_experience = Column(Integer)
    price_range = Column(String(50))
    profile_image_url = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('rating >= 0 AND rating <= 5', name='check_rating_range'),
    )
    
    service_category = relationship("ServiceCategory", back_populates="providers")
    time_slots = relationship("TimeSlot", back_populates="provider", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="provider")
    
    def __repr__(self):
        return f"<Provider(id={self.id}, name='{self.name}', service='{self.service_category.name_en if self.service_category else 'N/A'}')>"


class TimeSlot(Base):
    __tablename__ = "time_slots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    slot_date = Column(Date, nullable=False)
    slot_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=60)
    is_booked = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('provider_id', 'slot_date', 'slot_time', name='unique_provider_slot'),
    )
    
    provider = relationship("Provider", back_populates="time_slots")
    booking = relationship("Booking", back_populates="time_slot", uselist=False)
    
    def __repr__(self):
        return f"<TimeSlot(id={self.id}, provider_id={self.provider_id}, date={self.slot_date}, time={self.slot_time}, booked={self.is_booked})>"


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_reference = Column(String(50), unique=True, nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    user_phone = Column(String(20), nullable=False)
    user_name = Column(String(200))
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    service_category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False)
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=False)
    location_requested = Column(Geography(geometry_type='POINT', srid=4326))
    address_requested = Column(Text)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.PENDING)
    special_instructions = Column(Text)
    estimated_price = Column(DECIMAL(10, 2))
    actual_price = Column(DECIMAL(10, 2))
    user_rating = Column(DECIMAL(3, 2))
    user_review = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    confirmed_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    cancelled_at = Column(TIMESTAMP)
    cancellation_reason = Column(Text)
    
    
    __table_args__ = (
        CheckConstraint('user_rating >= 0 AND user_rating <= 5', name='check_user_rating_range'),
    )
    
    provider = relationship("Provider", back_populates="bookings")
    service_category = relationship("ServiceCategory", back_populates="bookings")
    time_slot = relationship("TimeSlot", back_populates="booking")
    conversation_logs = relationship("ConversationLog", back_populates="booking")
    
    def __repr__(self):
        return f"<Booking(id={self.id}, ref='{self.booking_reference}', status={self.status.value})>"


class ConversationLog(Base):
    __tablename__ = "conversation_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    user_input = Column(Text)
    user_input_language = Column(SQLEnum(LanguageCode))
    extracted_intent = Column(JSONB)
    agent_name = Column(String(100))
    agent_response = Column(Text)
    tool_calls = Column(JSONB)
    reasoning = Column(Text)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    booking = relationship("Booking", back_populates="conversation_logs")
    
    def __repr__(self):
        return f"<ConversationLog(id={self.id}, session={self.session_id}, agent='{self.agent_name}')>"
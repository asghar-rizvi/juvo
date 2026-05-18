from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DECIMAL,
    TIMESTAMP, Date, Time, ForeignKey, ARRAY, Enum as SQLEnum,
    CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, UUID as PG_UUID
from geoalchemy2 import Geography
from datetime import datetime
import enum
import uuid
from src.database.connection import Base


# ============================================
# Enums (must match Postgres type names exactly)
# ============================================

class BookingStatus(str, enum.Enum):
    PENDING     = "pending"
    CONFIRMED   = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    CANCELLED   = "cancelled"


class LanguageCode(str, enum.Enum):
    URDU       = "ur"
    ROMAN_URDU = "roman_ur"
    ENGLISH    = "en"


# ============================================
# Models
# ============================================

class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    name_en       = Column(String(100), nullable=False, unique=True)
    name_ur       = Column(String(100), nullable=False)
    name_roman_ur = Column(String(100))
    keywords      = Column(ARRAY(Text), default=[])
    description   = Column(Text)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at    = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    providers = relationship("Provider", back_populates="service_category", cascade="all, delete-orphan")
    bookings  = relationship("Booking",  back_populates="service_category")

    def __repr__(self):
        return f"<ServiceCategory(id={self.id}, name_en='{self.name_en}')>"


class Provider(Base):
    __tablename__ = "providers"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    name                = Column(String(200), nullable=False)
    phone               = Column(String(20),  nullable=False)
    email               = Column(String(255))
    service_category_id = Column(Integer, ForeignKey("service_categories.id", ondelete="CASCADE"), nullable=False)
    location            = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    address_text        = Column(Text)
    city                = Column(String(100), nullable=True)
    rating              = Column(DECIMAL(3, 2), default=0.00)
    total_reviews       = Column(Integer, default=0)
    is_available        = Column(Boolean, default=True)
    is_verified         = Column(Boolean, default=False)
    years_experience    = Column(Integer)
    price_range         = Column(String(50))
    profile_image_url   = Column(Text)
    created_at          = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at          = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('rating >= 0 AND rating <= 5', name='check_rating_range'),
    )

    service_category = relationship("ServiceCategory", back_populates="providers")
    time_slots       = relationship("TimeSlot", back_populates="provider", cascade="all, delete-orphan")
    bookings         = relationship("Booking",  back_populates="provider")

    def __repr__(self):
        return f"<Provider(id={self.id}, name='{self.name}')>"


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    provider_id      = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    slot_date        = Column(Date,    nullable=False)
    slot_time        = Column(Time,    nullable=False)
    duration_minutes = Column(Integer, default=60)
    is_booked        = Column(Boolean, default=False)
    created_at       = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('provider_id', 'slot_date', 'slot_time', name='unique_provider_slot'),
    )

    provider = relationship("Provider", back_populates="time_slots")
    booking  = relationship("Booking",  back_populates="time_slot", uselist=False)

    def __repr__(self):
        return f"<TimeSlot(id={self.id}, provider_id={self.provider_id}, date={self.slot_date}, time={self.slot_time}, booked={self.is_booked})>"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FIX 1: nullable=True so flush() succeeds before we generate the
    # reference string from the new booking.id. We set it immediately
    # after flush and before commit, so the committed row always has a value.
    booking_reference = Column(String(50), unique=True, nullable=True)

    session_id          = Column(UUID(as_uuid=True), nullable=False)
    user_id             = Column(Integer, ForeignKey("users.id"))
    user_phone          = Column(String(20),  nullable=False)
    user_name           = Column(String(200))
    provider_id         = Column(Integer, ForeignKey("providers.id"),          nullable=False)
    htl_reservation_id  = Column(Integer, ForeignKey("htl_reservations.id"))
    service_category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False)
    time_slot_id        = Column(Integer, ForeignKey("time_slots.id"),          nullable=False)
    location_requested  = Column(Geography(geometry_type='POINT', srid=4326))
    address_requested   = Column(Text)

    status = Column(
        SQLEnum(
            BookingStatus,
            name='booking_status',
            create_type=False,
            values_callable=lambda x: [e.value for e in x]  # ← forces lowercase values
        ),
        nullable=False,
        default=BookingStatus.PENDING
    )

    special_instructions = Column(Text)
    estimated_price      = Column(DECIMAL(10, 2))
    actual_price         = Column(DECIMAL(10, 2))
    user_rating          = Column(DECIMAL(3, 2))
    user_review          = Column(Text)
    created_at           = Column(TIMESTAMP, default=datetime.utcnow)
    confirmed_at         = Column(TIMESTAMP)
    completed_at         = Column(TIMESTAMP)
    cancelled_at         = Column(TIMESTAMP)
    cancellation_reason  = Column(Text)

    __table_args__ = (
        CheckConstraint('user_rating >= 0 AND user_rating <= 5', name='check_user_rating_range'),
    )

    user              = relationship("User",            back_populates="bookings")
    provider          = relationship("Provider",        back_populates="bookings")
    service_category  = relationship("ServiceCategory", back_populates="bookings")
    time_slot         = relationship("TimeSlot",        back_populates="booking")
    conversation_logs = relationship("ConversationLog", back_populates="booking")
    htl_reservation   = relationship("HTLReservation")

    def __repr__(self):
        status_val = self.status.value if self.status else "unknown"
        return f"<Booking(id={self.id}, ref='{self.booking_reference}', status={status_val})>"


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id      = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    user_input = Column(Text)

    # FIX 3: name='language_code' matches the Postgres enum type name
    user_input_language = Column(
        SQLEnum(LanguageCode, name='language_code', create_type=False)
    )

    extracted_intent = Column(JSONB)
    agent_name       = Column(String(100))
    agent_response   = Column(Text)
    tool_calls       = Column(JSONB)
    reasoning        = Column(Text)
    context_metadata = Column(JSONB, name="metadata")
    created_at       = Column(TIMESTAMP, default=datetime.utcnow)

    booking = relationship("Booking", back_populates="conversation_logs")

    def __repr__(self):
        return f"<ConversationLog(id={self.id}, session={self.session_id}, agent='{self.agent_name}')>"


# ============================================
# Phase 3 Models
# ============================================

class User(Base):
    __tablename__ = "users"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    email               = Column(String(255), unique=True, nullable=False, index=True)
    phone               = Column(String(20),  unique=True, nullable=False, index=True)
    password_hash       = Column(String(255), nullable=False)
    full_name           = Column(String(200), nullable=False)
    profile_picture_url = Column(Text)
    address             = Column(Text)
    city                = Column(String(100))
    location            = Column(Geography(geometry_type='POINT', srid=4326))
    preferred_language  = Column(String(10), default='en')
    is_active           = Column(Boolean, default=True,  index=True)
    is_verified         = Column(Boolean, default=False)
    is_phone_verified   = Column(Boolean, default=False)
    email_verified_at   = Column(TIMESTAMP)
    phone_verified_at   = Column(TIMESTAMP)
    last_login_at       = Column(TIMESTAMP)
    created_at          = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at          = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookings         = relationship("Booking",        back_populates="user")
    chat_sessions    = relationship("ChatSession",    back_populates="user")
    notifications    = relationship("Notification",   back_populates="user")
    reviews          = relationship("ProviderReview", back_populates="user")
    htl_reservations = relationship("HTLReservation", back_populates="user")
    refresh_tokens   = relationship("RefreshToken",   back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.full_name}')>"


class ProviderAccount(Base):
    __tablename__ = "provider_accounts"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    provider_id       = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), unique=True, nullable=False)
    email             = Column(String(255), unique=True, nullable=False, index=True)
    password_hash     = Column(String(255), nullable=False)
    is_active         = Column(Boolean, default=True)
    is_verified       = Column(Boolean, default=False)
    email_verified_at = Column(TIMESTAMP)
    last_login_at     = Column(TIMESTAMP)
    created_at        = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at        = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    provider       = relationship("Provider",      back_populates="account")
    notifications  = relationship("Notification",  back_populates="provider_account")
    refresh_tokens = relationship("RefreshToken",  back_populates="provider_account")

    def __repr__(self):
        return f"<ProviderAccount(id={self.id}, email='{self.email}')>"


Provider.account = relationship("ProviderAccount", back_populates="provider", uselist=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    user_id             = Column(Integer, ForeignKey("users.id",             ondelete="CASCADE"))
    provider_account_id = Column(Integer, ForeignKey("provider_accounts.id", ondelete="CASCADE"))
    token_hash          = Column(String(255), unique=True, nullable=False, index=True)
    expires_at          = Column(TIMESTAMP, nullable=False)
    is_revoked          = Column(Boolean, default=False)
    revoked_at          = Column(TIMESTAMP)
    user_agent          = Column(Text)
    ip_address          = Column(INET)
    created_at          = Column(TIMESTAMP, default=datetime.utcnow)

    user             = relationship("User",            back_populates="refresh_tokens")
    provider_account = relationship("ProviderAccount", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"


class HTLReservation(Base):
    __tablename__ = "htl_reservations"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(PG_UUID(as_uuid=True), nullable=False, default=uuid.uuid4, index=True)
    user_id      = Column(Integer, ForeignKey("users.id",     ondelete="CASCADE"))
    provider_id  = Column(Integer, ForeignKey("providers.id"))
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"))
    reserved_at  = Column(TIMESTAMP, default=datetime.utcnow)
    expires_at   = Column(TIMESTAMP, nullable=False, index=True)
    is_confirmed = Column(Boolean, default=False)
    is_expired   = Column(Boolean, default=False)
    confirmed_at = Column(TIMESTAMP)
    expired_at   = Column(TIMESTAMP)

    user      = relationship("User",     back_populates="htl_reservations")
    provider  = relationship("Provider")
    time_slot = relationship("TimeSlot")

    def __repr__(self):
        return f"<HTLReservation(id={self.id}, slot_id={self.time_slot_id}, expires={self.expires_at})>"


class Notification(Base):
    __tablename__ = "notifications"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    user_id             = Column(Integer, ForeignKey("users.id",             ondelete="CASCADE"), index=True)
    provider_account_id = Column(Integer, ForeignKey("provider_accounts.id", ondelete="CASCADE"), index=True)
    notification_type   = Column(String(50),  nullable=False, index=True)
    title               = Column(String(200), nullable=False)
    message             = Column(Text,        nullable=False)
    data                = Column(JSONB)
    is_read             = Column(Boolean, default=False, index=True)
    read_at             = Column(TIMESTAMP)
    created_at          = Column(TIMESTAMP, default=datetime.utcnow)

    user             = relationship("User",            back_populates="notifications")
    provider_account = relationship("ProviderAccount", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.notification_type}', read={self.is_read})>"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    session_id         = Column(PG_UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    user_id            = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    current_step       = Column(String(50))
    intent_data        = Column(JSONB)
    selected_providers = Column(JSONB)
    context_data       = Column(JSONB)
    is_active          = Column(Boolean, default=True, index=True)
    started_at         = Column(TIMESTAMP, default=datetime.utcnow)
    last_message_at    = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at       = Column(TIMESTAMP)

    user = relationship("User", back_populates="chat_sessions")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, session_id={self.session_id}, user_id={self.user_id})>"


class ProviderReview(Base):
    __tablename__ = "provider_reviews"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    booking_id    = Column(Integer, ForeignKey("bookings.id"), unique=True)
    user_id       = Column(Integer, ForeignKey("users.id"))
    provider_id   = Column(Integer, ForeignKey("providers.id"))
    rating        = Column(DECIMAL(3, 2), nullable=False)
    review_text   = Column(Text)
    response_text = Column(Text)
    response_at   = Column(TIMESTAMP)
    created_at    = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at    = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('rating >= 0 AND rating <= 5', name='check_review_rating_range'),
    )

    booking  = relationship("Booking")
    user     = relationship("User",     back_populates="reviews")
    provider = relationship("Provider")

    def __repr__(self):
        return f"<ProviderReview(id={self.id}, provider_id={self.provider_id}, rating={self.rating})>"
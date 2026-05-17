"""
Booking service - Complete booking lifecycle management
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from src.database.models import (
    Booking, User, Provider, TimeSlot, ServiceCategory, ProviderReview
)
from src.models.booking import (
    BookingResponse, BookingListResponse,
    ReviewCreateRequest
)
from src.tools import DatabaseTools
from src.utils.logger import get_logger

# FIX: Import HTTPException and status under an alias to avoid the name
# collision where `from fastapi import status` shadows the local `status`
# variable used in cancel_booking and get_user_bookings.
from fastapi import HTTPException
from fastapi import status as http_status

import uuid

logger = get_logger(__name__)


class BookingService:
    """Complete booking management service"""

    def __init__(self, db: Session):
        self.db = db
        self.db_tools = DatabaseTools(db)

    def create_booking(
        self,
        user: User,
        provider_id: int,
        service_category_id: int,
        time_slot_id: int,
        special_instructions: Optional[str] = None
    ) -> BookingResponse:
        """Create booking directly (without HTL)."""
        
        # Validate provider
        provider = self.db.query(Provider).filter(
            Provider.id == provider_id
        ).first()
        if not provider:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Provider not found"
            )

        # Validate service category
        category = self.db.query(ServiceCategory).filter(
            ServiceCategory.id == service_category_id
        ).first()
        if not category:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Service category not found"
            )

        # Validate and lock time slot
        slot = self.db.query(TimeSlot).filter(
            TimeSlot.id == time_slot_id,
            TimeSlot.provider_id == provider_id
        ).with_for_update().first()
        
        if not slot:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Time slot not found"
            )
        if slot.is_booked:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Time slot already booked"
            )

        # Create booking using db_tools (which handles everything correctly)
        booking = self.db_tools.create_booking_record(
            session_id=str(uuid.uuid4()),
            user_phone=user.phone,
            provider_id=provider_id,
            service_category_id=service_category_id,
            time_slot_id=time_slot_id,
            user_name=user.full_name,
            special_instructions=special_instructions
        )

        if not booking:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create booking - slot may have been taken"
            )

        # Associate booking with user
        booking.user_id = user.id
        self.db.commit()
        self.db.refresh(booking)

        logger.info(f"Booking {booking.booking_reference} created for user {user.id}")

        # Schedule reminder (non-critical, wrap in try-except)
        try:
            from src.agents.followup_agent import FollowUpAgent
            FollowUpAgent().schedule_reminder(
                booking_id=booking.id,
                session_id=str(booking.session_id),
                hours_before=1
            )
        except Exception as e:
            logger.warning(f"Follow-up reminder failed (non-critical): {e}")

        return self._build_booking_response(booking)

    def get_booking_details(self, user: User, booking_id: int) -> BookingResponse:
        """Get specific booking details by ID."""
        booking = self.db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.user_id == user.id
        ).first()
        if not booking:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        return self._build_booking_response(booking)

    def get_user_bookings(
        self,
        user: User,
        status: Optional[str] = None,   # 'status' here is a method param, not the module
        page: int = 1,
        page_size: int = 10
    ) -> BookingListResponse:
        """Get user's bookings with pagination."""
        from sqlalchemy import text

        if status:
            status_lower = status.lower().strip()
            valid = {'pending', 'confirmed', 'in_progress', 'completed', 'cancelled'}
            if status_lower not in valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}"
                )

            total_count = self.db.execute(
                text(
                    "SELECT COUNT(*) FROM bookings "
                    "WHERE user_id = :uid AND status::text = :st"
                ),
                {"uid": user.id, "st": status_lower}
            ).scalar() or 0

            rows = self.db.execute(
                text(
                    "SELECT id FROM bookings "
                    "WHERE user_id = :uid AND status::text = :st "
                    "ORDER BY created_at DESC "
                    "LIMIT :lim OFFSET :off"
                ),
                {
                    "uid": user.id,
                    "st": status_lower,
                    "lim": page_size,
                    "off": (page - 1) * page_size
                }
            ).fetchall()

            booking_ids = [row[0] for row in rows]
            bookings = (
                self.db.query(Booking)
                .filter(Booking.id.in_(booking_ids))
                .order_by(Booking.created_at.desc())
                .all()
                if booking_ids else []
            )

        else:
            from sqlalchemy import text as _text
            total_count = self.db.execute(
                _text("SELECT COUNT(*) FROM bookings WHERE user_id = :uid"),
                {"uid": user.id}
            ).scalar() or 0

            offset = (page - 1) * page_size
            bookings = (
                self.db.query(Booking)
                .filter(Booking.user_id == user.id)
                .order_by(Booking.created_at.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )

        return BookingListResponse(
            bookings=[self._build_booking_response(b) for b in bookings],
            total_count=total_count,
            page=page,
            page_size=page_size
        )

    def cancel_booking(
        self,
        user: User,
        booking_id: int,
        cancellation_reason: Optional[str] = None
    ) -> BookingResponse:
        """Cancel user's booking."""
        booking = self.db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.user_id == user.id
        ).first()
        if not booking:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )

        # FIX: Use a local variable name that doesn't shadow the module alias.
        current_booking_status = (
            booking.status.value
            if hasattr(booking.status, 'value')
            else str(booking.status)
        )
        if current_booking_status in ('cancelled', 'completed'):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel booking with status: {current_booking_status}"
            )

        booking.status = 'cancelled'
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = cancellation_reason

        slot = self.db.query(TimeSlot).filter(
            TimeSlot.id == booking.time_slot_id
        ).first()
        if slot:
            slot.is_booked = False

        self.db.commit()
        self.db.refresh(booking)

        logger.info(f"Booking {booking.booking_reference} cancelled by user {user.id}")
        return self._build_booking_response(booking)

    def add_review(
        self,
        user: User,
        booking_id: int,
        review_request: ReviewCreateRequest
    ) -> dict:
        """Add review for completed booking."""
        booking = self.db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.user_id == user.id
        ).first()
        if not booking:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )

        current_booking_status = (
            booking.status.value
            if hasattr(booking.status, 'value')
            else str(booking.status)
        )
        if current_booking_status != 'completed':
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Can only review completed bookings"
            )

        existing_review = self.db.query(ProviderReview).filter(
            ProviderReview.booking_id == booking_id
        ).first()
        if existing_review:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Booking already reviewed"
            )

        review = ProviderReview(
            booking_id=booking_id,
            user_id=user.id,
            provider_id=booking.provider_id,
            rating=review_request.rating,
            review_text=review_request.review_text
        )
        self.db.add(review)

        booking.user_rating = review_request.rating
        booking.user_review = review_request.review_text

        self.db.commit()

        logger.info(f"Review added for booking {booking.booking_reference}")
        return {
            "review_id": review.id,
            "booking_id": booking_id,
            "rating": float(review_request.rating),
            "status": "submitted"
        }

    def _build_booking_response(self, booking: Booking) -> BookingResponse:
        """Build booking response model."""
        return BookingResponse(
            id=booking.id,
            booking_reference=booking.booking_reference,
            user_id=booking.user_id,
            user_name=booking.user_name,
            user_phone=booking.user_phone,
            provider_id=booking.provider_id,
            provider_name=booking.provider.name if booking.provider else "Unknown",
            service_type=(
                booking.service_category.name_en
                if booking.service_category else "Unknown"
            ),
            scheduled_date=booking.time_slot.slot_date if booking.time_slot else None,
            scheduled_time=booking.time_slot.slot_time if booking.time_slot else None,
            location=booking.address_requested,
            status=(
                booking.status.value
                if hasattr(booking.status, 'value')
                else str(booking.status)
            ),
            special_instructions=booking.special_instructions,
            estimated_price=booking.estimated_price,
            created_at=booking.created_at,
            confirmed_at=booking.confirmed_at
        )
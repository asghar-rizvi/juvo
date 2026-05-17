"""
Provider service - Provider dashboard and management
Complete implementation with analytics, slots, profile management
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, and_
from typing import List, Optional
from datetime import datetime, date, time as time_type, timedelta

from src.database.models import (
    Booking, BookingStatus, ProviderAccount, Provider,
    TimeSlot, ServiceCategory
)
from src.models.booking import ProviderBookingResponse
from src.models.provider import (
    TimeSlotResponse, TimeSlotListResponse,
    ProviderProfileResponse, ProviderAnalyticsResponse,
    ProviderProfileUpdateRequest
)
from src.utils.logger import get_logger
from fastapi import HTTPException, status

logger = get_logger(__name__)


class ProviderService:
    """Provider management service - complete implementation"""

    def __init__(self, db: Session):
        self.db = db

    # ============================================
    # Booking Management
    # ============================================

    def get_provider_bookings(
        self,
        provider_account: ProviderAccount,
        booking_status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """
        Get provider's bookings with filters and pagination

        Args:
            provider_account: Current provider account
            booking_status: Filter by status
            start_date: Filter from date
            end_date: Filter to date
            page: Page number
            page_size: Results per page

        Returns:
            Dict with bookings list and pagination info
        """
        query = (
            self.db.query(Booking)
            .options(
                joinedload(Booking.time_slot),
                joinedload(Booking.service_category)
            )
            .filter(Booking.provider_id == provider_account.provider_id)
        )

        if booking_status:
            # Handle both enum and string comparison
            try:
                status_enum = BookingStatus(booking_status)
                logger.info(f"inside providers ervice: {status_enum}")
                query = query.filter(Booking.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {booking_status}"
                )

        if start_date:
            query = query.join(TimeSlot).filter(TimeSlot.slot_date >= start_date)

        if end_date:
            if not start_date:
                query = query.join(TimeSlot)
            query = query.filter(TimeSlot.slot_date <= end_date)

        # Total count
        total_count = query.count()

        # Paginate
        offset = (page - 1) * page_size
        bookings = query.order_by(
            Booking.created_at.desc()
        ).offset(offset).limit(page_size).all()

        return {
            "bookings": [self._build_provider_booking_response(b) for b in bookings],
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }

    def update_booking_status(
        self,
        provider_account: ProviderAccount,
        booking_id: int,
        new_status: str,
        notes: Optional[str] = None
    ) -> ProviderBookingResponse:
        """
        Update booking status (provider only)

        Valid transitions:
        - pending -> confirmed
        - confirmed -> in_progress, cancelled
        - in_progress -> completed, cancelled
        """
        booking = (
            self.db.query(Booking)
            .options(
                joinedload(Booking.time_slot),
                joinedload(Booking.service_category)
            )
            .filter(
                Booking.id == booking_id,
                Booking.provider_id == provider_account.provider_id
            )
            .first()
        )

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )

        # Get current status string
        current_status = (
            booking.status.value
            if hasattr(booking.status, 'value')
            else str(booking.status)
        )

        # Valid status transitions
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['in_progress', 'cancelled'],
            'in_progress': ['completed', 'cancelled'],
        }

        if current_status not in valid_transitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update booking with status: {current_status}"
            )

        if new_status not in valid_transitions[current_status]:
            allowed = valid_transitions[current_status]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid transition: {current_status} -> {new_status}. "
                    f"Allowed: {allowed}"
                )
            )

        # Apply update
        try:
            booking.status = BookingStatus(new_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status value: {new_status}"
            )

        if new_status == 'completed':
            booking.completed_at = datetime.utcnow()
        elif new_status == 'cancelled':
            booking.cancelled_at = datetime.utcnow()
            booking.cancellation_reason = notes or "Cancelled by provider"
        elif new_status == 'confirmed':
            booking.confirmed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(booking)

        logger.info(
            f"Booking {booking.booking_reference} "
            f"updated: {current_status} -> {new_status} "
            f"by provider {provider_account.id}"
        )

        return self._build_provider_booking_response(booking)

    # ============================================
    # Time Slot Management
    # ============================================

    def get_time_slots(
        self,
        provider_account: ProviderAccount,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_booked: bool = True
    ) -> TimeSlotListResponse:
        """
        Get provider's time slots with availability info

        Args:
            provider_account: Current provider
            start_date: Filter from date (defaults to today)
            end_date: Filter to date
            include_booked: Whether to include booked slots

        Returns:
            TimeSlotListResponse with counts
        """
        query = self.db.query(TimeSlot).filter(
            TimeSlot.provider_id == provider_account.provider_id
        )

        # Default to today onwards
        effective_start = start_date or date.today()
        query = query.filter(TimeSlot.slot_date >= effective_start)

        if end_date:
            query = query.filter(TimeSlot.slot_date <= end_date)

        if not include_booked:
            query = query.filter(TimeSlot.is_booked == False)

        slots = query.order_by(
            TimeSlot.slot_date,
            TimeSlot.slot_time
        ).all()

        slot_responses = [
            TimeSlotResponse(
                id=slot.id,
                date=slot.slot_date.isoformat(),
                time=slot.slot_time.isoformat(),
                duration_minutes=slot.duration_minutes,
                is_booked=slot.is_booked,
                booking_id=slot.booking.id if slot.booking else None
            )
            for slot in slots
        ]

        total = len(slot_responses)
        booked = sum(1 for s in slot_responses if s.is_booked)
        available = total - booked

        return TimeSlotListResponse(
            slots=slot_responses,
            total_count=total,
            available_count=available,
            booked_count=booked
        )

    def create_time_slots(
        self,
        provider_account: ProviderAccount,
        slot_date: date,
        start_time: time_type,
        end_time: time_type,
        duration_minutes: int = 60
    ) -> TimeSlotListResponse:
        """
        Create multiple time slots for a day
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"=== CREATE TIME SLOTS DEBUG ===")
        logger.info(f"Provider Account ID: {provider_account.id}")
        logger.info(f"Provider ID from account: {provider_account.provider_id}")
        logger.info(f"Slot Date: {slot_date}")
        logger.info(f"Start Time: {start_time}, End Time: {end_time}")
        logger.info(f"Duration: {duration_minutes}")
        
        if slot_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create slots for past dates"
            )

        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time must be before end_time"
            )

        created_slots = []
        skipped = 0

        # Generate slots
        current_dt = datetime.combine(date.today(), start_time)
        end_dt = datetime.combine(date.today(), end_time)
        
        logger.info(f"Will create slots from {current_dt} to {end_dt}")

        while current_dt < end_dt:
            current_time = current_dt.time()
            
            logger.info(f"Checking slot at {current_time}")

            # Check for duplicate
            existing = self.db.query(TimeSlot).filter(
                TimeSlot.provider_id == provider_account.provider_id,
                TimeSlot.slot_date == slot_date,
                TimeSlot.slot_time == current_time
            ).first()

            if not existing:
                slot = TimeSlot(
                    provider_id=provider_account.provider_id,
                    slot_date=slot_date,
                    slot_time=current_time,
                    duration_minutes=duration_minutes,
                    is_booked=False
                )
                self.db.add(slot)
                created_slots.append(slot)
                logger.info(f"  Created slot for {current_time}")
            else:
                skipped += 1
                logger.info(f"  Slot at {current_time} already exists")

            current_dt += timedelta(minutes=duration_minutes)

        logger.info(f"Flushing to database...")
        self.db.flush()  # This will assign IDs
        
        logger.info(f"Committing {len(created_slots)} slots...")
        self.db.commit()

        # Refresh all created slots
        for slot in created_slots:
            self.db.refresh(slot)
            logger.info(f"  Slot ID: {slot.id}, Time: {slot.slot_time}")

        # Verify they were saved
        verify_slots = self.db.query(TimeSlot).filter(
            TimeSlot.provider_id == provider_account.provider_id,
            TimeSlot.slot_date == slot_date
        ).all()
        
        logger.info(f"VERIFICATION: Found {len(verify_slots)} slots in DB for provider {provider_account.provider_id} on {slot_date}")
        for slot in verify_slots:
            logger.info(f"  DB Slot: ID={slot.id}, Time={slot.slot_time}, Booked={slot.is_booked}")

        logger.info(
            f"Created {len(created_slots)} slots for provider "
            f"{provider_account.provider_id} on {slot_date} "
            f"(skipped {skipped} existing)"
        )

        slot_responses = [
            TimeSlotResponse(
                id=slot.id,
                date=slot.slot_date.isoformat(),
                time=slot.slot_time.isoformat(),
                duration_minutes=slot.duration_minutes,
                is_booked=slot.is_booked,
                booking_id=None
            )
            for slot in created_slots
        ]

        return TimeSlotListResponse(
            slots=slot_responses,
            total_count=len(slot_responses),
            available_count=len(slot_responses),
            booked_count=0
        )
    
    def delete_time_slot(
        self,
        provider_account: ProviderAccount,
        slot_id: int
    ) -> bool:
        """Delete an unbooked time slot"""
        slot = self.db.query(TimeSlot).filter(
            TimeSlot.id == slot_id,
            TimeSlot.provider_id == provider_account.provider_id
        ).first()

        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time slot not found"
            )

        if slot.is_booked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a booked slot"
            )

        self.db.delete(slot)
        self.db.commit()

        logger.info(f"Slot {slot_id} deleted by provider {provider_account.provider_id}")
        return True

    # ============================================
    # Profile Management
    # ============================================

    def get_provider_profile(
        self,
        provider_account: ProviderAccount
    ) -> ProviderProfileResponse:
        """Get complete provider profile"""
        provider = provider_account.provider

        return ProviderProfileResponse(
            id=provider.id,
            name=provider.name,
            phone=provider.phone,
            email=provider_account.email,
            service_category=provider.service_category.name_en,
            address_text=provider.address_text,
            rating=float(provider.rating),
            total_reviews=provider.total_reviews,
            is_available=provider.is_available,
            is_verified=provider_account.is_verified,
            years_experience=provider.years_experience,
            price_range=provider.price_range,
            profile_image_url=provider.profile_image_url
        )

    def update_provider_profile(
        self,
        provider_account: ProviderAccount,
        update_request: ProviderProfileUpdateRequest
    ) -> ProviderProfileResponse:
        """
        Update provider profile

        Args:
            provider_account: Current provider
            update_request: Fields to update

        Returns:
            Updated provider profile
        """
        provider = provider_account.provider

        # Only update provided fields
        update_data = update_request.model_dump(exclude_none=True)

        allowed_fields = {
            'name', 'phone', 'address_text', 'years_experience',
            'price_range', 'is_available', 'profile_image_url'
        }

        updated_fields = []
        for field, value in update_data.items():
            if field in allowed_fields and hasattr(provider, field):
                setattr(provider, field, value)
                updated_fields.append(field)

        if not updated_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        provider.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(provider)

        logger.info(
            f"Provider {provider.id} updated fields: {updated_fields}"
        )

        return self.get_provider_profile(provider_account)

    # ============================================
    # Analytics
    # ============================================

    def get_analytics(
        self,
        provider_account: ProviderAccount
    ) -> ProviderAnalyticsResponse:
        from sqlalchemy import text

        provider_id = provider_account.provider_id
        provider = provider_account.provider

        total_bookings = self.db.execute(
            text("SELECT COUNT(*) FROM bookings WHERE provider_id = :pid"),
            {"pid": provider_id}
        ).scalar() or 0

        completed = self.db.execute(
            text("SELECT COUNT(*) FROM bookings WHERE provider_id = :pid AND status::text = 'completed'"),
            {"pid": provider_id}
        ).scalar() or 0

        cancelled = self.db.execute(
            text("SELECT COUNT(*) FROM bookings WHERE provider_id = :pid AND status::text = 'cancelled'"),
            {"pid": provider_id}
        ).scalar() or 0

        pending = self.db.execute(
            text("SELECT COUNT(*) FROM bookings WHERE provider_id = :pid AND status::text = 'pending'"),
            {"pid": provider_id}
        ).scalar() or 0

        now = datetime.utcnow()

        current_month_bookings = self.db.execute(
            text("""
                SELECT COUNT(*) FROM bookings
                WHERE provider_id = :pid
                AND EXTRACT(month FROM created_at) = :month
                AND EXTRACT(year FROM created_at) = :year
            """),
            {"pid": provider_id, "month": now.month, "year": now.year}
        ).scalar() or 0

        total_slots = self.db.execute(
            text("SELECT COUNT(*) FROM time_slots WHERE provider_id = :pid AND slot_date >= CURRENT_DATE"),
            {"pid": provider_id}
        ).scalar() or 0

        booked_slots = self.db.execute(
            text("SELECT COUNT(*) FROM time_slots WHERE provider_id = :pid AND slot_date >= CURRENT_DATE AND is_booked = TRUE"),
            {"pid": provider_id}
        ).scalar() or 0

        available_slots = total_slots - booked_slots
        completion_rate   = (completed / total_bookings * 100) if total_bookings > 0 else 0.0
        cancellation_rate = (cancelled / total_bookings * 100) if total_bookings > 0 else 0.0
        utilization_rate  = (booked_slots / total_slots * 100) if total_slots > 0 else 0.0

        return ProviderAnalyticsResponse(
            total_bookings=total_bookings,
            completed_bookings=completed,
            cancelled_bookings=cancelled,
            pending_bookings=pending,
            completion_rate=round(completion_rate, 2),
            cancellation_rate=round(cancellation_rate, 2),
            current_month_bookings=current_month_bookings,
            average_rating=float(provider.rating),
            total_reviews=provider.total_reviews,
            total_slots=total_slots,
            available_slots=available_slots,
            booked_slots=booked_slots,
            utilization_rate=round(utilization_rate, 2)
        )

    # ============================================
    # Internal Helpers
    # ============================================

    def _build_provider_booking_response(
        self,
        booking: Booking
    ) -> ProviderBookingResponse:
        """Build provider booking response with safe attribute access"""
        return ProviderBookingResponse(
            id=booking.id,
            booking_reference=booking.booking_reference,
            user_name=booking.user_name,
            user_phone=booking.user_phone,
            service_type=(
                booking.service_category.name_en
                if booking.service_category else "Unknown"
            ),
            scheduled_date=booking.time_slot.slot_date,
            scheduled_time=booking.time_slot.slot_time,
            location=booking.address_requested,
            status=(
                booking.status.value
                if hasattr(booking.status, 'value')
                else str(booking.status)
            ),
            special_instructions=booking.special_instructions,
            created_at=booking.created_at
        )
"""
HTL (Hold-to-Lock) service
Manages temporary slot reservations with automatic expiration
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import uuid

from src.database.models import (
    HTLReservation, User, Provider, TimeSlot, ChatSession
)
from src.models.htl import HTLReservationResponse
from src.core.config import settings
from src.utils.logger import get_logger
from fastapi import HTTPException, status

logger = get_logger(__name__)


class HTLService:
    """HTL reservation management service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def reserve_slot(
        self,
        user: User,
        session_id: uuid.UUID,
        provider_id: int,
        time_slot_id: int
    ) -> HTLReservationResponse:
        """
        Create HTL reservation (5-minute hold)
        
        Args:
            user: Current user
            session_id: Chat session ID
            provider_id: Selected provider
            time_slot_id: Selected time slot
        
        Returns:
            HTL reservation details
        
        Raises:
            HTTPException: If slot already reserved/booked
        """
        # Verify chat session belongs to user
        chat = self.db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user.id
        ).first()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Check if slot exists and is available
        slot = self.db.query(TimeSlot).filter(
            TimeSlot.id == time_slot_id,
            TimeSlot.provider_id == provider_id
        ).with_for_update().first()  # Lock row
        
        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time slot not found"
            )
        
        if slot.is_booked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Time slot already booked"
            )
        
        # Check for existing active HTL on this slot
        existing_htl = self.db.query(HTLReservation).filter(
            HTLReservation.time_slot_id == time_slot_id,
            HTLReservation.is_confirmed == False,
            HTLReservation.is_expired == False,
            HTLReservation.expires_at > datetime.utcnow()
        ).first()
        
        if existing_htl:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Slot is currently held by another user"
            )
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.HTL_RESERVATION_MINUTES
        )
        
        # Create HTL reservation
        htl = HTLReservation(
            session_id=session_id,
            user_id=user.id,
            provider_id=provider_id,
            time_slot_id=time_slot_id,
            reserved_at=datetime.utcnow(),
            expires_at=expires_at,
            is_confirmed=False,
            is_expired=False
        )
        
        self.db.add(htl)
        self.db.commit()
        self.db.refresh(htl)
        
        logger.info(f"HTL reservation {htl.id} created for user {user.id}, slot {time_slot_id}")
        
        # Get provider details
        provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
        
        return self._build_htl_response(htl, provider, slot)
    
    def confirm_reservation(
        self,
        user: User,
        htl_reservation_id: int,
        special_instructions: Optional[str] = None
    ) -> dict:
        """
        Confirm HTL and convert to actual booking
        
        Args:
            user: Current user
            htl_reservation_id: HTL reservation ID
            special_instructions: Optional booking notes
        
        Returns:
            Booking details
        
        Raises:
            HTTPException: If HTL expired or invalid
        """
        # Get HTL reservation with lock
        htl = self.db.query(HTLReservation).filter(
            HTLReservation.id == htl_reservation_id,
            HTLReservation.user_id == user.id
        ).with_for_update().first()
        
        if not htl:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="HTL reservation not found"
            )
        
        # Check if already confirmed
        if htl.is_confirmed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="HTL already confirmed"
            )
        
        # Check if expired
        if htl.expires_at < datetime.utcnow() or htl.is_expired:
            htl.is_expired = True
            htl.expired_at = datetime.utcnow()
            self.db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="HTL reservation expired"
            )
        
        # Create booking using existing DatabaseTools
        from src.tools import DatabaseTools
        db_tools = DatabaseTools(self.db)
        
        provider = self.db.query(Provider).filter(Provider.id == htl.provider_id).first()
        
        booking = db_tools.create_booking_record(
            session_id=str(htl.session_id),
            user_phone=user.phone,
            provider_id=htl.provider_id,
            service_category_id=provider.service_category_id,
            time_slot_id=htl.time_slot_id,
            user_name=user.full_name,
            special_instructions=special_instructions
        )
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create booking"
            )
        
        # Mark HTL as confirmed
        htl.is_confirmed = True
        htl.confirmed_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"HTL {htl.id} confirmed, booking {booking.id} created")
        
        return {
            "booking_id": booking.id,
            "booking_reference": booking.booking_reference,
            "htl_id": htl.id,
            "status": "confirmed"
        }
    
    def cancel_reservation(self, user: User, htl_reservation_id: int) -> bool:
        """Cancel HTL reservation"""
        
        htl = self.db.query(HTLReservation).filter(
            HTLReservation.id == htl_reservation_id,
            HTLReservation.user_id == user.id,
            HTLReservation.is_confirmed == False
        ).first()
        
        if not htl:
            return False
        
        htl.is_expired = True
        htl.expired_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"HTL {htl.id} cancelled by user")
        
        return True
    
    def get_active_reservations(self, user: User) -> List[HTLReservationResponse]:
        """Get user's active HTL reservations"""
        
        htls = self.db.query(HTLReservation).filter(
            HTLReservation.user_id == user.id,
            HTLReservation.is_confirmed == False,
            HTLReservation.is_expired == False,
            HTLReservation.expires_at > datetime.utcnow()
        ).all()
        
        results = []
        for htl in htls:
            provider = self.db.query(Provider).filter(Provider.id == htl.provider_id).first()
            slot = self.db.query(TimeSlot).filter(TimeSlot.id == htl.time_slot_id).first()
            results.append(self._build_htl_response(htl, provider, slot))
        
        return results
    
    def expire_old_reservations(self) -> int:
        """
        Background task: Expire old HTL reservations
        
        Returns:
            Number of reservations expired
        """
        expired = self.db.query(HTLReservation).filter(
            HTLReservation.is_confirmed == False,
            HTLReservation.is_expired == False,
            HTLReservation.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired)
        
        for htl in expired:
            htl.is_expired = True
            htl.expired_at = datetime.utcnow()
        
        self.db.commit()
        
        if count > 0:
            logger.info(f"Expired {count} HTL reservations")
        
        return count
    
    def _build_htl_response(
        self, 
        htl: HTLReservation, 
        provider: Provider, 
        slot: TimeSlot
    ) -> HTLReservationResponse:
        """Build HTL response model"""
        
        time_remaining = (htl.expires_at - datetime.utcnow()).total_seconds()
        
        return HTLReservationResponse(
            id=htl.id,
            session_id=htl.session_id,
            provider_id=provider.id,
            provider_name=provider.name,
            time_slot_id=slot.id,
            slot_date=slot.slot_date.isoformat(),
            slot_time=slot.slot_time.isoformat(),
            reserved_at=htl.reserved_at,
            expires_at=htl.expires_at,
            time_remaining_seconds=max(0, int(time_remaining)),
            is_confirmed=htl.is_confirmed,
            is_expired=htl.is_expired
        )
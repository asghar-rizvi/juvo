from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from src.models import (
    ServiceIntent, ProviderMatch, BookingRequest,
    BookingConfirmation, AvailableSlot
)
from src.utils.gemini_client import get_gemini_client
from src.utils.logger import AgentLogger
from src.database.connection import get_db
from src.database.models import Booking
from src.tools import DatabaseTools


class BookingAgent:
    """
    Agent responsible for booking orchestration
    Handles slot selection, booking creation, and confirmation
    """
    
    def __init__(self):
        self.name = "BookingAgent"
        self.logger = AgentLogger(self.name)
        self.gemini = get_gemini_client()
    
    async def create_booking(
        self,
        intent: ServiceIntent,
        selected_provider: ProviderMatch,
        user_phone: str,
        user_name: Optional[str],
        session_id: str,
        location_coords: Optional[tuple] = None,
        special_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a booking with the selected provider
        
        Args:
            intent: User's service intent
            selected_provider: Selected provider
            user_phone: User's phone number
            user_name: User's name
            session_id: Session identifier
            location_coords: (latitude, longitude) tuple
            special_instructions: Special requirements
        
        Returns:
            Booking confirmation details
        """
        self.logger.log_workflow_step(
            "booking_creation",
            "started",
            {
                "provider_id": selected_provider.provider_id,
                "user_phone": user_phone,
                "session_id": session_id
            }
        )
        
        try:
            with get_db() as db:
                tools = DatabaseTools(db)
                
                # Step 1: Get available slots for the provider
                self.logger.log_tool_call(
                    "get_available_slots",
                    {
                        "provider_id": selected_provider.provider_id,
                        "date": intent.preferred_date.isoformat()
                    }
                )
                
                available_slots = tools.get_available_slots(
                    provider_id=selected_provider.provider_id,
                    start_date=intent.preferred_date,
                    end_date=intent.preferred_date,
                    limit=20
                )
                
                if not available_slots:
                    self.logger.log_error(
                        "no_slots_available",
                        f"No available slots for provider {selected_provider.provider_id} on {intent.preferred_date}"
                    )
                    return {
                        'session_id': session_id,
                        'status': 'no_slots_available',
                        'message': f"No available slots on {intent.preferred_date}",
                        'alternative_dates': []  # Could suggest other dates
                    }
                
                self.logger.log_tool_call(
                    "get_available_slots",
                    {},
                    {"slot_count": len(available_slots)},
                    success=True
                )
                
                # Step 2: Select best slot based on time preference
                selected_slot = self._select_best_slot(
                    available_slots,
                    intent.preferred_time
                )
                
                self.logger.log_decision(
                    {
                        "slot_id": selected_slot.slot_id,
                        "slot_time": selected_slot.slot_time.isoformat()
                    },
                    f"Selected slot at {selected_slot.slot_time} based on preference '{intent.preferred_time}'",
                    confidence=0.85
                )
                
                # Step 3: Get service category ID
                category = tools.find_service_category(intent.service_type)
                if not category:
                    raise ValueError(f"Service category not found: {intent.service_type}")
                
                # Step 4: Create booking in database
                self.logger.log_tool_call(
                    "create_booking_record",
                    {
                        "provider_id": selected_provider.provider_id,
                        "slot_id": selected_slot.slot_id
                    }
                )
                
                booking = tools.create_booking_record(
                    session_id=session_id,
                    user_phone=user_phone,
                    provider_id=selected_provider.provider_id,
                    service_category_id=category.id,
                    time_slot_id=selected_slot.slot_id,
                    user_name=user_name,
                    location_coords=location_coords,
                    address_text=intent.location,
                    special_instructions=special_instructions
                )
                
                if not booking:
                    self.logger.log_error(
                        "booking_creation_failed",
                        "Database booking creation failed (possibly double-booked)"
                    )
                    return {
                        'session_id': session_id,
                        'status': 'booking_failed',
                        'message': 'Slot was just booked by someone else. Please select another time.'
                    }
                
                self.logger.log_tool_call(
                    "create_booking_record",
                    {},
                    {
                        "booking_id": booking.id,
                        "booking_reference": booking.booking_reference
                    },
                    success=True
                )
                
                # Step 5: Generate confirmation message using Gemini
                confirmation_message = self.gemini.generate_booking_confirmation_message(
                    booking_data={
                        'booking_reference': booking.booking_reference,
                        'provider_name': selected_provider.name,
                        'service_type': intent.service_type,
                        'scheduled_date': intent.preferred_date.isoformat(),
                        'scheduled_time': selected_slot.slot_time.isoformat(),
                        'provider_phone': selected_provider.phone,
                        'estimated_price': selected_provider.price_range
                    },
                    language=intent.language_detected.value
                )
                
                # Step 6: Create confirmation object
                confirmation = BookingConfirmation(
                    booking_id=booking.id,
                    booking_reference=booking.booking_reference,
                    provider_name=selected_provider.name,
                    service_type=intent.service_type,
                    scheduled_date=intent.preferred_date,
                    scheduled_time=selected_slot.slot_time,
                    provider_phone=selected_provider.phone,
                    estimated_price=None,  # Will be set later
                    confirmation_message=confirmation_message,
                    status=booking.status,
                    created_at=booking.created_at
                )
                
                # Step 7: Log to conversation
                tools.log_conversation(
                    session_id=session_id,
                    agent_name=self.name,
                    agent_response=confirmation_message,
                    tool_calls={
                        "booking_created": booking.id,
                        "slot_reserved": selected_slot.slot_id
                    },
                    reasoning=f"Created booking {booking.booking_reference} for {selected_provider.name}"
                )
                
                self.logger.log_decision(
                    {
                        "booking_id": booking.id,
                        "booking_reference": booking.booking_reference
                    },
                    f"Booking confirmed for {user_phone} with {selected_provider.name}",
                    confidence=1.0
                )
            
            result = {
                'session_id': session_id,
                'booking': confirmation,
                'status': 'success'
            }
            
            self.logger.log_workflow_step(
                "booking_creation",
                "completed",
                {"booking_reference": confirmation.booking_reference}
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error(
                "booking_creation_error",
                str(e),
                {
                    "provider_id": selected_provider.provider_id,
                    "session_id": session_id
                }
            )
            raise
    
    def _select_best_slot(
        self,
        available_slots: List[AvailableSlot],
        time_preference: Optional[str]
    ) -> AvailableSlot:
        """
        Select best slot based on time preference
        
        Args:
            available_slots: List of available slots
            time_preference: User's time preference (morning/afternoon/evening)
        
        Returns:
            Selected slot
        """
        if not time_preference:
            # Default to first available slot
            return available_slots[0]
        
        # Define time ranges
        time_ranges = {
            'morning': (9, 12),
            'subah': (9, 12),
            'afternoon': (12, 17),
            'dopahar': (12, 17),
            'evening': (17, 20),
            'sham': (17, 20)
        }
        
        # Find matching range
        pref_lower = time_preference.lower()
        for key, (start_hour, end_hour) in time_ranges.items():
            if key in pref_lower:
                # Filter slots in this time range
                matching_slots = [
                    slot for slot in available_slots
                    if start_hour <= slot.slot_time.hour < end_hour
                ]
                if matching_slots:
                    return matching_slots[0]
        
        # Fallback to first available
        return available_slots[0]
    
    def create_booking_sync(self, **kwargs) -> Dict[str, Any]:
        """Synchronous version"""
        import asyncio
        return asyncio.run(self.create_booking(**kwargs))
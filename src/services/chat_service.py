"""
Chat service - Integrates Phase 2 agents with Phase 4 API
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import re

from src.database.models import ChatSession, User
from src.agents.intent_agent import IntentAgent
from src.agents.discovery_agent import ProviderDiscoveryAgent
from src.models.chat import (
    ChatResponse, ChatStep, ProviderOption, TimeSlotOption
)
from src.models import ServiceIntent
from src.utils.gemini_client import get_gemini_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """
    Chat service orchestrating AI agents
    Manages conversation state and agent interactions
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.intent_agent = IntentAgent()
        self.discovery_agent = ProviderDiscoveryAgent()
        self.gemini = get_gemini_client()
    
    def start_chat(self, user: User, initial_message: Optional[str] = None) -> ChatResponse:
        """
        Start new chat session
        """
        session_id = uuid.uuid4()
        
        chat_session = ChatSession(
            session_id=session_id,
            user_id=user.id,
            current_step=ChatStep.INITIAL.value,
            is_active=True,
            started_at=datetime.utcnow(),
            last_message_at=datetime.utcnow()
        )
        
        self.db.add(chat_session)
        self.db.commit()
        self.db.refresh(chat_session)
        
        logger.info(f"Started chat session {session_id} for user {user.id}")
        
        if initial_message:
            return self.process_message(chat_session, user, initial_message)
        
        welcome_message = self._generate_welcome_message(user.preferred_language)
        
        return ChatResponse(
            session_id=session_id,
            current_step=ChatStep.INITIAL,
            agent_message=welcome_message,
            next_action="Tell me what service you need (e.g., AC technician, plumber)"
        )
    
    def process_message(
        self, 
        chat_session: ChatSession, 
        user: User, 
        message: str
    ) -> ChatResponse:
        """Process user message and return agent response"""
        current_step = chat_session.current_step
        
        logger.info(f"Processing message in step {current_step}: {message[:50]}")
        
        # NEW: Skip confirmation - go directly to provider search
        if current_step == ChatStep.INITIAL.value:
            return self._handle_initial_intent_and_search(chat_session, user, message)
        
        elif current_step == ChatStep.INTENT_EXTRACTED.value:
            # Redirect to provider search directly (no confirmation needed)
            return self._search_providers(chat_session, user)
        
        elif current_step == ChatStep.PROVIDERS_SHOWN.value:
            return self._handle_provider_selection(chat_session, user, message)
        
        elif current_step == ChatStep.PROVIDER_SELECTED.value:
            return self._handle_booking_confirmation(chat_session, user, message)
        
        else:
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep(current_step),
                agent_message="I'm not sure what to do next. Let's start over.",
                next_action="Please describe the service you need"
            )
    
    # def _handle_initial_intent(
    #     self, 
    #     chat_session: ChatSession, 
    #     user: User, 
    #     message: str
    # ) -> ChatResponse:
    #     """Extract intent from user's initial message"""
    #     try:
    #         intent_result = self.intent_agent.process_input_sync(
    #             user_input=message,
    #             session_id=str(chat_session.session_id)
    #         )
            
    #         intent: ServiceIntent = intent_result['intent']
            
    #         chat_session.intent_data = intent.model_dump(mode='json')
    #         chat_session.current_step = ChatStep.INTENT_EXTRACTED.value
    #         chat_session.last_message_at = datetime.utcnow()
    #         self.db.commit()
            
    #         confirm_message = self._generate_intent_confirmation(intent)
            
    #         return ChatResponse(
    #             session_id=chat_session.session_id,
    #             current_step=ChatStep.INTENT_EXTRACTED,
    #             agent_message=confirm_message,
    #             intent=intent.model_dump(mode='json'),
    #             next_action="Reply 'yes' to search for providers, or provide more details"
    #         )
            
    #     except Exception as e:
    #         logger.error(f"Intent extraction failed: {str(e)}")
            
    #         return ChatResponse(
    #             session_id=chat_session.session_id,
    #             current_step=ChatStep.INITIAL,
    #             agent_message="Sorry, I didn't understand that. Can you tell me what service you need and where?",
    #             next_action="Example: 'I need an AC technician tomorrow in G-13'"
    #         )
    
    # def _handle_intent_confirmation(
    #     self, 
    #     chat_session: ChatSession, 
    #     user: User, 
    #     message: str
    # ) -> ChatResponse:
    #     """Handle user confirming intent or modifying it"""
    #     message_lower = message.lower()
        
    #     if any(word in message_lower for word in ['yes', 'haan', 'theek', 'ok', 'correct']):
    #         return self._search_providers(chat_session, user)
        
    #     elif any(word in message_lower for word in ['no', 'nahi', 'change', 'different']):
    #         chat_session.current_step = ChatStep.INITIAL.value
    #         self.db.commit()
            
    #         return ChatResponse(
    #             session_id=chat_session.session_id,
    #             current_step=ChatStep.INITIAL,
    #             agent_message="Okay, let's start again. What service do you need?",
    #             next_action="Describe your service requirement"
    #         )
        
    #     else:
    #         return self._handle_initial_intent(chat_session, user, message)
    
    def _handle_initial_intent_and_search(
        self, 
        chat_session: ChatSession, 
        user: User, 
        message: str
    ) -> ChatResponse:
        """Extract intent and immediately search for providers (no confirmation)"""
        try:
            intent_result = self.intent_agent.process_input_sync(
                user_input=message,
                session_id=str(chat_session.session_id)
            )
            
            intent: ServiceIntent = intent_result['intent']
            
            # Check if intent is valid
            if intent.location == "Unknown" or intent.service_type == "General Service":
                return ChatResponse(
                    session_id=chat_session.session_id,
                    current_step=ChatStep.INITIAL,
                    agent_message="I couldn't understand your request. Please tell me:\n- What service you need\n- Your location (e.g., G-13, F-10)\n- When you need it",
                    next_action="Example: 'I need an AC technician tomorrow in G-13'"
                )
            
            # Store intent and go directly to provider search
            chat_session.intent_data = intent.model_dump(mode='json')
            chat_session.current_step = ChatStep.INTENT_EXTRACTED.value
            chat_session.last_message_at = datetime.utcnow()
            self.db.commit()
            
            # Immediately search for providers
            return self._search_providers(chat_session, user)
            
        except Exception as e:
            logger.error(f"Intent extraction failed: {str(e)}")
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.INITIAL,
                agent_message="Sorry, I didn't understand that. Can you tell me what service you need and where?",
                next_action="Example: 'I need an AC technician tomorrow in G-13'"
            )
            
    def _generate_provider_with_slots_message(self, providers: List[dict], preferred_date) -> str:
        """Generate message showing providers with their time slots"""
        
        message = f"📋 **Available Providers for {preferred_date}:**\n\n"
        
        for i, provider in enumerate(providers, 1):
            message += f"**{i}. {provider['name']}**\n"
            message += f"   ⭐ Rating: {provider['rating']} ({provider['total_reviews']} reviews)\n"
            message += f"   📍 Distance: {provider['distance_km']} km\n"
            message += f"   💰 Price: {provider.get('price_range', 'Call for quote')}\n"
            message += f"   ✅ Verified: {'Yes' if provider.get('is_verified', False) else 'No'}\n"
            
            time_slots = provider.get('time_slots', [])
            if time_slots:
                message += f"   ⏰ **Available times:**\n"
                for j, slot in enumerate(time_slots[:5], 1):  # Show max 5 slots
                    slot_time = slot['slot_time'][:5]  # Get HH:MM
                    message += f"      Slot {j}: {slot_time}\n"
            else:
                message += f"   ⚠️ No slots available on this date\n"
            
            message += "\n"
        
        message += "💡 **How to book:**\n"
        message += "   • Type: `provider 1, slot 1` to select Provider 1, Slot 1\n"
        message += "   • Or: `1,2` for provider 1, slot 2\n"
        message += "   • Or: `Ali AC at 10:00` to select by name and time\n"
        
        return message

    def _search_providers(
        self, 
        chat_session: ChatSession, 
        user: User
    ) -> ChatResponse:
        """Search for providers with their available time slots"""
        
        intent_data = chat_session.intent_data
        intent = ServiceIntent(**intent_data)
        
        logger.info(f"=== SEARCHING PROVIDERS ===")
        logger.info(f"Service: {intent.service_type}")
        logger.info(f"Location: {intent.location}")
        logger.info(f"Preferred date: {intent.preferred_date}")
        logger.info(f"Preferred time: {intent.preferred_time}")
        
        discovery_result = self.discovery_agent.find_and_rank_providers_sync(
            intent=intent,
            session_id=str(chat_session.session_id),
            max_distance_km=15.0,
            max_results=3
        )
        
        logger.info(f"Discovery result status: {discovery_result.get('status')}")
        logger.info(f"Providers found: {len(discovery_result.get('providers', []))}")
        
        if discovery_result['status'] != 'success' or not discovery_result['providers']:
            chat_session.is_active = False
            self.db.commit()
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.COMPLETED,
                agent_message=f"Sorry, no {intent.service_type} providers found near {intent.location}",
                next_action="Start a new search or try a different location"
            )
        
        # Fetch time slots for each provider
        from src.tools import DatabaseTools
        tools = DatabaseTools(self.db)
        
        providers_with_slots = []
        for p in discovery_result['providers']:
            logger.info(f"--- Checking provider: {p.name} (ID: {p.provider_id}) ---")
            
            # Log what slots exist for this provider
            from src.database.models import TimeSlot
            all_slots = self.db.query(TimeSlot).filter(
                TimeSlot.provider_id == p.provider_id
            ).all()
            logger.info(f"Total slots in DB for this provider: {len(all_slots)}")
            for slot in all_slots:
                logger.info(f"  Slot ID: {slot.id}, Date: {slot.slot_date}, Booked: {slot.is_booked}")
            
            # Get slots for preferred date
            slots = tools.get_available_slots(
                provider_id=p.provider_id,
                start_date=intent.preferred_date,
                end_date=intent.preferred_date,
                limit=5
            )
            
            logger.info(f"Available slots on {intent.preferred_date}: {len(slots)}")
            for slot in slots:
                logger.info(f"  Slot ID: {slot.slot_id}, Time: {slot.slot_time}")
            
            providers_with_slots.append({
                "provider_id": p.provider_id,
                "name": p.name,
                "distance_km": p.distance_km,
                "rating": float(p.rating),
                "total_reviews": p.total_reviews,
                "phone": p.phone,
                "price_range": p.price_range,
                "available_slots_count": len(slots),
                "time_slots": [
                    {
                        "slot_id": slot.slot_id,
                        "slot_date": slot.slot_date.isoformat(),
                        "slot_time": slot.slot_time.strftime('%H:%M:%S'),
                        "duration_minutes": slot.duration_minutes
                    }
                    for slot in slots
                ]
            })
        
        chat_session.selected_providers = providers_with_slots
        chat_session.current_step = ChatStep.PROVIDERS_SHOWN.value
        chat_session.last_message_at = datetime.utcnow()
        self.db.commit()
        
        # Log summary
        total_slots = sum(len(p['time_slots']) for p in providers_with_slots)
        logger.info(f"=== SUMMARY: {len(providers_with_slots)} providers, {total_slots} total time slots ===")
        
        return ChatResponse(
            session_id=chat_session.session_id,
            current_step=ChatStep.PROVIDERS_SHOWN,
            agent_message=self._generate_provider_with_slots_message(providers_with_slots, intent.preferred_date),
            providers=providers_with_slots,
            next_action="Select a provider and time slot. Example: 'provider 1, slot 1' or 'Ali AC at 10:00'"
        )
    
    def _handle_provider_selection(
        self, 
        chat_session: ChatSession, 
        user: User, 
        message: str
    ) -> ChatResponse:
        """Handle user selecting a provider AND time slot"""
        
        import re
        message_lower = message.lower().strip()
        
        logger.info(f"=== PROVIDER SELECTION ===")
        logger.info(f"Raw message: '{message}'")
        
        providers = chat_session.selected_providers
        if not providers:
            logger.error("No providers in session")
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.PROVIDERS_SHOWN,
                agent_message="No providers found. Please start a new search.",
                next_action="Type your service request"
            )
        
        # Parse selection
        numbers = re.findall(r'\d+', message_lower)
        
        selected_provider_idx = None
        selected_slot_id = None
        
        if len(numbers) >= 2:
            provider_num = int(numbers[0]) - 1
            slot_num = int(numbers[1]) - 1
            
            if 0 <= provider_num < len(providers):
                provider = providers[provider_num]
                time_slots = provider.get('time_slots', [])
                if 0 <= slot_num < len(time_slots):
                    selected_provider_idx = provider_num
                    selected_slot_id = time_slots[slot_num]['slot_id']
        
        if selected_provider_idx is None or selected_slot_id is None:
            # Show options again
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.PROVIDERS_SHOWN,
                agent_message=self._generate_provider_with_slots_message(providers, None),
                providers=providers,
                next_action="Type 'provider 1, slot 1' to select"
            )
        
        selected_provider = providers[selected_provider_idx]
        
        # FIX: Create booking DIRECTLY without HTL (simpler flow)
        from src.services.booking_service import BookingService
        booking_service = BookingService(self.db)
        
        try:
            # Get service category from intent
            intent_data = chat_session.intent_data or {}
            service_category_id = 1  # Default to AC Technician
            
            # Create booking directly
            booking = booking_service.create_booking(
                user=user,
                provider_id=selected_provider['provider_id'],
                service_category_id=service_category_id,
                time_slot_id=selected_slot_id,
                special_instructions=None
            )
            
            # End chat session
            chat_session.is_active = False
            chat_session.completed_at = datetime.utcnow()
            self.db.commit()
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.COMPLETED,
                agent_message=f"""
    ✅ **Booking Confirmed!**

    📋 **Booking Reference:** {booking.booking_reference}
    👤 **Provider:** {selected_provider['name']}
    ⭐ **Rating:** {selected_provider['rating']} ({selected_provider['total_reviews']} reviews)
    📅 **Date:** {booking.scheduled_date}
    ⏰ **Time:** {booking.scheduled_time}

    A confirmation has been sent to your phone.

    Thank you for using Juvo! 🎉
                """.strip(),
                booking_id=booking.id,
                next_action="Start a new conversation"
            )
            
        except Exception as e:
            logger.error(f"Booking creation failed: {e}")
            import traceback
            traceback.print_exc()
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.PROVIDERS_SHOWN,
                agent_message=f"Sorry, that time slot is no longer available. Please select another one.",
                providers=providers,
                next_action="Select a different provider or time slot"
            )
            
    def _handle_booking_confirmation(
        self,
        chat_session: ChatSession,
        user: User,
        message: str
    ) -> ChatResponse:
        """Handle user confirming or cancelling the booking"""
        
        message_lower = message.lower().strip()
        logger.info(f"=== BOOKING CONFIRMATION ===")
        logger.info(f"Message: '{message_lower}'")
        
        context_data = chat_session.context_data or {}
        htl_id = context_data.get('htl_id')
        logger.info(f"HTL ID from context: {htl_id}")
        
        if message_lower in ['cancel', 'no', 'nahi']:
            if htl_id:
                from src.services.htl_service import HTLService
                htl_service = HTLService(self.db)
                try:
                    htl_service.cancel_reservation(user, htl_id)
                    logger.info(f"Cancelled HTL {htl_id}")
                except Exception as e:
                    logger.error(f"Failed to cancel HTL: {e}")
            
            chat_session.is_active = False
            chat_session.completed_at = datetime.utcnow()
            self.db.commit()
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.COMPLETED,
                agent_message="Booking cancelled. Start a new search anytime!",
                next_action="Start new conversation"
            )
        
        elif message_lower in ['confirm', 'yes', 'haan', 'theek', 'ok']:
            if not htl_id:
                logger.error("No HTL ID found in context")
                return ChatResponse(
                    session_id=chat_session.session_id,
                    current_step=ChatStep.PROVIDERS_SHOWN,
                    agent_message="No pending booking found. Please select a provider and time slot first.",
                    next_action="Start a new search"
                )
            
            from src.services.htl_service import HTLService
            htl_service = HTLService(self.db)
            
            try:
                booking_result = htl_service.confirm_reservation(
                    user=user,
                    htl_reservation_id=htl_id,
                    special_instructions=None
                )
                
                logger.info(f"Booking confirmed: {booking_result}")
                
                chat_session.is_active = False
                chat_session.completed_at = datetime.utcnow()
                self.db.commit()
                
                return ChatResponse(
                    session_id=chat_session.session_id,
                    current_step=ChatStep.COMPLETED,
                    agent_message=f"""
    ✅ **Booking Confirmed!**

    📋 Booking Reference: **{booking_result.get('booking_reference')}**
    🆔 Booking ID: {booking_result.get('booking_id')}

    A confirmation has been sent to your phone.
    You can view your bookings in the app.

    Thank you for using Juvo! 🎉
                    """.strip(),
                    context_data={
                        'booking_id': booking_result.get('booking_id'),
                        'booking_reference': booking_result.get('booking_reference')
                    },
                    booking_id=booking_result.get('booking_id'),
                    next_action="Start a new conversation for another service"
                )
                
            except Exception as e:
                logger.error(f"Booking confirmation failed: {e}")
                import traceback
                traceback.print_exc()
                return ChatResponse(
                    session_id=chat_session.session_id,
                    current_step=ChatStep.PROVIDER_SELECTED,
                    agent_message=f"Sorry, failed to confirm booking: {str(e)}. Please try again.",
                    next_action="Type 'confirm' again or 'cancel'"
                )
        
        else:
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.PROVIDER_SELECTED,
                agent_message="Please type 'confirm' to complete your booking or 'cancel' to release the slot.",
                next_action="Type 'confirm' or 'cancel'"
            )
    
    def _generate_welcome_message(self, language: str) -> str:
        """Generate welcome message in user's language"""
        messages = {
            'en': "Welcome to Juvo! I'll help you find service providers. What service do you need?",
            'ur': "جوو میں خوش آمدید! میں آپ کو سروس فراہم کرنے والے تلاش کرنے میں مدد کروں گا۔ آپ کو کس سروس کی ضرورت ہے؟",
            'roman_ur': "Juvo mein khush amdeed! Main aap ko service providers dhundne mein madad karunga. Aap ko kis service ki zaroorat hai?"
        }
        return messages.get(language, messages['en'])
    
    def _generate_intent_confirmation(self, intent: ServiceIntent) -> str:
        """Generate intent confirmation message"""
        prompt = f"""
Generate a friendly confirmation message in {intent.language_detected.value}:

Understood details:
- Service: {intent.service_type}
- Location: {intent.location}
- Date: {intent.preferred_date}
- Time: {intent.preferred_time or 'Any time'}

Ask user to confirm if this is correct.
Keep it short and conversational.
        """
        response = self.gemini.conversation_model.generate_content(prompt)
        return response.text.strip()
    
    def get_chat_history(self, session_id: uuid.UUID, user: User) -> Optional[ChatSession]:
        """Get chat session history"""
        return self.db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user.id
        ).first()
    
    def end_chat(self, session_id: uuid.UUID, user: User) -> bool:
        """End chat session"""
        chat = self.get_chat_history(session_id, user)
        if not chat:
            return False
        
        chat.is_active = False
        chat.completed_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Ended chat session {session_id}")
        return True
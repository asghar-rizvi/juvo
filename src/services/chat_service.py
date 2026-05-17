"""
Chat service - Integrates Phase 2 agents with Phase 4 API
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from src.database.models import ChatSession, User
from src.agents.intent_agent import IntentAgent
from src.agents.discovery_agent import ProviderDiscoveryAgent
from src.models.chat import (
    ChatResponse, ChatStep, ProviderOption
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
        
        Args:
            user: Current user
            initial_message: Optional first message
        
        Returns:
            ChatResponse with session details
        """
        # Create chat session
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
        
        # If initial message provided, process it
        if initial_message:
            return self.process_message(chat_session, user, initial_message)
        
        # Otherwise, send welcome message
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
        """
        Process user message and return agent response
        
        Args:
            chat_session: Current chat session
            user: Current user
            message: User's message
        
        Returns:
            ChatResponse with agent reply
        """
        current_step = chat_session.current_step
        
        logger.info(f"Processing message in step {current_step}: {message[:50]}")
        
        # Route to appropriate handler based on current step
        if current_step == ChatStep.INITIAL.value:
            return self._handle_initial_intent(chat_session, user, message)
        
        elif current_step == ChatStep.INTENT_EXTRACTED.value:
            return self._handle_intent_confirmation(chat_session, user, message)
        
        elif current_step == ChatStep.PROVIDERS_SHOWN.value:
            return self._handle_provider_selection(chat_session, user, message)
        
        else:
            # Fallback
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep(current_step),
                agent_message="I'm not sure what to do next. Let's start over.",
                next_action="Please describe the service you need"
            )
    
    def _handle_initial_intent(
        self, 
        chat_session: ChatSession, 
        user: User, 
        message: str
    ) -> ChatResponse:
        """Extract intent from user's initial message"""
        
        try:
            # Use Intent Agent from Phase 2
            intent_result = self.intent_agent.process_input_sync(
                user_input=message,
                session_id=str(chat_session.session_id)
            )
            
            intent: ServiceIntent = intent_result['intent']
            
            # Store intent in chat session
            chat_session.intent_data = intent.model_dump(mode='json')
            chat_session.current_step = ChatStep.INTENT_EXTRACTED.value
            chat_session.last_message_at = datetime.utcnow()
            self.db.commit()
            
            # Generate confirmation message
            confirm_message = self._generate_intent_confirmation(intent)
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.INTENT_EXTRACTED,
                agent_message=confirm_message,
                intent=intent.model_dump(mode='json'),
                next_action="Reply 'yes' to search for providers, or provide more details"
            )
            
        except Exception as e:
            logger.error(f"Intent extraction failed: {str(e)}")
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.INITIAL,
                agent_message="Sorry, I didn't understand that. Can you tell me what service you need and where?",
                next_action="Example: 'I need an AC technician tomorrow in G-13'"
            )
    
    def _handle_intent_confirmation(
        self, 
        chat_session: ChatSession, 
        user: User, 
        message: str
    ) -> ChatResponse:
        """Handle user confirming intent or modifying it"""
        
        message_lower = message.lower()
        
        # Check if user confirms
        if any(word in message_lower for word in ['yes', 'haan', 'theek', 'ok', 'correct']):
            # Proceed to provider discovery
            return self._search_providers(chat_session, user)
        
        # Check if user wants to modify
        elif any(word in message_lower for word in ['no', 'nahi', 'change', 'different']):
            chat_session.current_step = ChatStep.INITIAL.value
            self.db.commit()
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.INITIAL,
                agent_message="Okay, let's start again. What service do you need?",
                next_action="Describe your service requirement"
            )
        
        else:
            # Treat as new intent
            return self._handle_initial_intent(chat_session, user, message)
    
    def _search_providers(
        self, 
        chat_session: ChatSession, 
        user: User
    ) -> ChatResponse:
        """Search for providers based on stored intent"""
        
        intent_data = chat_session.intent_data
        
        # Reconstruct ServiceIntent
        intent = ServiceIntent(**intent_data)
        
        # Use Discovery Agent from Phase 2
        discovery_result = self.discovery_agent.find_and_rank_providers_sync(
            intent=intent,
            session_id=str(chat_session.session_id),
            max_distance_km=15.0,
            max_results=3  # Show top 3
        )
        
        if discovery_result['status'] != 'success' or not discovery_result['providers']:
            chat_session.is_active = False
            self.db.commit()
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.COMPLETED,
                agent_message=f"Sorry, no {intent.service_type} providers found near {intent.location}",
                next_action="Start a new search or try a different location"
            )
        
        # Convert to ProviderOption
        providers = [
            ProviderOption(
                provider_id=p.provider_id,
                name=p.name,
                distance_km=p.distance_km,
                rating=float(p.rating),
                total_reviews=p.total_reviews,
                phone=p.phone,
                price_range=p.price_range,
                available_slots_count=p.available_slots_count
            )
            for p in discovery_result['providers']
        ]
        
        # Store providers in session
        chat_session.selected_providers = [p.model_dump() for p in providers]
        chat_session.current_step = ChatStep.PROVIDERS_SHOWN.value
        chat_session.last_message_at = datetime.utcnow()
        self.db.commit()
        
        # Generate provider presentation message
        presentation = self._generate_provider_presentation(
            providers, 
            intent.language_detected.value
        )
        
        return ChatResponse(
            session_id=chat_session.session_id,
            current_step=ChatStep.PROVIDERS_SHOWN,
            agent_message=presentation,
            providers=providers,
            next_action="Select a provider by number (1, 2, 3) or type 'cancel'"
        )
    
    def _handle_provider_selection(
        self, 
        chat_session: ChatSession, 
        user: User, 
        message: str
    ) -> ChatResponse:
        """Handle user selecting a provider"""
        
        message_lower = message.lower().strip()
        
        # Check for cancellation
        if message_lower in ['cancel', 'no', 'nahi']:
            chat_session.is_active = False
            self.db.commit()
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.COMPLETED,
                agent_message="Booking cancelled. Start a new search anytime!",
                next_action="Start new conversation"
            )
        
        # Try to extract number
        try:
            # Handle various formats: "1", "provider 1", "pehla", etc.
            selection = None
            
            if message_lower in ['1', 'first', 'pehla', 'one']:
                selection = 0
            elif message_lower in ['2', 'second', 'dusra', 'two']:
                selection = 1
            elif message_lower in ['3', 'third', 'teesra', 'three']:
                selection = 2
            else:
                # Try direct number parsing
                selection = int(message_lower) - 1
            
            providers = chat_session.selected_providers
            
            if selection < 0 or selection >= len(providers):
                raise ValueError("Invalid selection")
            
            selected_provider = providers[selection]
            
            # Store selection
            chat_session.context_data = {
                'selected_provider_id': selected_provider['provider_id'],
                'selected_provider_name': selected_provider['name']
            }
            chat_session.current_step = ChatStep.PROVIDER_SELECTED.value
            chat_session.last_message_at = datetime.utcnow()
            self.db.commit()
            
            # Generate next step message (HTL reservation)
            next_message = f"""
Great! You've selected {selected_provider['name']}.

I'll reserve a time slot for you for 5 minutes.
Please confirm within this time to complete your booking.

Type 'confirm' to proceed with the booking.
            """.strip()
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.PROVIDER_SELECTED,
                agent_message=next_message,
                next_action="Type 'confirm' to reserve slot or 'back' to choose different provider"
            )
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Invalid provider selection: {message}")
            
            return ChatResponse(
                session_id=chat_session.session_id,
                current_step=ChatStep.PROVIDERS_SHOWN,
                agent_message="Please select a valid provider number (1, 2, or 3)",
                providers=[ProviderOption(**p) for p in chat_session.selected_providers],
                next_action="Enter provider number"
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
    
    def _generate_provider_presentation(
        self, 
        providers: List[ProviderOption], 
        language: str
    ) -> str:
        """Generate provider list presentation"""
        
        provider_list = "\n".join([
            f"{i+1}. {p.name} - {p.distance_km} km away - {p.rating}⭐ ({p.total_reviews} reviews)"
            for i, p in enumerate(providers)
        ])
        
        prompt = f"""
Generate a message in {language} presenting these providers:

{provider_list}

Tell user to select by number.
Keep it friendly and concise.
        """
        
        response = self.gemini.conversation_model.generate_content(prompt)
        return response.text.strip()
    
    def get_chat_history(self, session_id: uuid.UUID, user: User) -> Optional[ChatSession]:
        """Get chat session history"""
        
        chat = self.db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user.id
        ).first()
        
        return chat
    
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
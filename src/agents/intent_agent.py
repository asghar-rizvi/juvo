from typing import Dict, Any, Optional
from datetime import date, datetime, timedelta
import uuid

from src.models import ServiceIntent, Language
from src.utils.gemini_client import get_gemini_client
from src.utils.logger import AgentLogger
from src.database.connection import get_db
from src.tools import DatabaseTools


class IntentAgent:
    """
    Agent responsible for understanding user intent
    Supports Urdu, Roman Urdu, and English
    """
    
    def __init__(self):
        self.name = "IntentAgent"
        self.logger = AgentLogger(self.name)
        self.gemini = get_gemini_client()
    
    async def process_input(
        self,
        user_input: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user input and extract service intent
        
        Args:
            user_input: User's message
            session_id: Session identifier
        
        Returns:
            Dictionary with intent and metadata
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        self.logger.log_workflow_step(
            "input_processing",
            "started",
            {"input_length": len(user_input), "session_id": session_id}
        )
        
        try:
            # Step 1: Extract intent using Gemini
            self.logger.log_tool_call(
                "gemini_extract_intent",
                {"user_input": user_input[:100]},
                success=True
            )
            
            intent_data = self.gemini.extract_service_intent(user_input)
            
            # Step 2: Parse and validate with Pydantic
            try:
                # Parse date
                preferred_date = datetime.strptime(
                    intent_data['preferred_date'],
                    '%Y-%m-%d'
                ).date()
                
                # Map language code
                lang_map = {
                    'ur': Language.URDU,
                    'roman_ur': Language.ROMAN_URDU,
                    'en': Language.ENGLISH
                }
                language = lang_map.get(
                    intent_data['language_detected'],
                    Language.ENGLISH
                )
                
                # Create validated intent object
                intent = ServiceIntent(
                    service_type=intent_data['service_type'],
                    location=intent_data['location'],
                    preferred_date=preferred_date,
                    preferred_time=intent_data.get('preferred_time'),
                    language_detected=language,
                    original_input=user_input
                )
                
                self.logger.log_workflow_step(
                    "intent_validation",
                    "success",
                    {
                        "service": intent.service_type,
                        "location": intent.location,
                        "language": intent.language_detected.value
                    }
                )
                
            except Exception as e:
                self.logger.log_error(
                    "intent_validation_error",
                    str(e),
                    {"raw_intent": intent_data}
                )
                raise
            
            # Step 3: Verify service category exists in database
            with get_db() as db:
                tools = DatabaseTools(db)
                category = tools.find_service_category(intent.service_type)
                
                if category:
                    self.logger.log_decision(
                        {"service_category_id": category.id},
                        f"Matched service type '{intent.service_type}' to category '{category.name_en}'",
                        confidence=0.9
                    )
                else:
                    self.logger.log_decision(
                        {"service_category_id": None},
                        f"No exact match for '{intent.service_type}', will use fuzzy matching",
                        confidence=0.5
                    )
            
            # Step 4: Log to conversation log
            with get_db() as db:
                tools = DatabaseTools(db)
                tools.log_conversation(
                    session_id=session_id,
                    user_input=user_input,
                    agent_name=self.name,
                    extracted_intent=intent.model_dump(mode='json'),
                    reasoning="Extracted service intent from natural language input"
                )
            
            result = {
                'session_id': session_id,
                'intent': intent,
                'raw_intent': intent_data,
                'status': 'success'
            }
            
            self.logger.log_workflow_step(
                "input_processing",
                "completed",
                {"service": intent.service_type}
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error(
                "intent_processing_error",
                str(e),
                {"user_input": user_input, "session_id": session_id}
            )
            raise
    
    def process_input_sync(
        self,
        user_input: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous version of process_input"""
        import asyncio
        return asyncio.run(self.process_input(user_input, session_id))
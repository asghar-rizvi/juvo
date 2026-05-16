"""
Gemini API client with function calling support
Handles intent extraction and text generation with multi-lingual support
"""
import google.generativeai as genai
from google.generativeai.types import content_types
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json
from datetime import datetime, date, timedelta

from config import settings
from src.utils.logger import get_logger

from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)





logger = get_logger(__name__)


class GeminiClient:
    """
    Wrapper for Google Gemini API with function calling
    Supports multi-lingual intent extraction
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Gemini API key (default: from settings)
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        
        # Initialize models
        self.intent_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={
                'temperature': 0.3,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 2048,
            }
        )
        
        self.conversation_model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 1024,
            }
        )
        
        logger.info("Gemini client initialized")
    
    def extract_service_intent(
        self,
        user_input: str,
        current_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Extract structured service intent from natural language
        Supports Urdu, Roman Urdu, and English
        
        Args:
            user_input: User's message
            current_date: Current date for relative date parsing
        
        Returns:
            Extracted intent as dictionary
        """
        if current_date is None:
            current_date = date.today()
        
        prompt = f"""
You are an expert at understanding service requests in Pakistani context.
Analyze this message and extract service request details in JSON format.

Current date: {current_date.strftime('%Y-%m-%d')} ({current_date.strftime('%A')})

User message: "{user_input}"

Instructions:
1. Detect language (ur=Urdu script, roman_ur=Roman Urdu, en=English)
2. Extract service type (e.g., AC Technician, Plumber, Electrician, Tutor, etc.)
3. Extract location (area/sector in Pakistan, e.g., G-13, F-7, DHA, etc.)
4. Parse date references:
   - "kal" / "tomorrow" → {(current_date + timedelta(days=1)).strftime('%Y-%m-%d')}
   - "aaj" / "today" → {current_date.strftime('%Y-%m-%d')}
   - "parson" / "day after tomorrow" → {(current_date + timedelta(days=2)).strftime('%Y-%m-%d')}
5. Extract time preference:
   - "subah" / "morning" → morning
   - "dopahar" / "afternoon" → afternoon
   - "sham" / "evening" → evening
   - Specific times (e.g., "10 baje", "2 PM")
6. Determine urgency from context (low, medium, high, emergency)
7. Capture any special requirements

Return ONLY a JSON object with this structure:
{{
    "service_type": "extracted service type",
    "location": "extracted location",
    "preferred_date": "YYYY-MM-DD",
    "preferred_time": "extracted time or null",
    "language_detected": "ur or roman_ur or en",
    "urgency": "low or medium or high or emergency",
    "additional_details": "any special requirements or null"
}}

JSON:
"""
        
        try:
            response = self.intent_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.2,
                    'response_mime_type': 'application/json'
                }
            )
            
            # Parse JSON response
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()
            
            intent_data = json.loads(text)
            
            logger.info(f"Intent extracted: {intent_data.get('service_type')} in {intent_data.get('location')}")
            logger.debug(f"Full intent: {json.dumps(intent_data, ensure_ascii=False)}")
            
            return intent_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            logger.debug(f"Raw response: {response.text}")
            # Fallback to text parsing
            return self._parse_intent_from_text(response.text, current_date)
            
        except Exception as e:
            logger.error(f"Intent extraction failed: {str(e)}")
            raise
    
    def _parse_intent_from_text(self, text: str, current_date: date) -> Dict[str, Any]:
        """Fallback text parsing if JSON extraction fails"""
        # Basic heuristic parsing
        service_keywords = {
            'AC': 'AC Technician',
            'plumber': 'Plumber',
            'electrician': 'Electrician',
            'tutor': 'Tutor',
            'beautician': 'Beautician',
            'carpenter': 'Carpenter'
        }
        
        detected_service = 'General Service'
        for keyword, service in service_keywords.items():
            if keyword.lower() in text.lower():
                detected_service = service
                break
        
        # Try to detect location (sector patterns)
        import re
        location_match = re.search(r'(G-\d+|F-\d+|I-\d+|E-\d+|DHA)', text, re.IGNORECASE)
        location = location_match.group(0) if location_match else 'Unknown'
        
        return {
            "service_type": detected_service,
            "location": location,
            "preferred_date": current_date.strftime('%Y-%m-%d'),
            "preferred_time": "morning",
            "language_detected": "en",
            "urgency": "medium",
            "additional_details": text
        }
    
    def generate_user_message(
        self,
        template: str,
        language: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate user-facing message in specified language
        
        Args:
            template: Message template/intent
            language: Target language (ur, roman_ur, en)
            context: Context data for message
        
        Returns:
            Generated message
        """
        language_names = {
            'ur': 'Urdu (اردو)',
            'roman_ur': 'Roman Urdu',
            'en': 'English'
        }
        
        prompt = f"""
Generate a friendly, professional message in {language_names.get(language, 'English')}.

Message purpose: {template}

Context:
{json.dumps(context, indent=2, ensure_ascii=False)}

Requirements:
- Use natural, conversational tone
- Be polite and helpful
- Include relevant details from context
- Keep message concise and clear
- For Urdu/Roman Urdu: use commonly understood words

Generate the message:
"""
        
        try:
            response = self.conversation_model.generate_content(prompt)
            message = response.text.strip()
            
            logger.debug(f"Generated message in {language}: {message[:100]}...")
            return message
            
        except Exception as e:
            logger.error(f"Message generation failed: {str(e)}")
            return "An error occurred. Please try again."
    
    def rank_providers_with_reasoning(
        self,
        providers: List[Dict[str, Any]],
        user_intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rank providers using AI with detailed reasoning
        
        Args:
            providers: List of provider data
            user_intent: User's service request intent
        
        Returns:
            Ranked providers with reasoning
        """
        prompt = f"""
You are an expert at matching service providers to customer needs in Pakistan.

Customer Request:
- Service: {user_intent.get('service_type')}
- Location: {user_intent.get('location')}
- Date: {user_intent.get('preferred_date')}
- Time: {user_intent.get('preferred_time', 'Not specified')}
- Urgency: {user_intent.get('urgency', 'medium')}

Available Providers:
{json.dumps(providers, indent=2, ensure_ascii=False, cls=DecimalEncoder)}

Ranking Criteria (in order of importance):
1. Distance (closer is better)
2. Rating (higher is better)
3. Availability (more slots = better)
4. Verification status (verified providers preferred)
5. Experience (more years = better)

Task:
1. Rank these providers from best to worst match
2. Provide clear reasoning for each ranking decision
3. Explain tradeoffs (e.g., "Provider A is closer but Provider B has higher rating")
4. Give a confidence score (0-100) for the top recommendation

Return ONLY a JSON object:
{{
    "ranked_provider_ids": [id1, id2, ...],
    "top_recommendation_id": id,
    "confidence_score": 85,
    "reasoning": "Detailed explanation",
    "individual_scores": {{}}
}}

JSON:
"""
        
        try:
            response = self.conversation_model.generate_content(
                prompt,
                generation_config={'response_mime_type': 'application/json'}
            )
            
            # Extract JSON from response
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()
            
            ranking_data = json.loads(text)
            
            logger.info(f"Ranked providers - Top: ID {ranking_data['top_recommendation_id']} (confidence: {ranking_data['confidence_score']}%)")
            logger.debug(f"Ranking reasoning: {ranking_data['reasoning']}")
            
            return ranking_data
            
        except Exception as e:
            logger.error(f"Provider ranking failed: {str(e)}")
            # Fallback: Simple distance-based ranking
            sorted_providers = sorted(
                providers,
                key=lambda p: (p.get('distance_km', 999), -p.get('rating', 0))
            )
            return {
                "ranked_provider_ids": [p['provider_id'] for p in sorted_providers],
                "top_recommendation_id": sorted_providers[0]['provider_id'] if sorted_providers else None,
                "confidence_score": 60,
                "reasoning": "Fallback ranking based on distance and rating",
                "individual_scores": {}
            }
    
    def generate_booking_confirmation_message(
        self,
        booking_data: Dict[str, Any],
        language: str
    ) -> str:
        """
        Generate booking confirmation message
        
        Args:
            booking_data: Booking details
            language: Target language
        
        Returns:
            Confirmation message
        """
        return self.generate_user_message(
            template="booking_confirmation",
            language=language,
            context={
                "booking_reference": booking_data.get('booking_reference'),
                "provider_name": booking_data.get('provider_name'),
                "service_type": booking_data.get('service_type'),
                "scheduled_date": booking_data.get('scheduled_date'),
                "scheduled_time": booking_data.get('scheduled_time'),
                "provider_phone": booking_data.get('provider_phone'),
                "estimated_price": booking_data.get('estimated_price')
            }
        )

_gemini_client: Optional[GeminiClient] = None

def get_gemini_client() -> GeminiClient:
    """Get or create Gemini client instance"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
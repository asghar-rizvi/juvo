"""
Gemini API client with function calling support
Handles intent extraction and text generation with multi-lingual support
"""
import google.generativeai as genai
from typing import Optional, List, Dict, Any
import json
from datetime import datetime, date, timedelta
from decimal import Decimal

from config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


class GeminiClient:
    """
    Wrapper for Google Gemini API with function calling
    Supports multi-lingual intent extraction
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        
        self.intent_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={
                'temperature': 0.2,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 1024,
            }
        )

        self.conversation_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
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
        Extract structured service intent from natural language.
        Supports Urdu, Roman Urdu, and English.
        Always returns a valid dict — never raises.
        """
        if current_date is None:
            current_date = date.today()

        tomorrow = (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
        day_after = (current_date + timedelta(days=2)).strftime('%Y-%m-%d')
        today_str = current_date.strftime('%Y-%m-%d')

        prompt = f"""
You are an expert at understanding service requests in Pakistani context.
Analyze this message and extract service request details.

Current date: {today_str} ({current_date.strftime('%A')})

User message: "{user_input}"

Instructions:
1. Detect language (ur=Urdu script, roman_ur=Roman Urdu, en=English)
2. Extract service type (e.g., AC Technician, Plumber, Electrician, Tutor, etc.)
3. Extract location (area/sector in Pakistan, e.g., G-13, F-7, DHA, Karachi, Lahore)
4. Parse date references:
   - "kal" / "tomorrow" → {tomorrow}
   - "aaj" / "today" → {today_str}
   - "parson" / "day after tomorrow" → {day_after}
   - If no date mentioned → use {tomorrow}
5. Extract time preference (morning/afternoon/evening or specific time). Default: morning
6. Determine urgency (low, medium, high, emergency). Default: medium
7. Capture any special requirements

You MUST return ONLY a valid JSON object — no explanation, no markdown, no code fences.

{{
    "service_type": "extracted service type in English",
    "location": "extracted location",
    "preferred_date": "YYYY-MM-DD",
    "preferred_time": "morning or afternoon or evening or null",
    "language_detected": "ur or roman_ur or en",
    "urgency": "low or medium or high or emergency",
    "additional_details": "any special requirements or null"
}}
"""

        try:
            response = self.intent_model.generate_content(prompt)
            text = response.text.strip()

            # Strip markdown fences if model ignored instructions
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()

            intent_data = json.loads(text)

            # Ensure all required keys exist with sane defaults
            intent_data.setdefault('service_type', 'General Service')
            intent_data.setdefault('location', 'Unknown')
            intent_data.setdefault('preferred_date', today_str)
            intent_data.setdefault('preferred_time', 'morning')
            intent_data.setdefault('language_detected', 'en')
            intent_data.setdefault('urgency', 'medium')
            intent_data.setdefault('additional_details', None)

            # Validate date format — fall back to today if malformed
            try:
                datetime.strptime(intent_data['preferred_date'], '%Y-%m-%d')
            except (ValueError, TypeError):
                logger.warning(f"Bad date from Gemini: {intent_data.get('preferred_date')!r}, defaulting to today")
                intent_data['preferred_date'] = today_str

            logger.info(
                f"Intent extracted: {intent_data.get('service_type')} "
                f"in {intent_data.get('location')}"
            )
            return intent_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e} — falling back to heuristic parser")
            try:
                return self._parse_intent_from_text(response.text, current_date)
            except Exception:
                pass
            return self._default_intent(current_date)

        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            return self._default_intent(current_date)

    def _default_intent(self, current_date: date) -> Dict[str, Any]:
        """Return a safe default intent when all parsing fails."""
        return {
            "service_type": "General Service",
            "location": "Unknown",
            "preferred_date": current_date.strftime('%Y-%m-%d'),
            "preferred_time": "morning",
            "language_detected": "en",
            "urgency": "medium",
            "additional_details": None
        }

    def _parse_intent_from_text(self, text: str, current_date: date) -> Dict[str, Any]:
        """Fallback heuristic parser when JSON extraction fails."""
        import re

        service_keywords = {
            'ac': 'AC Technician',
            'plumber': 'Plumber',
            'electrician': 'Electrician',
            'tutor': 'Tutor',
            'beautician': 'Beautician',
            'carpenter': 'Carpenter',
            'painter': 'Painter',
            'cleaner': 'Cleaner',
        }

        detected_service = 'General Service'
        text_lower = text.lower()
        for keyword, service in service_keywords.items():
            if keyword in text_lower:
                detected_service = service
                break

        location_match = re.search(
            r'(G-\d+|F-\d+|I-\d+|E-\d+|H-\d+|DHA|Gulberg|Defence|Clifton|Johar|Nazimabad)',
            text, re.IGNORECASE
        )
        location = location_match.group(0) if location_match else 'Unknown'

        return {
            "service_type": detected_service,
            "location": location,
            "preferred_date": current_date.strftime('%Y-%m-%d'),
            "preferred_time": "morning",
            "language_detected": "en",
            "urgency": "medium",
            "additional_details": None
        }

    def generate_user_message(
        self,
        template: str,
        language: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate a user-facing message in the specified language."""
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

Generate the message (plain text only, no markdown):
"""

        try:
            response = self.conversation_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Message generation failed: {e}")
            return "Your booking has been confirmed. Thank you!"

    def rank_providers_with_reasoning(
        self,
        providers: List[Dict[str, Any]],
        user_intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rank providers using AI with detailed reasoning.
        Always returns a valid ranking dict — falls back to distance sort.
        """
        # Always have a distance-based fallback ready
        def distance_fallback() -> Dict[str, Any]:
            sorted_p = sorted(
                providers,
                key=lambda p: (p.get('distance_km', 999), -p.get('rating', 0))
            )
            return {
                "ranked_provider_ids": [p['provider_id'] for p in sorted_p],
                "top_recommendation_id": sorted_p[0]['provider_id'] if sorted_p else None,
                "confidence_score": 60,
                "reasoning": "Ranked by distance and rating (fallback)",
                "individual_scores": {}
            }

        if not providers:
            return distance_fallback()

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

Ranking Criteria (most to least important):
1. Distance (closer = better)
2. Rating (higher = better)
3. Available slots (more = better)
4. Verified status (verified preferred)
5. Years of experience

Return ONLY valid JSON — no markdown, no explanation:
{{
    "ranked_provider_ids": [id1, id2, ...],
    "top_recommendation_id": id,
    "confidence_score": 85,
    "reasoning": "Brief explanation",
    "individual_scores": {{}}
}}
"""

        try:
            response = self.conversation_model.generate_content(prompt)
            text = response.text.strip()

            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()

            ranking_data = json.loads(text)

            # Validate all returned IDs actually exist
            valid_ids = {p['provider_id'] for p in providers}
            ranking_data['ranked_provider_ids'] = [
                pid for pid in ranking_data.get('ranked_provider_ids', [])
                if pid in valid_ids
            ]

            # If top recommendation was filtered out, pick first valid
            if ranking_data.get('top_recommendation_id') not in valid_ids:
                ranking_data['top_recommendation_id'] = (
                    ranking_data['ranked_provider_ids'][0]
                    if ranking_data['ranked_provider_ids']
                    else None
                )

            # If Gemini dropped providers, append remaining at the end
            returned_ids = set(ranking_data['ranked_provider_ids'])
            for p in providers:
                if p['provider_id'] not in returned_ids:
                    ranking_data['ranked_provider_ids'].append(p['provider_id'])

            logger.info(
                f"Ranked providers — top: {ranking_data['top_recommendation_id']} "
                f"(confidence: {ranking_data.get('confidence_score')}%)"
            )
            return ranking_data

        except Exception as e:
            logger.error(f"Provider ranking failed: {e} — using distance fallback")
            return distance_fallback()

    def generate_booking_confirmation_message(
        self,
        booking_data: Dict[str, Any],
        language: str
    ) -> str:
        """Generate booking confirmation message."""
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
                "estimated_price": booking_data.get('estimated_price'),
            }
        )


_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get or create singleton Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Optional, Tuple
from datetime import date, datetime, time as time_type
from geoalchemy2.functions import ST_Distance, ST_MakePoint, ST_SetSRID, ST_DWithin
from decimal import Decimal
import logging

from src.database.models import (
    ServiceCategory, Provider, TimeSlot, Booking, 
    ConversationLog, BookingStatus
)
from src.models import (
    NearbyProviderQuery, NearbyProviderResult, ProviderMatch,
    AvailableSlot, GeoLocation
)

logger = logging.getLogger(__name__)


class DatabaseTools:
    """
    Database interaction layer for AI agents
    All methods are designed to be called via Gemini function calling
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    # ============================================
    # Provider Discovery Tools
    # ============================================
    
    def find_nearby_providers(
        self,
        service_category: str,
        latitude: float,
        longitude: float,
        max_distance_km: float = 10.0,
        min_rating: Optional[float] = None,
        limit: int = 5
    ) -> List[NearbyProviderResult]:
        """
        Find service providers near a location using PostGIS
        
        Args:
            service_category: Service type (e.g., "AC Technician")
            latitude: Latitude of search center
            longitude: Longitude of search center
            max_distance_km: Maximum search radius in kilometers
            min_rating: Minimum provider rating filter
            limit: Maximum number of results
            
        Returns:
            List of nearby providers with distance and availability
        """
        try:
            # Create point for search location
            search_point = func.ST_SetSRID(
                func.ST_MakePoint(longitude, latitude), 
                4326
            )
            
            # Build query
            query = self.db.query(
                Provider.id.label('provider_id'),
                Provider.name.label('provider_name'),
                Provider.phone,
                Provider.rating,
                # Calculate distance in kilometers
                func.ST_Distance(
                    Provider.location.cast(Geography(srid=4326)),
                    search_point.cast(Geography(srid=4326))
                ) / 1000.0
            ).label('distance_km'),
                # Count available slots
                func.count(TimeSlot.id).label('available_slots_count')
            ).join(
                ServiceCategory, 
                Provider.service_category_id == ServiceCategory.id
            ).outerjoin(
                TimeSlot,
                (Provider.id == TimeSlot.provider_id) &
                (TimeSlot.is_booked == False) &
                (TimeSlot.slot_date >= date.today())
            ).filter(
                ServiceCategory.name_en.ilike(f'%{service_category}%'),
                Provider.is_available == True,
                func.ST_DWithin(
                    Provider.location.cast(Geography(srid=4326)),
                    search_point.cast(Geography(srid=4326)),
                    max_distance_km * 1000  # Convert to meters
                )
            )
            
            # Add rating filter if specified
            if min_rating is not None:
                query = query.filter(Provider.rating >= min_rating)
            
            # Group and order
            query = query.group_by(
                Provider.id, 
                Provider.name, 
                Provider.phone, 
                Provider.rating,
                Provider.location
            ).order_by(
                func.ST_Distance(
                    Provider.location.cast(Geography(srid=4326)),
                    search_point.cast(Geography(srid=4326))
                )
            ).limit(limit)
            
            results = query.all()
            
            logger.info(f"Found {len(results)} providers near ({latitude}, {longitude})")
            
            return [
                NearbyProviderResult(
                    provider_id=r.provider_id,
                    provider_name=r.provider_name,
                    phone=r.phone,
                    rating=Decimal(str(r.rating)),
                    distance_km=round(r.distance_km, 2),
                    available_slots_count=r.available_slots_count or 0
                )
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Error finding nearby providers: {str(e)}")
            raise
    
    def get_provider_details(self, provider_id: int) -> Optional[ProviderMatch]:
        """
        Get detailed information about a specific provider
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Provider details or None if not found
        """
        try:
            provider = self.db.query(Provider).filter(
                Provider.id == provider_id
            ).first()
            
            if not provider:
                return None
            
            # Count available slots
            available_slots = self.db.query(func.count(TimeSlot.id)).filter(
                TimeSlot.provider_id == provider_id,
                TimeSlot.is_booked == False,
                TimeSlot.slot_date >= date.today()
            ).scalar() or 0
            
            # Extract coordinates
            location_wkt = self.db.scalar(
                func.ST_AsText(provider.location)
            )
            coords = self._parse_point_wkt(location_wkt)
            
            return ProviderMatch(
                provider_id=provider.id,
                name=provider.name,
                phone=provider.phone,
                service_category=provider.service_category.name_en,
                distance_km=0.0,  # Not applicable for direct lookup
                rating=provider.rating,
                total_reviews=provider.total_reviews,
                years_experience=provider.years_experience,
                price_range=provider.price_range,
                available_slots_count=available_slots,
                is_verified=provider.is_verified,
                location=GeoLocation(
                    latitude=coords[1],
                    longitude=coords[0]
                ) if coords else None
            )
            
        except Exception as e:
            logger.error(f"Error getting provider details: {str(e)}")
            raise
    
    # ============================================
    # Time Slot Tools
    # ============================================
    
    def get_available_slots(
        self,
        provider_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[AvailableSlot]:
        """
        Get available time slots for a provider
        
        Args:
            provider_id: Provider ID
            start_date: Start date filter (default: today)
            end_date: End date filter (default: 30 days from start)
            limit: Maximum slots to return
            
        Returns:
            List of available time slots
        """
        try:
            if start_date is None:
                start_date = date.today()
            
            if end_date is None:
                from datetime import timedelta
                end_date = start_date + timedelta(days=30)
            
            slots = self.db.query(TimeSlot).filter(
                TimeSlot.provider_id == provider_id,
                TimeSlot.is_booked == False,
                TimeSlot.slot_date >= start_date,
                TimeSlot.slot_date <= end_date
            ).order_by(
                TimeSlot.slot_date,
                TimeSlot.slot_time
            ).limit(limit).all()
            
            return [
                AvailableSlot(
                    slot_id=slot.id,
                    slot_date=slot.slot_date,
                    slot_time=slot.slot_time,
                    duration_minutes=slot.duration_minutes
                )
                for slot in slots
            ]
            
        except Exception as e:
            logger.error(f"Error getting available slots: {str(e)}")
            raise
    
    def check_slot_availability(self, slot_id: int) -> bool:
        """
        Check if a specific time slot is available
        
        Args:
            slot_id: Time slot ID
            
        Returns:
            True if available, False otherwise
        """
        try:
            slot = self.db.query(TimeSlot).filter(
                TimeSlot.id == slot_id
            ).first()
            
            return slot is not None and not slot.is_booked
            
        except Exception as e:
            logger.error(f"Error checking slot availability: {str(e)}")
            return False
    
    # ============================================
    # Service Category Tools
    # ============================================
    
    def find_service_category(self, search_term: str) -> Optional[ServiceCategory]:
        """
        Find service category by name or keywords
        Supports fuzzy matching for English/Urdu/Roman Urdu
        
        Args:
            search_term: Service name or keyword
            
        Returns:
            Matching service category or None
        """
        try:
            # Try exact match first
            category = self.db.query(ServiceCategory).filter(
                (ServiceCategory.name_en.ilike(f'%{search_term}%')) |
                (ServiceCategory.name_ur.contains(search_term)) |
                (ServiceCategory.name_roman_ur.ilike(f'%{search_term}%'))
            ).first()
            
            # Try keyword match if no exact match
            if not category:
                category = self.db.query(ServiceCategory).filter(
                    ServiceCategory.keywords.contains([search_term])
                ).first()
            
            return category
            
        except Exception as e:
            logger.error(f"Error finding service category: {str(e)}")
            return None
    
    def list_all_service_categories(self) -> List[dict]:
        """
        Get all available service categories
        
        Returns:
            List of service categories with names in all languages
        """
        try:
            categories = self.db.query(ServiceCategory).filter(
                ServiceCategory.is_active == True
            ).all()
            
            return [
                {
                    "id": cat.id,
                    "name_en": cat.name_en,
                    "name_ur": cat.name_ur,
                    "name_roman_ur": cat.name_roman_ur,
                    "keywords": cat.keywords
                }
                for cat in categories
            ]
            
        except Exception as e:
            logger.error(f"Error listing service categories: {str(e)}")
            return []
    
    # ============================================
    # Booking Tools
    # ============================================
    
    def create_booking_record(
        self,
        session_id: str,
        user_phone: str,
        provider_id: int,
        service_category_id: int,
        time_slot_id: int,
        user_name: Optional[str] = None,
        location_coords: Optional[Tuple[float, float]] = None,
        address_text: Optional[str] = None,
        special_instructions: Optional[str] = None
    ) -> Optional[Booking]:
        """
        Create a new booking record with transaction safety
        Automatically marks time slot as booked
        
        Args:
            session_id: Conversation session ID
            user_phone: User's phone number
            provider_id: Selected provider ID
            service_category_id: Service category ID
            time_slot_id: Selected time slot ID
            user_name: User's name (optional)
            location_coords: (latitude, longitude) tuple (optional)
            address_text: Address text (optional)
            special_instructions: Special notes (optional)
            
        Returns:
            Created booking object or None if failed
        """
        try:
            # Check slot availability with row lock
            slot = self.db.query(TimeSlot).filter(
                TimeSlot.id == time_slot_id
            ).with_for_update().first()
            
            if not slot or slot.is_booked:
                logger.warning(f"Slot {time_slot_id} not available")
                return None
            
            # Create booking
            booking = Booking(
                session_id=session_id,
                user_phone=user_phone,
                user_name=user_name,
                provider_id=provider_id,
                service_category_id=service_category_id,
                time_slot_id=time_slot_id,
                address_requested=address_text,
                special_instructions=special_instructions,
                status=BookingStatus.CONFIRMED,
                confirmed_at=datetime.utcnow()
            )
            
            # Set location if provided
            if location_coords:
                lat, lon = location_coords
                booking.location_requested = f'SRID=4326;POINT({lon} {lat})'
            
            # Mark slot as booked
            slot.is_booked = True
            
            self.db.add(booking)
            self.db.flush()  # Get booking ID without committing
            
            # Generate booking reference
            booking.booking_reference = f"BK{datetime.now().strftime('%Y%m%d')}-{str(booking.id).zfill(6)}"
            
            self.db.commit()
            self.db.refresh(booking)
            
            logger.info(f"Created booking {booking.booking_reference}")
            return booking
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating booking: {str(e)}")
            return None
    
    def get_booking_details(self, booking_id: int) -> Optional[Booking]:
        """Get booking details by ID"""
        try:
            return self.db.query(Booking).filter(
                Booking.id == booking_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting booking details: {str(e)}")
            return None
    
    # ============================================
    # Conversation Logging
    # ============================================
    
    def log_conversation(
        self,
        session_id: str,
        user_input: Optional[str] = None,
        agent_name: Optional[str] = None,
        agent_response: Optional[str] = None,
        extracted_intent: Optional[dict] = None,
        tool_calls: Optional[dict] = None,
        reasoning: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> ConversationLog:
        """
        Log conversation interaction for audit trail
        
        Args:
            session_id: Session identifier
            user_input: User's message
            agent_name: Name of agent handling request
            agent_response: Agent's response
            extracted_intent: Parsed intent data
            tool_calls: Tools/functions called
            reasoning: Agent's reasoning
            metadata: Additional metadata
            
        Returns:
            Created log entry
        """
        try:
            log_entry = ConversationLog(
                session_id=session_id,
                user_input=user_input,
                agent_name=agent_name,
                agent_response=agent_response,
                extracted_intent=extracted_intent,
                tool_calls=tool_calls,
                reasoning=reasoning,
                metadata=metadata
            )
            
            self.db.add(log_entry)
            self.db.commit()
            self.db.refresh(log_entry)
            
            return log_entry
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error logging conversation: {str(e)}")
            raise
    
    # ============================================
    # Helper Methods
    # ============================================
    
    @staticmethod
    def _parse_point_wkt(wkt: str) -> Optional[Tuple[float, float]]:
        """
        Parse PostGIS POINT WKT to (longitude, latitude)
        Example: "POINT(73.0479 33.6844)" -> (73.0479, 33.6844)
        """
        try:
            import re
            match = re.search(r'POINT\(([0-9.-]+)\s+([0-9.-]+)\)', wkt)
            if match:
                return (float(match.group(1)), float(match.group(2)))
            return None
        except Exception:
            return None
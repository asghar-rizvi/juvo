"""
Provider Discovery Agent
Finds and ranks service providers based on location and requirements
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal

from src.models import ServiceIntent, ProviderMatch, GeoLocation
from src.utils.gemini_client import get_gemini_client
from src.utils.maps_client import get_maps_client
from src.utils.logger import AgentLogger
from src.database.connection import get_db
from src.tools import DatabaseTools


class ProviderDiscoveryAgent:
    """
    Agent responsible for finding and ranking service providers
    Uses PostGIS for spatial queries and Gemini for intelligent ranking
    """
    
    def __init__(self):
        self.name = "ProviderDiscoveryAgent"
        self.logger = AgentLogger(self.name)
        self.gemini = get_gemini_client()
        self.maps = get_maps_client()
    
    async def find_and_rank_providers(
        self,
        intent: ServiceIntent,
        session_id: str,
        max_distance_km: float = 15.0,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Find nearby providers and rank them intelligently
        
        Args:
            intent: User's service intent
            session_id: Session identifier
            max_distance_km: Maximum search radius
            max_results: Maximum number of results
        
        Returns:
            Ranked providers with reasoning
        """
        self.logger.log_workflow_step(
            "provider_discovery",
            "started",
            {
                "service": intent.service_type,
                "location": intent.location,
                "session_id": session_id
            }
        )
        
        try:
            # Step 1: Geocode location using Google Maps
            self.logger.log_tool_call(
                "google_maps_geocode",
                {"location": intent.location}
            )
            
            geocode_result = self.maps.geocode_location(intent.location)
            
            if not geocode_result:
                self.logger.log_error(
                    "geocoding_failed",
                    f"Could not geocode location: {intent.location}"
                )
                raise ValueError(f"Location not found: {intent.location}")
            
            # Validate it's in Pakistan
            if not self.maps.validate_pakistan_location(geocode_result):
                self.logger.log_error(
                    "location_validation_failed",
                    f"Location is not in Pakistan: {geocode_result['formatted_address']}"
                )
                raise ValueError("Service only available in Pakistan")
            
            latitude = geocode_result['latitude']
            longitude = geocode_result['longitude']
            
            self.logger.log_tool_call(
                "google_maps_geocode",
                {"location": intent.location},
                {
                    "formatted_address": geocode_result['formatted_address'],
                    "coordinates": (latitude, longitude)
                },
                success=True
            )
            
            # Step 2: Find nearby providers using PostGIS
            with get_db() as db:
                tools = DatabaseTools(db)
                
                self.logger.log_tool_call(
                    "find_nearby_providers",
                    {
                        "service": intent.service_type,
                        "location": (latitude, longitude),
                        "radius_km": max_distance_km
                    }
                )
                
                providers = tools.find_nearby_providers(
                    service_category=intent.service_type,
                    latitude=latitude,
                    longitude=longitude,
                    max_distance_km=max_distance_km,
                    limit=max_results * 2  # Get extra for ranking
                )
                
                if not providers:
                    self.logger.log_error(
                        "no_providers_found",
                        f"No providers found for {intent.service_type} near {intent.location}"
                    )
                    return {
                        'session_id': session_id,
                        'providers': [],
                        'location': geocode_result,
                        'status': 'no_providers_found',
                        'message': f"No {intent.service_type} providers found within {max_distance_km} km"
                    }
                
                self.logger.log_tool_call(
                    "find_nearby_providers",
                    {},
                    {"provider_count": len(providers)},
                    success=True
                )
                
                # Step 3: Get detailed provider information
                detailed_providers = []
                for prov in providers:
                    details = tools.get_provider_details(prov.provider_id)
                    if details:
                        # Add distance from initial query
                        details_dict = details.model_dump()
                        details_dict['distance_km'] = float(prov.distance_km)
                        detailed_providers.append(details_dict)
                
                # Step 4: Rank providers using Gemini AI
                if len(detailed_providers) > 1:
                    self.logger.log_tool_call(
                        "gemini_rank_providers",
                        {"provider_count": len(detailed_providers)}
                    )
                    
                    ranking_result = self.gemini.rank_providers_with_reasoning(
                        providers=detailed_providers,
                        user_intent=intent.model_dump(mode='json')
                    )
                    
                    # Reorder providers based on AI ranking
                    ranked_ids = ranking_result['ranked_provider_ids']
                    provider_map = {p['provider_id']: p for p in detailed_providers}
                    ranked_providers = [
                        provider_map[pid] 
                        for pid in ranked_ids 
                        if pid in provider_map
                    ][:max_results]
                    
                    self.logger.log_decision(
                        {
                            "top_provider_id": ranking_result['top_recommendation_id'],
                            "ranked_count": len(ranked_providers)
                        },
                        ranking_result['reasoning'],
                        confidence=ranking_result['confidence_score'] / 100.0
                    )
                else:
                    ranked_providers = detailed_providers[:max_results]
                    ranking_result = {
                        'reasoning': 'Only one provider available',
                        'confidence_score': 100
                    }
                
                # Convert to ProviderMatch objects
                provider_matches = [
                    ProviderMatch(**p) for p in ranked_providers
                ]
                
                # Step 5: Log to conversation
                tools.log_conversation(
                    session_id=session_id,
                    agent_name=self.name,
                    agent_response=f"Found {len(provider_matches)} providers",
                    tool_calls={
                        "geocoding": geocode_result,
                        "providers_found": len(providers),
                        "providers_ranked": len(provider_matches)
                    },
                    reasoning=ranking_result['reasoning']
                )
            
            result = {
                'session_id': session_id,
                'providers': provider_matches,
                'location': geocode_result,
                'ranking': ranking_result,
                'status': 'success'
            }
            
            self.logger.log_workflow_step(
                "provider_discovery",
                "completed",
                {"provider_count": len(provider_matches)}
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error(
                "provider_discovery_error",
                str(e),
                {"intent": intent.model_dump(mode='json')}
            )
            raise
    
    def find_and_rank_providers_sync(
        self,
        intent: ServiceIntent,
        session_id: str,
        max_distance_km: float = 15.0,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """Synchronous version"""
        import asyncio
        return asyncio.run(
            self.find_and_rank_providers(
                intent, session_id, max_distance_km, max_results
            )
        )
import googlemaps
from typing import Optional, Tuple, Dict, Any, List
from config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MapsClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        self.client = googlemaps.Client(key=self.api_key)
        
        self.default_region = 'pk'
        self.default_bounds = {
            'northeast': {'lat': 37.084107, 'lng': 77.840919},
            'southwest': {'lat': 23.634501, 'lng': 60.872972}
        }
        
        logger.info("Google Maps client initialized")
    
    def geocode_location(
        self,
        location_query: str,
        bias_region: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Geocode a location query to coordinates
        
        Args:
            location_query: Location string (e.g., "G-13, Islamabad")
            bias_region: Country code to bias results (default: 'pk')
        
        Returns:
            Geocoding result with coordinates or None
        """
        try:
            region = bias_region or self.default_region
            
            if 'pakistan' not in location_query.lower():
                enhanced_query = f"{location_query}, Pakistan"
            else:
                enhanced_query = location_query
            
            logger.debug(f"Geocoding: {enhanced_query}")
            
            results = self.client.geocode(
                enhanced_query,
                region=region,
                bounds=self.default_bounds
            )
            
            if not results:
                logger.warning(f"No geocoding results for: {location_query}")
                return None
            
            result = results[0]
            
            geocode_data = {
                'formatted_address': result['formatted_address'],
                'latitude': result['geometry']['location']['lat'],
                'longitude': result['geometry']['location']['lng'],
                'place_id': result.get('place_id'),
                'location_type': result['geometry'].get('location_type'),
                'types': result.get('types', []),
                'address_components': result.get('address_components', [])
            }
            
            logger.info(f"Geocoded '{location_query}' → {geocode_data['formatted_address']}")
            logger.debug(f"Coordinates: ({geocode_data['latitude']}, {geocode_data['longitude']})")
            
            return geocode_data
            
        except googlemaps.exceptions.ApiError as e:
            logger.error(f"Google Maps API error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Geocoding failed: {str(e)}")
            return None
    
    def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Reverse geocode coordinates to address
        
        Args:
            latitude: Latitude
            longitude: Longitude
        
        Returns:
            Address information or None
        """
        try:
            results = self.client.reverse_geocode((latitude, longitude))
            
            if not results:
                logger.warning(f"No reverse geocoding results for: ({latitude}, {longitude})")
                return None
            
            result = results[0]
            
            return {
                'formatted_address': result['formatted_address'],
                'place_id': result.get('place_id'),
                'types': result.get('types', []),
                'address_components': result.get('address_components', [])
            }
            
        except Exception as e:
            logger.error(f"Reverse geocoding failed: {str(e)}")
            return None
    
    def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        mode: str = "driving"
    ) -> Optional[Dict[str, Any]]:
        """
        Get distance and duration between multiple points
        
        Args:
            origins: List of (lat, lng) tuples
            destinations: List of (lat, lng) tuples
            mode: Travel mode (driving, walking, bicycling, transit)
        
        Returns:
            Distance matrix results
        """
        try:
            results = self.client.distance_matrix(
                origins=origins,
                destinations=destinations,
                mode=mode,
                units="metric"
            )
            
            logger.debug(f"Distance matrix: {len(origins)} origins × {len(destinations)} destinations")
            
            return results
            
        except Exception as e:
            logger.error(f"Distance matrix failed: {str(e)}")
            return None
    
    def extract_city_from_geocode(self, geocode_result: Dict[str, Any]) -> Optional[str]:
        """
        Extract city name from geocoding result
        
        Args:
            geocode_result: Result from geocode_location()
        
        Returns:
            City name or None
        """
        for component in geocode_result.get('address_components', []):
            if 'locality' in component.get('types', []):
                return component['long_name']
            elif 'administrative_area_level_2' in component.get('types', []):
                return component['long_name']
        return None
    
    def validate_pakistan_location(self, geocode_result: Dict[str, Any]) -> bool:
        """
        Validate that location is in Pakistan
        
        Args:
            geocode_result: Result from geocode_location()
        
        Returns:
            True if location is in Pakistan
        """
        for component in geocode_result.get('address_components', []):
            if 'country' in component.get('types', []):
                return component.get('short_name') == 'PK'
        return False


_maps_client: Optional[MapsClient] = None

def get_maps_client() -> MapsClient:
    """Get or create Maps client instance"""
    global _maps_client
    if _maps_client is None:
        _maps_client = MapsClient()
    return _maps_client
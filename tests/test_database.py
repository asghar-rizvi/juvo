import pytest
from datetime import date
from src.database.connection import get_db, test_connection, verify_postgis
from src.database.models import ServiceCategory, Provider, TimeSlot
from src.tools import DatabaseTools


class TestDatabaseConnection:
    """Test database connection and PostGIS"""
    
    def test_connection(self):
        """Test basic database connection"""
        assert test_connection() == True
    
    def test_postgis_extension(self):
        """Test PostGIS extension is installed"""
        assert verify_postgis() == True


class TestServiceCategories:
    """Test service category operations"""
    
    def test_list_categories(self):
        """Test listing all service categories"""
        with get_db() as db:
            tools = DatabaseTools(db)
            categories = tools.list_all_service_categories()
            assert len(categories) > 0
            assert all('name_en' in cat for cat in categories)
    
    def test_find_category(self):
        """Test finding category by search term"""
        with get_db() as db:
            tools = DatabaseTools(db)
            category = tools.find_service_category("AC Technician")
            assert category is not None
            assert category.name_en == "AC Technician"


class TestProviderDiscovery:
    """Test provider search functionality"""
    
    def test_find_nearby_providers(self):
        """Test finding providers near G-13, Islamabad"""
        with get_db() as db:
            tools = DatabaseTools(db)
            results = tools.find_nearby_providers(
                service_category="AC Technician",
                latitude=33.6844,
                longitude=73.0479,
                max_distance_km=10.0
            )
            assert len(results) > 0
            assert all(r.distance_km <= 10.0 for r in results)
    
    def test_provider_details(self):
        """Test getting provider details"""
        with get_db() as db:
            # Get first provider
            provider = db.query(Provider).first()
            assert provider is not None
            
            tools = DatabaseTools(db)
            details = tools.get_provider_details(provider.id)
            assert details is not None
            assert details.provider_id == provider.id


class TestTimeSlots:
    """Test time slot operations"""
    
    def test_get_available_slots(self):
        """Test getting available slots for a provider"""
        with get_db() as db:
            # Get first provider
            provider = db.query(Provider).first()
            assert provider is not None
            
            tools = DatabaseTools(db)
            slots = tools.get_available_slots(provider.id)
            assert len(slots) > 0
    
    def test_check_slot_availability(self):
        """Test checking if slot is available"""
        with get_db() as db:
            # Get first available slot
            slot = db.query(TimeSlot).filter(
                TimeSlot.is_booked == False
            ).first()
            assert slot is not None
            
            tools = DatabaseTools(db)
            is_available = tools.check_slot_availability(slot.id)
            assert is_available == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
import sys
from datetime import date
from sqlalchemy import text

from config import settings
from src.database.connection import get_db, test_connection, verify_postgis
from src.database.models import ServiceCategory, Provider, TimeSlot, Booking
from src.tools import DatabaseTools
from src.models import ServiceIntent, Language


def print_header(message):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {message}")
    print("="*60)


def verify_environment():
    """Verify environment configuration"""
    print_header("1. Verifying Environment Configuration")
    
    required_vars = [
        'DATABASE_URL',
        'GOOGLE_CLOUD_PROJECT',
        'GEMINI_API_KEY',
        'GOOGLE_MAPS_API_KEY'
    ]
    
    missing = []
    for var in required_vars:
        value = getattr(settings, var, None)
        if value:
            print(f"✓ {var}: {'*' * 10} (set)")
        else:
            print(f"✗ {var}: NOT SET")
            missing.append(var)
    
    if missing:
        print(f"\n⚠ Missing environment variables: {', '.join(missing)}")
        return False
    
    print("\n✓ All environment variables configured")
    return True


def verify_database_connection():
    """Verify database connectivity"""
    print_header("2. Verifying Database Connection")
    
    if not test_connection():
        print("✗ Database connection failed")
        return False
    
    print("✓ Database connection successful")
    return True


def verify_postgis_installation():
    """Verify PostGIS extension"""
    print_header("3. Verifying PostGIS Extension")
    
    if not verify_postgis():
        print("✗ PostGIS not installed or not working")
        return False
    
    print("✓ PostGIS extension verified")
    return True


def verify_database_schema():
    """Verify all tables exist"""
    print_header("4. Verifying Database Schema")
    
    expected_tables = [
        'service_categories',
        'providers',
        'time_slots',
        'bookings',
        'conversation_logs'
    ]
    
    with get_db() as db:
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """))
        
        existing_tables = [row[0] for row in result]
        
        all_exist = True
        for table in expected_tables:
            if table in existing_tables:
                print(f"✓ Table exists: {table}")
            else:
                print(f"✗ Table missing: {table}")
                all_exist = False
    
    return all_exist


def verify_seed_data():
    """Verify seed data was loaded"""
    print_header("5. Verifying Seed Data")
    
    with get_db() as db:
        # Check service categories
        cat_count = db.query(ServiceCategory).count()
        print(f"Service Categories: {cat_count}")
        
        # Check providers
        prov_count = db.query(Provider).count()
        print(f"Providers: {prov_count}")
        
        # Check time slots
        slot_count = db.query(TimeSlot).count()
        print(f"Time Slots: {slot_count}")
        
        if cat_count > 0 and prov_count > 0 and slot_count > 0:
            print("\n✓ Seed data verified")
            return True
        else:
            print("\n✗ Seed data incomplete")
            return False


def verify_pydantic_models():
    """Verify Pydantic models work correctly"""
    print_header("6. Verifying Pydantic Models")
    
    try:
        # Test ServiceIntent model
        intent = ServiceIntent(
            service_type="AC Technician",
            location="G-13, Islamabad",
            preferred_date=date.today(),
            preferred_time="morning",
            language_detected=Language.ROMAN_URDU,
            original_input="Test input"
        )
        print(f"✓ ServiceIntent model validated")
        print(f"  - Service: {intent.service_type}")
        print(f"  - Location: {intent.location}")
        print(f"  - Language: {intent.language_detected.value}")
        
        return True
        
    except Exception as e:
        print(f"✗ Pydantic model validation failed: {str(e)}")
        return False


def verify_database_tools():
    """Verify DatabaseTools functionality"""
    print_header("7. Verifying Database Tools")
    
    try:
        with get_db() as db:
            tools = DatabaseTools(db)
            
            # Test find_nearby_providers
            providers = tools.find_nearby_providers(
                service_category="AC Technician",
                latitude=33.6844,
                longitude=73.0479,
                max_distance_km=10.0,
                limit=3
            )
            print(f"✓ find_nearby_providers: Found {len(providers)} providers")
            
            if providers:
                print(f"  - Top provider: {providers[0].provider_name} ({providers[0].distance_km} km)")
            
            # Test get_available_slots
            if providers:
                slots = tools.get_available_slots(providers[0].provider_id, limit=5)
                print(f"✓ get_available_slots: Found {len(slots)} slots")
            
            # Test find_service_category
            category = tools.find_service_category("AC Technician")
            print(f"✓ find_service_category: Found '{category.name_en if category else 'None'}'")
            
            return True
            
    except Exception as e:
        print(f"✗ Database tools test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify_spatial_queries():
    """Verify PostGIS spatial queries work"""
    print_header("8. Verifying Spatial Queries")
    
    try:
        with get_db() as db:
            # Test ST_Distance calculation
            result = db.execute(text("""
                SELECT 
                    name,
                    ST_Distance(
                        location::geography,
                        ST_SetSRID(ST_MakePoint(73.0479, 33.6844), 4326)::geography
                    ) / 1000.0 as distance_km
                FROM providers
                WHERE ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(73.0479, 33.6844), 4326)::geography,
                    10000
                )
                ORDER BY distance_km
                LIMIT 3
            """))
            
            providers = result.fetchall()
            print(f"✓ Spatial query successful: Found {len(providers)} providers")
            
            for prov in providers:
                print(f"  - {prov[0]}: {round(prov[1], 2)} km")
            
            return len(providers) > 0
            
    except Exception as e:
        print(f"✗ Spatial query failed: {str(e)}")
        return False


def run_all_verifications():
    """Run all verification checks"""
    print("\n" + "="*60)
    print("  PHASE 1 VERIFICATION")
    print("  Pakistani Service Orchestrator")
    print("="*60)
    
    checks = [
        ("Environment Configuration", verify_environment),
        ("Database Connection", verify_database_connection),
        ("PostGIS Extension", verify_postgis_installation),
        ("Database Schema", verify_database_schema),
        ("Seed Data", verify_seed_data),
        ("Pydantic Models", verify_pydantic_models),
        ("Database Tools", verify_database_tools),
        ("Spatial Queries", verify_spatial_queries)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {str(e)}")
            results.append((name, False))
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 Phase 1 Complete - All systems operational!")
        return True
    else:
        print("\n⚠ Phase 1 Incomplete - Please fix failing checks")
        return False


if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
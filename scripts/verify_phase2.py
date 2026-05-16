import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from src.utils.gemini_client import get_gemini_client
from src.utils.maps_client import get_maps_client
from src.agents.intent_agent import IntentAgent
from src.agents.discovery_agent import ProviderDiscoveryAgent
from src.agents.booking_agent import BookingAgent
from src.agents.orchestrator import ServiceOrchestrator
from src.models import ServiceIntent, Language


def print_header(message):
    print("\n" + "="*60)
    print(f"  {message}")
    print("="*60)


def verify_gemini():
    """Test Gemini API connection"""
    print_header("1. Verifying Gemini API")
    try:
        client = get_gemini_client()
        result = client.extract_service_intent(
            "I need an AC technician tomorrow in G-13"
        )
        assert 'service_type' in result
        print("✓ Gemini API working")
        print(f"  Sample extraction: {result['service_type']}")
        return True
    except Exception as e:
        print(f"✗ Gemini API failed: {str(e)}")
        return False


def verify_google_maps():
    """Test Google Maps API"""
    print_header("2. Verifying Google Maps API")
    try:
        client = get_maps_client()
        result = client.geocode_location("G-13, Islamabad")
        assert result is not None
        assert 'latitude' in result
        print("✓ Google Maps API working")
        print(f"  Geocoded: {result['formatted_address']}")
        print(f"  Coordinates: ({result['latitude']}, {result['longitude']})")
        return True
    except Exception as e:
        print(f"✗ Google Maps API failed: {str(e)}")
        return False


def verify_intent_agent():
    """Test Intent Agent"""
    print_header("3. Verifying Intent Agent")
    try:
        agent = IntentAgent()
        result = agent.process_input_sync(
            "Mujhe kal G-13 mein plumber chahiye"
        )
        assert result['status'] == 'success'
        assert isinstance(result['intent'], ServiceIntent)
        print("✓ Intent Agent working")
        print(f"  Extracted: {result['intent'].service_type} in {result['intent'].location}")
        return True
    except Exception as e:
        print(f"✗ Intent Agent failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify_discovery_agent():
    """Test Provider Discovery Agent"""
    print_header("4. Verifying Provider Discovery Agent")
    try:
        agent = ProviderDiscoveryAgent()
        intent = ServiceIntent(
            service_type="AC Technician",
            location="G-13, Islamabad",
            preferred_date=date.today(),
            language_detected=Language.ENGLISH
        )
        result = agent.find_and_rank_providers_sync(intent, "test-session")
        assert result['status'] == 'success'
        assert len(result['providers']) > 0
        print("✓ Provider Discovery Agent working")
        print(f"  Found {len(result['providers'])} providers")
        print(f"  Top: {result['providers'][0].name}")
        return True
    except Exception as e:
        print(f"✗ Provider Discovery Agent failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify_orchestrator():
    """Test complete orchestration"""
    print_header("5. Verifying Service Orchestrator")
    try:
        orchestrator = ServiceOrchestrator()
        result = orchestrator.handle_service_request_sync(
            user_input="I need plumber in F-7",
            user_phone="+923001111111",
            auto_book=False
        )
        assert result['status'] in ['providers_found', 'completed_with_booking', 'no_providers_available']
        assert 'intent' in result['steps']
        print("✓ Service Orchestrator working")
        print(f"  Workflow status: {result['status']}")
        print(f"  Steps completed: {len(result['steps'])}")
        
        orchestrator.shutdown()
        return True
    except Exception as e:
        print(f"✗ Service Orchestrator failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_verifications():
    """Run all Phase 2 verifications"""
    print("\n" + "="*60)
    print("  PHASE 2 VERIFICATION")
    print("  Multi-Agent Service Orchestrator")
    print("="*60)
    
    checks = [
        ("Gemini API", verify_gemini),
        ("Google Maps API", verify_google_maps),
        ("Intent Agent", verify_intent_agent),
        ("Provider Discovery Agent", verify_discovery_agent),
        ("Service Orchestrator", verify_orchestrator)
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
        print("\n🎉 Phase 2 Complete - All agents operational!")
        return True
    else:
        print("\n⚠ Phase 2 Incomplete - Please fix failing checks")
        return False


if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
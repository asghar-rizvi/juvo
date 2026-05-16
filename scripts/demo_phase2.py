import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.orchestrator import ServiceOrchestrator
from src.utils.logger import setup_logging, get_logger
import json


def print_separator():
    print("\n" + "="*80 + "\n")


def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def demo_workflow():
    """Run interactive demo"""
    
    # Setup logging
    logger = setup_logging(log_level="INFO")
    
    print_section("🚀 PHASE 2 DEMO - Service Orchestrator")
    print("This demo shows the complete multi-agent workflow:")
    print("1. Intent Understanding (Gemini)")
    print("2. Provider Discovery (PostGIS + Google Maps)")
    print("3. AI-powered Ranking (Gemini)")
    print("4. Booking Creation")
    print("5. Follow-up Scheduling")
    
    # Initialize orchestrator
    print_separator()
    print("Initializing orchestrator and all agents...")
    orchestrator = ServiceOrchestrator()
    print("✓ All agents initialized")
    
    # Demo requests
    demo_requests = [
        {
            "input": "Mujhe kal subah G-13 mein AC technician chahiye",
            "phone": "+923001234567",
            "name": "Ahmed Khan",
            "auto_book": True,
            "description": "Roman Urdu request with auto-booking"
        },
        {
            "input": "I need a plumber tomorrow afternoon in F-7 Islamabad",
            "phone": "+923112345678",
            "name": "Sara Ali",
            "auto_book": False,
            "description": "English request, show options only"
        }
    ]
    
    for i, req in enumerate(demo_requests, 1):
        print_section(f"DEMO REQUEST #{i}: {req['description']}")
        
        print(f"User Input: \"{req['input']}\"")
        print(f"Phone: {req['phone']}")
        print(f"Auto-book: {req['auto_book']}")
        
        print_separator()
        print("🤖 Processing request...")
        
        try:
            result = orchestrator.handle_service_request_sync(
                user_input=req['input'],
                user_phone=req['phone'],
                user_name=req['name'],
                auto_book=req['auto_book']
            )
            
            print(f"\n✓ Workflow Status: {result['status']}")
            
            # Show intent
            if 'intent' in result['steps']:
                intent_data = result['steps']['intent']['data']
                print(f"\n📝 Extracted Intent:")
                print(f"   Service: {intent_data['service_type']}")
                print(f"   Location: {intent_data['location']}")
                print(f"   Date: {intent_data['preferred_date']}")
                print(f"   Time: {intent_data.get('preferred_time', 'Not specified')}")
                print(f"   Language: {intent_data['language_detected']}")
            
            # Show providers
            if 'discovery' in result['steps']:
                discovery = result['steps']['discovery']
                print(f"\n🔍 Providers Found: {discovery['provider_count']}")
                
                for idx, provider in enumerate(discovery['providers'][:3], 1):
                    print(f"\n   {idx}. {provider['name']}")
                    print(f"      Distance: {provider['distance_km']} km")
                    print(f"      Rating: {provider['rating']}/5 ({provider['total_reviews']} reviews)")
                    print(f"      Available Slots: {provider['available_slots_count']}")
                    print(f"      Phone: {provider['phone']}")
                
                print(f"\n   AI Reasoning:")
                print(f"   {discovery['ranking_reasoning']}")
            
            # Show booking
            if 'booking' in result['steps']:
                booking = result['steps']['booking']['data']
                print(f"\n✅ BOOKING CONFIRMED")
                print(f"   Reference: {booking['booking_reference']}")
                print(f"   Provider: {booking['provider_name']}")
                print(f"   Date: {booking['scheduled_date']}")
                print(f"   Time: {booking['scheduled_time']}")
                print(f"\n   Confirmation Message:")
                print(f"   {booking['confirmation_message']}")
            
            # Show follow-up
            if 'followup' in result['steps']:
                followup = result['steps']['followup']
                print(f"\n🔔 Reminder Scheduled:")
                print(f"   Status: {followup['status']}")
                print(f"   Time: {followup['reminder'].get('reminder_time', 'N/A')}")
            
            print_separator()
            
        except Exception as e:
            print(f"\n✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Shutdown
    print_section("DEMO COMPLETE")
    orchestrator.shutdown()
    print("✓ Orchestrator shutdown complete")
    print("\nCheck logs/ directory for detailed execution logs")


if __name__ == "__main__":
    demo_workflow()
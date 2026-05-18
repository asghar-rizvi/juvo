"""
Phase 4 Verification Script - Interactive Mode
Allows testing individual components with user input
"""
import requests
import json
import time
import sys
from datetime import datetime, date, timedelta

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Global state
state = {
    "user_token": None,
    "provider_token": None,
    "user_id": None,
    "provider_id": None,
    "session_id": None,
    "htl_id": None,
    "booking_id": None,
    "slot_id": None,
    "test_email_user": None,
    "test_email_provider": None,
}

results = {"passed": 0, "failed": 0, "warnings": 0}


def print_json(data, title=None):
    """Pretty print JSON"""
    if title:
        print(f"\n  {CYAN}📋 {title}:{RESET}")
    print(f"  {json.dumps(data, indent=2, default=str)[:2000]}")


def make_request(method, endpoint, token=None, data=None, params=None, expected_status=200, verbose=True):
    url = f"{API_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = getattr(requests, method.lower())(url, json=data, params=params, headers=headers, timeout=30)
        success = resp.status_code == expected_status
        
        try:
            body = resp.json()
        except:
            body = {"raw": resp.text}
        
        if verbose:
            print(f"    → Status: {resp.status_code}")
            if body and not isinstance(body, list):
                print(f"    → Response: {json.dumps(body, default=str)[:500]}")
        
        return success, resp.status_code, body
    except Exception as e:
        return False, 0, {"error": str(e)}


def record(success, msg, warning=False):
    if warning:
        print(f"  {YELLOW}⚠ {msg}{RESET}")
        results["warnings"] += 1
    elif success:
        print(f"  {GREEN}✓ {msg}{RESET}")
        results["passed"] += 1
    else:
        print(f"  {RED}✗ {msg}{RESET}")
        results["failed"] += 1
    return success


def print_header(title):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{title}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")


# ============================================
# Individual Test Functions
# ============================================

def test_server_health():
    print(f"\n{CYAN}  ── Server & Health ──{RESET}")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        record(r.status_code == 200, f"Root endpoint → {r.status_code}")
        
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        record(r.status_code == 200, f"Health check → {data.get('status')}")
        record(data.get("database") == "connected", f"Database → {data.get('database')}")
        return True
    except Exception as e:
        record(False, f"Server not reachable: {e}")
        return False


def test_register_user():
    """Register a new user"""
    print(f"\n{CYAN}  ── Register User ──{RESET}")
    
    timestamp = int(time.time())
    email = f"testuser_{timestamp}@example.com"
    phone = f"+923{str(timestamp)[-9:]}"
    
    print(f"    Email: {email}")
    print(f"    Phone: {phone}")
    
    success, code, body = make_request("POST", "/auth/register/user", data={
        "email": email,
        "phone": phone,
        "password": "TestPass123",
        "full_name": "Test User",
        "city": "Islamabad"
    }, expected_status=201)
    
    record(success, f"User registration → {code}")
    if success:
        state["user_token"] = body["tokens"]["access_token"]
        state["user_id"] = body["user"]["id"]
        state["test_email_user"] = email
        print(f"    → User ID: {state['user_id']}")
        print(f"    → Token: {state['user_token'][:50]}...")
    return success


def test_login_user():
    """Login existing user"""
    print(f"\n{CYAN}  ── Login User ──{RESET}")
    
    if not state["test_email_user"]:
        email = input("    Enter user email: ").strip()
    else:
        email = state["test_email_user"]
    
    password = input("    Enter password (default: TestPass123): ").strip() or "TestPass123"
    
    success, code, body = make_request("POST", "/auth/login/user", data={
        "email": email, "password": password
    })
    
    record(success, f"User login → {code}")
    if success:
        state["user_token"] = body["tokens"]["access_token"]
        state["user_id"] = body["user"]["id"]
        print(f"    → User ID: {state['user_id']}")
    return success


def test_register_provider():
    """Register a new provider"""
    print(f"\n{CYAN}  ── Register Provider ──{RESET}")
    
    timestamp = int(time.time())
    email = f"testprovider_{timestamp}@example.com"
    phone = f"+923{str(timestamp + 10000)[-9:]}"
    
    print(f"    Email: {email}")
    print(f"    Phone: {phone}")
    
    success, code, body = make_request("POST", "/auth/register/provider", data={
        "email": email,
        "password": "TestPass123",
        "name": "Test Provider",
        "phone": phone,
        "service_category_id": 1,
        "address_text": "G-13/1, Islamabad",
        "city": "Islamabad",
        "latitude": 33.6844,
        "longitude": 73.0479,
        "years_experience": 5,
        "price_range": "Rs. 1000-2000"
    }, expected_status=201)
    
    record(success, f"Provider registration → {code}")
    if success:
        state["provider_token"] = body["tokens"]["access_token"]
        state["provider_id"] = body["provider"]["provider_id"]
        state["test_email_provider"] = email
        print(f"    → Provider ID: {state['provider_id']}")
    return success


def test_create_time_slots():
    """Create time slots for a provider"""
    print(f"\n{CYAN}  ── Create Time Slots ──{RESET}")
    
    if not state["provider_token"]:
        print("    ❌ No provider token. Please register/login as provider first.")
        return False
    
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    print(f"    Date: {tomorrow}")
    
    success, code, body = make_request("POST", "/providers/slots", token=state["provider_token"], data={
        "slot_date": tomorrow,
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "duration_minutes": 60
    }, expected_status=201)
    
    record(success, f"Create time slots → {code}")
    if success and body.get("slots"):
        state["slot_id"] = body["slots"][0]["id"]
        print(f"    → Created {len(body['slots'])} slots")
        print(f"    → First slot ID: {state['slot_id']}")
    return success


def test_start_chat():
    """Start a chat session"""
    print(f"\n{CYAN}  ── Start Chat ──{RESET}")
    
    if not state["user_token"]:
        print("    ❌ No user token. Please login first.")
        return False
    
    initial_message = input("    Enter your message (default: 'I need an AC technician tomorrow in G-13'): ").strip()
    if not initial_message:
        initial_message = "I need an AC technician tomorrow in G-13"
    
    print(f"    Message: {initial_message}")
    
    success, code, body = make_request("POST", "/chat/start", token=state["user_token"], 
                                        data={"initial_message": initial_message},
                                        expected_status=201)
    record(success, f"Start chat → {code}")
    
    if success:
        state["session_id"] = str(body.get("session_id", ""))
        print(f"    → Session ID: {state['session_id']}")
        print(f"    → Current step: {body.get('current_step')}")
        print(f"    → Agent: {body.get('agent_message', '')[:200]}")
    return success


def test_send_message():
    """Send a message in chat"""
    print(f"\n{CYAN}  ── Send Message ──{RESET}")
    
    if not state["user_token"] or not state["session_id"]:
        print("    ❌ No session. Please start a chat first.")
        return False
    
    message = input("    Enter your message: ").strip()
    if not message:
        print("    ❌ Message cannot be empty")
        return False
    
    print(f"    Message: {message}")
    
    success, code, body = make_request("POST", "/chat/message", token=state["user_token"],
                                        data={"session_id": state["session_id"], "message": message})
    record(success, f"Send message → {code}")
    
    if success:
        print(f"    → Current step: {body.get('current_step')}")
        print(f"    → Agent response: {body.get('agent_message', '')[:300]}")
        
        # Store HTL ID if present
        context = body.get("context_data", {})
        if context.get("htl_id"):
            state["htl_id"] = context["htl_id"]
            print(f"    → HTL Created: {state['htl_id']}")
        
        # Store booking reference if present
        if body.get("booking_id"):
            state["booking_id"] = body["booking_id"]
            print(f"    → Booking Created: {body.get('booking_reference', 'N/A')}")
        
        # Show providers if any
        providers = body.get("providers", [])
        if providers:
            print(f"\n    📋 Available Providers:")
            for i, p in enumerate(providers[:3], 1):
                print(f"       {i}. {p.get('name')} - {p.get('distance_km')}km - ⭐{p.get('rating')}")
                slots = p.get('time_slots', [])[:3]
                if slots:
                    print(f"          Slots: {', '.join([s['slot_time'][:5] for s in slots])}")
    
    return success


def test_reserve_htl():
    """Reserve a time slot (HTL)"""
    print(f"\n{CYAN}  ── HTL Reservation ──{RESET}")
    
    if not state["user_token"]:
        print("    ❌ No user token. Please login first.")
        return False
    
    # Get session
    if not state["session_id"]:
        print("    Starting a new chat session...")
        success, code, body = make_request("POST", "/chat/start", token=state["user_token"], data={}, expected_status=201)
        if success:
            state["session_id"] = str(body.get("session_id", ""))
        else:
            return False
    
    provider_id = input("    Provider ID (default: 1): ").strip() or "1"
    time_slot_id = input("    Time Slot ID (default: 28): ").strip() or "28"
    
    print(f"    Session: {state['session_id']}")
    print(f"    Provider ID: {provider_id}")
    print(f"    Time Slot ID: {time_slot_id}")
    
    success, code, body = make_request("POST", "/htl/reserve", token=state["user_token"], data={
        "session_id": state["session_id"],
        "provider_id": int(provider_id),
        "time_slot_id": int(time_slot_id)
    }, expected_status=201)
    
    record(success, f"HTL reservation → {code}")
    if success:
        state["htl_id"] = body.get("id")
        print(f"    → HTL ID: {state['htl_id']}")
        print(f"    → Expires in: {body.get('time_remaining_seconds')}s")
    return success


def test_create_booking():
    """Create a direct booking"""
    print(f"\n{CYAN}  ── Create Booking ──{RESET}")
    
    if not state["user_token"]:
        print("    ❌ No user token. Please login first.")
        return False
    
    provider_id = input("    Provider ID (default: 1): ").strip() or "1"
    time_slot_id = input("    Time Slot ID (default: 28): ").strip() or "28"
    instructions = input("    Special instructions (optional): ").strip()
    
    data = {
        "provider_id": int(provider_id),
        "service_category_id": 1,
        "time_slot_id": int(time_slot_id),
    }
    if instructions:
        data["special_instructions"] = instructions
    
    success, code, body = make_request("POST", "/bookings", token=state["user_token"], data=data, expected_status=201)
    record(success, f"Create booking → {code}")
    
    if success:
        state["booking_id"] = body.get("id")
        print(f"    → Booking ID: {state['booking_id']}")
        print(f"    → Booking Reference: {body.get('booking_reference')}")
        print(f"    → Status: {body.get('status')}")
        print(f"    → Date: {body.get('scheduled_date')} at {body.get('scheduled_time')}")
    return success


def test_list_bookings():
    """List user's bookings"""
    print(f"\n{CYAN}  ── List Bookings ──{RESET}")
    
    if not state["user_token"]:
        print("    ❌ No user token. Please login first.")
        return False
    
    status_filter = input("    Filter by status (pending/confirmed/completed/cancelled, optional): ").strip()
    params = {}
    if status_filter:
        params["status"] = status_filter
    
    success, code, body = make_request("GET", "/bookings", token=state["user_token"], params=params)
    record(success, f"List bookings → {code}")
    
    if success and body.get("bookings"):
        print(f"\n    📋 Your Bookings ({body.get('total_count')} total):")
        for b in body["bookings"][:5]:
            print(f"       • {b.get('booking_reference')} - {b.get('status')} - {b.get('scheduled_date')} at {b.get('scheduled_time')}")
            print(f"         Provider: {b.get('provider_name')} - {b.get('service_type')}")
    return success


def test_cancel_booking():
    """Cancel a booking"""
    print(f"\n{CYAN}  ── Cancel Booking ──{RESET}")
    
    if not state["user_token"]:
        print("    ❌ No user token. Please login first.")
        return False
    
    if not state["booking_id"]:
        booking_id = input("    Booking ID to cancel: ").strip()
        if not booking_id:
            print("    ❌ Booking ID required")
            return False
    else:
        booking_id = state["booking_id"]
        print(f"    Using last created booking ID: {booking_id}")
    
    reason = input("    Cancellation reason (optional): ").strip()
    
    data = {}
    if reason:
        data["cancellation_reason"] = reason
    
    success, code, body = make_request("PATCH", f"/bookings/{booking_id}/cancel", token=state["user_token"], data=data)
    record(success, f"Cancel booking → {code}")
    
    if success:
        print(f"    → Status: {body.get('status')}")
    return success


def test_get_providers():
    """List available providers"""
    print(f"\n{CYAN}  ── Available Providers ──{RESET}")
    
    category = input("    Service category (AC Technician/Plumber/Electrician, optional): ").strip()
    
    params = {}
    if category:
        params["category"] = category
    
    success, code, body = make_request("GET", "/providers", params=params)
    record(success, f"Get providers → {code}")
    
    if success and isinstance(body, list):
        print(f"\n    📋 Providers found: {len(body)}")
        for p in body[:5]:
            print(f"       • ID: {p.get('id')} - {p.get('name')}")
            print(f"         Rating: {p.get('rating')}⭐, Available: {p.get('is_available')}")
    return success


def show_status():
    """Show current state"""
    print(f"\n{CYAN}  ── Current State ──{RESET}")
    print(f"    User ID: {state.get('user_id', 'Not set')}")
    print(f"    User Token: {state.get('user_token', 'Not set')[:50] + '...' if state.get('user_token') else 'Not set'}")
    print(f"    Provider ID: {state.get('provider_id', 'Not set')}")
    print(f"    Session ID: {state.get('session_id', 'Not set')}")
    print(f"    HTL ID: {state.get('htl_id', 'Not set')}")
    print(f"    Booking ID: {state.get('booking_id', 'Not set')}")
    print(f"    Slot ID: {state.get('slot_id', 'Not set')}")


def clear_state():
    """Clear all state variables"""
    print(f"\n{CYAN}  ── Clear State ──{RESET}")
    for key in state:
        state[key] = None
    print("    ✓ All state cleared")


# ============================================
# Interactive Menu
# ============================================

def print_menu():
    print_header("PHASE 4 INTERACTIVE TEST MENU")
    print(f"""
  {CYAN}1.{RESET} 🏥 Server Health Check
  {CYAN}2.{RESET} 👤 Register New User
  {CYAN}3.{RESET} 🔐 Login User
  {CYAN}4.{RESET} 🏢 Register Provider
  {CYAN}5.{RESET} ⏰ Create Time Slots (Provider)
  {CYAN}6.{RESET} 💬 Start Chat Session
  {CYAN}7.{RESET} 📝 Send Chat Message
  {CYAN}8.{RESET} 🔒 HTL Reservation (Hold to Lock)
  {CYAN}9.{RESET} 📖 Create Direct Booking
  {CYAN}10.{RESET}📋 List My Bookings
  {CYAN}11.{RESET}❌ Cancel Booking
  {CYAN}12.{RESET}🔍 Show Current State
  {CYAN}13.{RESET}🗑️ Clear State
  {CYAN}14.{RESET}🚀 Run Full Auto Verification
  {CYAN}0.{RESET} Exit
  
  {YELLOW}💡 Tip: For chat flow, use sequence: 6 → 7 (send "yes") → 7 (send "provider 1, slot 1") → 7 (send "confirm"){RESET}
""")


def run_full_verification():
    """Run the complete automated verification"""
    print_header("RUNNING FULL AUTO VERIFICATION")
    
    test_server_health()
    test_register_user()
    test_register_provider()
    test_create_time_slots()
    test_start_chat()
    
    # Send confirmation
    if state["session_id"]:
        print(f"\n  {BLUE}📝 Sending confirmation...{RESET}")
        make_request("POST", "/chat/message", token=state["user_token"],
                     data={"session_id": state["session_id"], "message": "yes"})
        
        # Send provider selection
        print(f"  {BLUE}📝 Selecting provider...{RESET}")
        make_request("POST", "/chat/message", token=state["user_token"],
                     data={"session_id": state["session_id"], "message": "provider 1, slot 1"})
        
        # Send confirmation
        print(f"  {BLUE}📝 Confirming booking...{RESET}")
        success, code, body = make_request("POST", "/chat/message", token=state["user_token"],
                                            data={"session_id": state["session_id"], "message": "confirm"})
        
        if success and body.get("context_data", {}).get("booking_reference"):
            print(f"\n  {GREEN}✓ Full flow completed! Booking created!{RESET}")
    
    test_booking_detailed()
    
    print_header("AUTO VERIFICATION COMPLETE")
    print(f"  {GREEN}Passed: {results['passed']}{RESET}")
    print(f"  {RED}Failed: {results['failed']}{RESET}")


def main():
    while True:
        print_menu()
        choice = input(f"\n{BOLD}Enter your choice (0-14): {RESET}").strip()
        
        if choice == "0":
            print(f"\n  {GREEN}Goodbye!{RESET}")
            break
        elif choice == "1":
            test_server_health()
        elif choice == "2":
            test_register_user()
        elif choice == "3":
            test_login_user()
        elif choice == "4":
            test_register_provider()
        elif choice == "5":
            test_create_time_slots()
        elif choice == "6":
            test_start_chat()
        elif choice == "7":
            test_send_message()
        elif choice == "8":
            test_reserve_htl()
        elif choice == "9":
            test_create_booking()
        elif choice == "10":
            test_list_bookings()
        elif choice == "11":
            test_cancel_booking()
        elif choice == "12":
            show_status()
        elif choice == "13":
            clear_state()
        elif choice == "14":
            run_full_verification()
        else:
            print(f"  {RED}Invalid choice. Please enter 0-14{RESET}")
        
        input(f"\n{YELLOW}Press Enter to continue...{RESET}")


if __name__ == "__main__":
    main()
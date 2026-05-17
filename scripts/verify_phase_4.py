"""
Phase 4 Verification Script with Detailed Output
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

state = {
    "user_token": None,
    "provider_token": None,
    "user_id": None,
    "provider_id": None,
    "session_id": None,
    "htl_id": None,
    "booking_id": None,
    "slot_id": None,
    "test_email_user": f"testuser_{int(time.time())}@example.com",
    "test_email_provider": f"testprovider_{int(time.time())}@example.com",
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
        
        if verbose and method.lower() != "get":
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


# ============================================
# Main Test Functions
# ============================================

def test_server_health():
    print(f"\n{CYAN}  ── Server & Health ──{RESET}")
    r = requests.get(f"{BASE_URL}/", timeout=5)
    record(r.status_code == 200, f"Root endpoint → {r.status_code}")
    
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    data = r.json()
    record(r.status_code == 200, f"Health check → {data.get('status')}")
    record(data.get("database") == "connected", f"Database → {data.get('database')}")


def test_auth():
    print(f"\n{CYAN}  ── Authentication ──{RESET}")
    
    # Register user
    success, code, body = make_request("POST", "/auth/register/user", data={
        "email": state["test_email_user"],
        "phone": f"+923{str(int(time.time()))[-9:]}",
        "password": "TestPass123",
        "full_name": "Test User",
        "city": "Islamabad"
    }, expected_status=201)
    record(success, f"User registration → {code}")
    if success:
        state["user_token"] = body["tokens"]["access_token"]
        state["user_id"] = body["user"]["id"]
    
    # Login
    success, code, body = make_request("POST", "/auth/login/user", data={
        "email": state["test_email_user"], "password": "TestPass123"
    })
    record(success, f"User login → {code}")
    if success:
        state["user_token"] = body["tokens"]["access_token"]


def test_chat_detailed():
    print(f"\n{CYAN}  ── Chat Flow Detailed ──{RESET}")
    
    # Step 1: Start chat
    print(f"\n  {BLUE}📝 Step 1: Start Chat{RESET}")
    success, code, body = make_request("POST", "/chat/start", token=state["user_token"], 
                                        data={"initial_message": "I need an AC technician tomorrow in G-13"},
                                        expected_status=201, verbose=True)
    record(success, f"Start chat → {code}")
    
    if success:
        state["session_id"] = str(body.get("session_id", ""))
        print_json(body, "Start Chat Response")
    
    if not state["session_id"]:
        return
    
    # Step 2: Confirm intent
    print(f"\n  {BLUE}📝 Step 2: Confirm Intent{RESET}")
    success, code, body = make_request("POST", "/chat/message", token=state["user_token"],
                                        data={"session_id": state["session_id"], "message": "yes"},
                                        verbose=True)
    record(success, f"Confirm intent → {code}")
    
    if success:
        print_json(body, "Intent Confirmation Response")
        providers = body.get("providers", [])
        if providers:
            print(f"\n  {GREEN}✓ Found {len(providers)} providers{RESET}")
            for i, p in enumerate(providers[:2]):
                print(f"    Provider {i+1}: {p.get('name')} - {len(p.get('time_slots', []))} time slots")
                if p.get('time_slots'):
                    print(f"      Slots: {[s['slot_time'][:5] for s in p['time_slots'][:3]]}")
    
    # Step 3: Select provider and time slot
    print(f"\n  {BLUE}📝 Step 3: Select Provider + Time Slot{RESET}")
    success, code, body = make_request("POST", "/chat/message", token=state["user_token"],
                                        data={"session_id": state["session_id"], "message": "provider 1, slot 1"},
                                        verbose=True)
    record(success, f"Select provider+slot → {code}")
    
    if success:
        print_json(body, "Provider Selection Response")
        step = body.get("current_step")
        context = body.get("context_data", {})
        print(f"    Current step: {step}")
        if context.get("htl_id"):
            state["htl_id"] = context["htl_id"]
            print(f"    {GREEN}✓ HTL Created: {state['htl_id']}{RESET}")
    
    # Step 4: Confirm booking
    print(f"\n  {BLUE}📝 Step 4: Confirm Booking{RESET}")
    success, code, body = make_request("POST", "/chat/message", token=state["user_token"],
                                        data={"session_id": state["session_id"], "message": "confirm"},
                                        verbose=True)
    record(success, f"Confirm booking → {code}")
    
    if success:
        print_json(body, "Booking Confirmation Response")
        context = body.get("context_data", {})
        if context.get("booking_reference"):
            state["booking_reference"] = context["booking_reference"]
            print(f"    {GREEN}✓ Booking Created: {state['booking_reference']}{RESET}")
    
    # Step 5: End chat
    print(f"\n  {BLUE}📝 Step 5: End Chat{RESET}")
    success, code, body = make_request("POST", f"/chat/end/{state['session_id']}", token=state["user_token"],
                                        expected_status=204, verbose=True)
    record(success or code == 204, f"End chat → {code}")


def test_htl_detailed():
    print(f"\n{CYAN}  ── HTL Reservations Detailed ──{RESET}")
    
    # Create a fresh chat session
    success, code, body = make_request("POST", "/chat/start", token=state["user_token"], data={}, expected_status=201)
    if not success:
        record(False, "Could not create chat session")
        return
    
    session_id = body.get("session_id")
    
    # Reserve a slot
    print(f"\n  {BLUE}📝 Reserve Time Slot{RESET}")
    success, code, body = make_request("POST", "/htl/reserve", token=state["user_token"], data={
        "session_id": session_id,
        "provider_id": 1,  # Ali AC Services
        "time_slot_id": 28  # First slot for tomorrow
    }, expected_status=201, verbose=True)
    record(success, f"Reserve slot → {code}")
    
    if success:
        state["htl_id"] = body.get("id")
        print_json(body, "HTL Reservation Response")
    
    # Get active HTLs
    print(f"\n  {BLUE}📝 Get Active HTLs{RESET}")
    success, code, body = make_request("GET", "/htl/active", token=state["user_token"], verbose=True)
    record(success, f"Get active HTLs → {code}")
    if success and body.get("active_reservations"):
        print_json(body, "Active HTLs")
    
    # Cancel HTL
    if state["htl_id"]:
        print(f"\n  {BLUE}📝 Cancel HTL{RESET}")
        success, code, body = make_request("DELETE", f"/htl/cancel/{state['htl_id']}", token=state["user_token"], verbose=True)
        record(success, f"Cancel HTL → {code}")


def test_booking_detailed():
    print(f"\n{CYAN}  ── Bookings Detailed ──{RESET}")
    
    # Create a booking directly
    print(f"\n  {BLUE}📝 Create Direct Booking{RESET}")
    success, code, body = make_request("POST", "/bookings", token=state["user_token"], data={
        "provider_id": 1,
        "service_category_id": 1,
        "time_slot_id": 28,
        "special_instructions": "Test booking"
    }, expected_status=201, verbose=True)
    record(success, f"Create booking → {code}")
    
    if success:
        state["booking_id"] = body.get("id")
        print_json(body, "Booking Response")
    
    # List bookings
    print(f"\n  {BLUE}📝 List Bookings{RESET}")
    success, code, body = make_request("GET", "/bookings", token=state["user_token"], verbose=True)
    record(success, f"List bookings → {code}")
    if success and body.get("bookings"):
        print_json(body, "Bookings List")


def main():
    print_header("PHASE 4 VERIFICATION - Detailed Mode")
    
    test_server_health()
    test_auth()
    test_chat_detailed()
    test_htl_detailed()
    test_booking_detailed()
    
    print_header("VERIFICATION RESULTS")
    print(f"  {GREEN}Passed: {results['passed']}{RESET}")
    print(f"  {RED}Failed: {results['failed']}{RESET}")
    print(f"  {YELLOW}Warnings: {results['warnings']}{RESET}")


def print_header(title):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{title}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")


if __name__ == "__main__":
    main()
"""
Phase 4 Verification Script - Final Working Version
Tests the complete user flow from chat to booking
"""
import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

state = {
    "user_token": None,
    "user_id": None,
    "session_id": None,
    "booking_id": None,
    "test_email_user": f"testuser_{int(time.time())}@example.com",
}

results = {"passed": 0, "failed": 0, "warnings": 0}


def make_request(method, endpoint, token=None, data=None, expected_status=200, verbose=False):
    url = f"{API_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = getattr(requests, method.lower())(url, json=data, headers=headers, timeout=30)
        success = resp.status_code == expected_status
        
        try:
            body = resp.json()
        except:
            body = {"raw": resp.text}
        
        if verbose and not success:
            print(f"    → Status: {resp.status_code}")
        
        return success, resp.status_code, body
    except Exception as e:
        return False, 0, {"error": str(e)}


def record(success, msg):
    if success:
        print(f"  {GREEN}✓ {msg}{RESET}")
        results["passed"] += 1
    else:
        print(f"  {RED}✗ {msg}{RESET}")
        results["failed"] += 1
    return success


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
    
    success, code, body = make_request("POST", "/auth/login/user", data={
        "email": state["test_email_user"], "password": "TestPass123"
    })
    record(success, f"User login → {code}")
    if success:
        state["user_token"] = body["tokens"]["access_token"]


def test_chat_booking(service_type, location, date_pref, expected_provider_name):
    """Generic chat booking test"""
    message = f"I need a {service_type} {date_pref} in {location}"
    
    print(f"\n  {BLUE}📝 User: '{message}'{RESET}")
    success, code, body = make_request("POST", "/chat/start", token=state["user_token"], 
                                        data={"initial_message": message},
                                        expected_status=201)
    
    if not success:
        record(False, f"Start chat failed for {service_type}")
        return False
    
    session_id = body.get("session_id")
    providers = body.get("providers", [])
    
    if not providers:
        record(False, f"No {service_type} providers found")
        return False
    
    print(f"    Found {len(providers)} provider(s)")
    
    # Select first provider, first slot
    print(f"\n  {BLUE}📝 Selecting 'provider 1, slot 1'{RESET}")
    success2, code2, body2 = make_request("POST", "/chat/message", token=state["user_token"],
                                            data={"session_id": session_id, "message": "provider 1, slot 1"})
    
    if success2 and body2.get("booking_id"):
        print(f"    {GREEN}✓ Booking created! ID: {body2.get('booking_id')}{RESET}")
        record(True, f"{service_type.capitalize()} booking successful")
        state["booking_id"] = body2.get("booking_id")
        return True
    else:
        record(False, f"{service_type.capitalize()} booking failed")
        return False


def test_list_bookings():
    print(f"\n{CYAN}  ── List Bookings ──{RESET}")
    success, code, body = make_request("GET", "/bookings", token=state["user_token"])
    record(success, f"List bookings → {code}")
    
    if success and body.get("bookings"):
        print(f"\n    Total bookings: {body.get('total_count')}")
        for b in body["bookings"][:3]:
            print(f"      • {b.get('booking_reference')} - {b.get('status')} - {b.get('scheduled_date')}")


def test_cancel_booking():
    print(f"\n{CYAN}  ── Cancel Booking ──{RESET}")
    
    if not state.get("booking_id"):
        print("    No booking to cancel")
        return
    
    success, code, body = make_request("PATCH", f"/bookings/{state['booking_id']}/cancel", token=state["user_token"], 
                                        data={"cancellation_reason": "Test cancellation"})
    record(success, f"Cancel booking → {code}")
    
    if success:
        print(f"    Status: {body.get('status')}")


def main():
    print_header("PHASE 4 VERIFICATION - Complete User Flow")
    
    test_server_health()
    test_auth()
    
    print(f"\n{CYAN}  ── Chat Flow Tests (Direct Booking) ──{RESET}")
    
    # Test Electrician
    test_chat_booking("electrician", "F-10", "today", "Bright Spark Electricals")
    
    # Test Plumber  
    test_chat_booking("plumber", "G-13", "tomorrow", "Quick Fix Plumbing")
    
    test_list_bookings()
    test_cancel_booking()
    
    print_header("VERIFICATION RESULTS")
    print(f"  {GREEN}Passed: {results['passed']}{RESET}")
    print(f"  {RED}Failed: {results['failed']}{RESET}")
    
    if results['failed'] == 0:
        print(f"\n  {GREEN}{BOLD}🎉 ALL TESTS PASSED! Phase 4 is ready for frontend integration!{RESET}")
    else:
        print(f"\n  {YELLOW}{BOLD}⚠ Some tests failed. Please check above.{RESET}")


def print_header(title):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{title}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")


if __name__ == "__main__":
    main()
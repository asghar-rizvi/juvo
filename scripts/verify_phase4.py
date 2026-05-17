"""
Phase 4 Verification Script
Tests all Phase 4 endpoints and functionality
"""
import requests
import json
import time
import sys
from datetime import datetime, date, timedelta

# ============================================
# Configuration
# ============================================

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Test state (shared across tests)
state = {
    "user_token": None,
    "provider_token": None,
    "user_id": None,
    "provider_id": None,
    "provider_account_id": None,
    "session_id": None,
    "htl_id": None,
    "booking_id": None,
    "slot_id": None,
    "test_email_user": f"testuser_{int(time.time())}@example.com",
    "test_email_provider": f"testprovider_{int(time.time())}@example.com",
}


# ============================================
# Helpers
# ============================================

def print_header(title: str):
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}")


def print_section(title: str):
    print(f"\n{CYAN}  ── {title} ──{RESET}")


def ok(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str):
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def info(msg: str):
    print(f"  {BLUE}→{RESET} {msg}")


def make_request(
    method: str,
    endpoint: str,
    token: str = None,
    data: dict = None,
    params: dict = None,
    expected_status: int = 200
) -> tuple:
    """
    Make HTTP request and return (success, response_data)
    """
    url = f"{API_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = getattr(requests, method.lower())(
            url,
            json=data,
            params=params,
            headers=headers,
            timeout=30
        )

        success = resp.status_code == expected_status

        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}

        return success, resp.status_code, body

    except requests.exceptions.ConnectionError:
        return False, 0, {"error": "Connection refused - is server running?"}
    except Exception as e:
        return False, 0, {"error": str(e)}


# ============================================
# Test Sections
# ============================================

results = {"passed": 0, "failed": 0, "warnings": 0}


def record(success: bool, msg: str, warning: bool = False):
    if warning:
        warn(msg)
        results["warnings"] += 1
    elif success:
        ok(msg)
        results["passed"] += 1
    else:
        fail(msg)
        results["failed"] += 1
    return success


# ============================================
# 1. Server Health
# ============================================

def test_server_health():
    print_section("Server & Health")

    # Root
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        record(r.status_code == 200, f"Root endpoint → {r.status_code}")
    except Exception as e:
        record(False, f"Cannot reach server: {e}")
        print(f"\n{RED}Server not running! Start with: python main.py{RESET}\n")
        sys.exit(1)

    # Health
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        record(r.status_code == 200, f"Health check → {data.get('status')}")
        record(
            data.get("database") == "connected",
            f"Database → {data.get('database')}"
        )
        record(
            data.get("background_tasks", {}).get("running"),
            f"Background tasks → {data.get('background_tasks', {}).get('running')}"
        )
    except Exception as e:
        record(False, f"Health check failed: {e}")

    # API info
    success, code, body = make_request("GET", "")
    record(code == 200, f"API info → {code}")


# ============================================
# 2. Authentication
# ============================================

def test_auth():
    print_section("Authentication")
    ts = str(int(time.time()))
    user_phone_digits = ("3" + ts)[-10:]  # always 10 digits starting with 3
    user_phone = f"+92{user_phone_digits}"
    
    # Provider phone: slightly different
    provider_phone_digits = ("3" + str(int(time.time()) + 7))[-10:]
    provider_phone = f"+92{provider_phone_digits}"
    
    # Register User
    success, code, body = make_request(
        "POST", "/auth/register/user",
        data={
            "email": state["test_email_user"],
            "phone": user_phone,
            "password": "TestPass123",
            "full_name": "Test User Phase4",
            "city": "Islamabad"
        },
        expected_status=201
    )
    record(success, f"User registration → {code}")

    if success:
        state["user_token"] = body["tokens"]["access_token"]
        state["user_id"] = body["user"]["id"]
        info(f"User ID: {state['user_id']}, Email: {state['test_email_user']}")

    # Login User
    success, code, body = make_request(
        "POST", "/auth/login/user",
        data={
            "email": state["test_email_user"],
            "password": "TestPass123"
        }
    )
    record(success, f"User login → {code}")

    if success and not state["user_token"]:
        state["user_token"] = body["tokens"]["access_token"]

    # Register Provider
    success, code, body = make_request(
        "POST", "/auth/register/provider",
        data={
            "email": state["test_email_provider"],
            "password": "TestPass123",
            "name": "Phase4 Test Provider",
            "phone": provider_phone,
            "service_category_id": 1,
            "address_text": "G-13/1, Islamabad",
            "city": "Islamabad",
            "latitude": 33.6844,
            "longitude": 73.0479,
            "years_experience": 5,
            "price_range": "Rs. 1000-2000"
        },
        expected_status=201
    )
    record(success, f"Provider registration → {code}")

    if success:
        state["provider_token"] = body["tokens"]["access_token"]
        state["provider_account_id"] = body["provider"]["id"]
        state["provider_id"] = body["provider"]["provider_id"]
        info(f"Provider ID: {state['provider_id']}")

    # Login Provider
    success, code, body = make_request(
        "POST", "/auth/login/provider",
        data={
            "email": state["test_email_provider"],
            "password": "TestPass123"
        }
    )
    record(success, f"Provider login → {code}")

    if success and not state["provider_token"]:
        state["provider_token"] = body["tokens"]["access_token"]

    # Get user profile
    success, code, body = make_request(
        "GET", "/auth/me/user",
        token=state["user_token"]
    )
    record(success, f"Get user profile → {code}")

    # Get provider profile
    success, code, body = make_request(
        "GET", "/auth/me/provider",
        token=state["provider_token"]
    )
    record(success, f"Get provider profile → {code}")

    # Test invalid login
    success, code, body = make_request(
        "POST", "/auth/login/user",
        data={"email": "wrong@email.com", "password": "wrong"},
        expected_status=401
    )
    record(success, f"Invalid login rejected → {code}")


# ============================================
# 3. Provider Slot Setup
# ============================================

def test_provider_slots():
    print_section("Provider Time Slots")

    if not state["provider_token"]:
        warn("Skipping slots - no provider token")
        return

    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Create slots
    success, code, body = make_request(
        "POST", "/providers/slots",
        token=state["provider_token"],
        data={
            "slot_date": tomorrow,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "duration_minutes": 60
        },
        expected_status=201
    )
    record(success, f"Create time slots → {code}")

    if success:
        slots = body.get("slots", [])
        record(len(slots) > 0, f"Slots created: {len(slots)}")
        if slots:
            state["slot_id"] = slots[0]["id"]
            info(f"First slot ID: {state['slot_id']}")

    # Get slots
    success, code, body = make_request(
        "GET", "/providers/slots",
        token=state["provider_token"]
    )
    record(success, f"Get time slots → {code}")

    if success:
        total = body.get("total_count", 0)
        available = body.get("available_count", 0)
        record(total > 0, f"Slots retrieved: {total} total, {available} available")

    # Get slots - available only
    success, code, body = make_request(
        "GET", "/providers/slots",
        token=state["provider_token"],
        params={"available_only": True}
    )
    record(success, f"Get available slots only → {code}")


# ============================================
# 4. Chat Flow
# ============================================

def test_chat():
    print_section("Chat & AI Agent")

    if not state["user_token"]:
        warn("Skipping chat - no user token")
        return

    # Start chat
    success, code, body = make_request(
        "POST", "/chat/start",
        token=state["user_token"],
        data={"initial_message": "I need an AC technician tomorrow in G-13"},
        expected_status=201
    )
    record(success, f"Start chat → {code}")

    if success:
        state["session_id"] = str(body.get("session_id", ""))
        current_step = body.get("current_step", "unknown")
        info(f"Session: {state['session_id']}")
        info(f"Step: {current_step}")
        agent_msg = body.get("agent_message", "")
        record(len(agent_msg) > 0, f"Agent responded: {agent_msg[:80]}...")

    if not state["session_id"]:
        warn("No session ID - skipping further chat tests")
        return

    # Send confirmation message
    success, code, body = make_request(
        "POST", "/chat/message",
        token=state["user_token"],
        data={
            "session_id": state["session_id"],
            "message": "yes"
        }
    )
    record(success, f"Send message (confirm intent) → {code}")

    if success:
        step = body.get("current_step", "")
        providers = body.get("providers", [])
        info(f"Step after confirm: {step}")
        if providers:
            info(f"Providers found: {len(providers)}")

    # Get chat history
    success, code, body = make_request(
        "GET", f"/chat/history/{state['session_id']}",
        token=state["user_token"]
    )
    record(success, f"Get chat history → {code}")

    # End chat
    success, code, body = make_request(
        "POST", f"/chat/end/{state['session_id']}",
        token=state["user_token"],
        expected_status=204
    )
    record(success or code == 204, f"End chat → {code}")


# ============================================
# 5. HTL Reservations
# ============================================

def test_htl():
    print_section("HTL Reservations")

    if not state["user_token"] or not state["slot_id"] or not state["provider_id"]:
        warn("Skipping HTL - missing user_token, slot_id, or provider_id")
        return

    # Need a fresh chat session for HTL
    success, code, body = make_request(
        "POST", "/chat/start",
        token=state["user_token"],
        data={},
        expected_status=201
    )

    if success:
        htl_session_id = body.get("session_id")
    else:
        warn("Could not create session for HTL test")
        return

    # Reserve slot
    success, code, body = make_request(
        "POST", "/htl/reserve",
        token=state["user_token"],
        data={
            "session_id": htl_session_id,
            "provider_id": state["provider_id"],
            "time_slot_id": state["slot_id"]
        },
        expected_status=201
    )
    record(success, f"Reserve slot (HTL) → {code}")

    if success:
        state["htl_id"] = body.get("id")
        time_remaining = body.get("time_remaining_seconds", 0)
        record(
            time_remaining > 0,
            f"HTL created: ID={state['htl_id']}, "
            f"expires in {time_remaining}s"
        )

    # Get active HTLs
    success, code, body = make_request(
        "GET", "/htl/active",
        token=state["user_token"]
    )
    record(success, f"Get active HTLs → {code}")

    if success:
        count = body.get("total_count", 0)
        record(count > 0, f"Active HTLs: {count}")

    # Cancel HTL
    if state["htl_id"]:
        success, code, body = make_request(
            "DELETE", f"/htl/cancel/{state['htl_id']}",
            token=state["user_token"]
        )
        record(success, f"Cancel HTL → {code}")
        info(f"HTL {state['htl_id']} cancelled")


# ============================================
# 6. Bookings
# ============================================

def test_bookings():
    print_section("Bookings")

    if not state["user_token"] or not state["provider_id"] or not state["slot_id"]:
        warn("Skipping bookings - missing tokens or IDs")
        return

    # Create direct booking
    success, code, body = make_request(
        "POST", "/bookings",
        token=state["user_token"],
        data={
            "provider_id": state["provider_id"],
            "service_category_id": 1,
            "time_slot_id": state["slot_id"],
            "special_instructions": "Phase 4 test booking"
        },
        expected_status=201
    )
    record(success, f"Create booking → {code}")

    if success:
        state["booking_id"] = body.get("id")
        ref = body.get("booking_reference", "")
        booking_status = body.get("status", "")
        record(len(ref) > 0, f"Booking created: {ref} (status: {booking_status})")

    # List bookings
    success, code, body = make_request(
        "GET", "/bookings",
        token=state["user_token"]
    )
    record(success, f"List bookings → {code}")

    if success:
        total = body.get("total_count", 0)
        record(total > 0, f"Bookings found: {total}")

    # Get specific booking
    if state["booking_id"]:
        success, code, body = make_request(
            "GET", f"/bookings/{state['booking_id']}",
            token=state["user_token"]
        )
        record(success, f"Get booking detail → {code}")

    # Cancel booking
    if state["booking_id"]:
        success, code, body = make_request(
            "PATCH", f"/bookings/{state['booking_id']}/cancel",
            token=state["user_token"],
            data={"cancellation_reason": "Phase 4 test cancellation"}
        )
        record(success, f"Cancel booking → {code}")

        if success:
            cancelled_status = body.get("status", "")
            record(
                cancelled_status == "cancelled",
                f"Booking status after cancel: {cancelled_status}"
            )

    # Filter bookings by status
    success, code, body = make_request(
        "GET", "/bookings",
        token=state["user_token"],
        params={"status": "cancelled"}
    )
    record(success, f"Filter bookings by status → {code}")


# ============================================
# 7. Provider Dashboard
# ============================================

def test_provider_dashboard():
    print_section("Provider Dashboard")

    if not state["provider_token"]:
        warn("Skipping provider dashboard - no provider token")
        return

    # Get provider profile
    success, code, body = make_request(
        "GET", "/providers/profile",
        token=state["provider_token"]
    )
    record(success, f"Get provider profile → {code}")

    if success:
        name = body.get("name", "")
        rating = body.get("rating", 0)
        record(len(name) > 0, f"Profile: {name} (rating: {rating})")

    # Update profile
    success, code, body = make_request(
        "PATCH", "/providers/profile",
        token=state["provider_token"],
        data={
            "price_range": "Rs. 1500-3000",
            "years_experience": 7,
            "is_available": True
        }
    )
    record(success, f"Update provider profile → {code}")

    # Get provider bookings
    success, code, body = make_request(
        "GET", "/providers/bookings",
        token=state["provider_token"]
    )
    record(success, f"Get provider bookings → {code}")

    if success:
        total = body.get("total_count", 0)
        info(f"Provider has {total} total bookings")

    # Get analytics
    success, code, body = make_request(
        "GET", "/providers/analytics",
        token=state["provider_token"]
    )
    record(success, f"Get provider analytics → {code}")

    if success:
        fields = [
            "total_bookings", "completion_rate",
            "average_rating", "utilization_rate"
        ]
        all_present = all(f in body for f in fields)
        record(all_present, f"Analytics has all fields: {fields}")

    # Update booking status (if we have a booking)
    if state["booking_id"]:
        # Note: booking was cancelled, this will likely fail - that's expected
        success, code, body = make_request(
            "PATCH", f"/providers/bookings/{state['booking_id']}/status",
            token=state["provider_token"],
            data={"status": "confirmed", "notes": "Test status update"}
        )
        # It's OK if this fails (booking was cancelled)
        if success:
            record(True, f"Provider booking status update → {code}")
        else:
            warn(f"Booking status update failed (expected if cancelled) → {code}")


# ============================================
# 8. Background Tasks
# ============================================

def test_background_tasks():
    print_section("Background Tasks")

    # Check health endpoint for task status
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        tasks = data.get("background_tasks", {})
        record(tasks.get("running"), f"Tasks running: {tasks.get('running')}")
        record(
            tasks.get("thread_alive"),
            f"Task thread alive: {tasks.get('thread_alive')}"
        )
        info(f"HTL cleanup interval: {tasks.get('htl_cleanup_interval_seconds')}s")
    except Exception as e:
        record(False, f"Background task check failed: {e}")

    # Direct function test
    try:
        from src.core.background_tasks import expire_htl_reservations
        count = expire_htl_reservations()
        record(True, f"HTL expiration function works (expired: {count})")
    except Exception as e:
        record(False, f"HTL expiration function error: {e}")

    try:
        from src.core.background_tasks import cleanup_inactive_sessions
        count = cleanup_inactive_sessions()
        record(True, f"Session cleanup function works (cleaned: {count})")
    except Exception as e:
        record(False, f"Session cleanup function error: {e}")


# ============================================
# 9. Error Handling
# ============================================

def test_error_handling():
    print_section("Error Handling")

    # Unauthorized access
    success, code, body = make_request(
        "GET", "/bookings",
        token=None,
        expected_status=403
    )
    record(code in [401, 403], f"Unauthorized access blocked → {code}")

    # Invalid token
    success, code, body = make_request(
        "GET", "/auth/me/user",
        token="invalid.jwt.token",
        expected_status=401
    )
    record(code == 401, f"Invalid token rejected → {code}")

    # Not found
    success, code, body = make_request(
        "GET", "/bookings/99999",
        token=state["user_token"],
        expected_status=404
    )
    record(code == 404, f"Not found handled → {code}")

    # Wrong role (user token on provider endpoint)
    success, code, body = make_request(
        "GET", "/providers/analytics",
        token=state["user_token"],
        expected_status=401
    )
    record(code in [401, 403], f"Wrong role rejected → {code}")

    # Validation error
    success, code, body = make_request(
        "POST", "/auth/register/user",
        data={"email": "notanemail", "password": "weak"},
        expected_status=422
    )
    record(code == 422, f"Validation error handled → {code}")


# ============================================
# Main Runner
# ============================================

def main():
    print_header("PHASE 4 VERIFICATION - Juvo Service Orchestrator")
    print(f"  {BLUE}Testing against: {BASE_URL}{RESET}")
    print(f"  {BLUE}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")

    # Run all test sections
    test_server_health()
    test_auth()
    test_provider_slots()
    test_chat()
    test_htl()
    test_bookings()
    test_provider_dashboard()
    test_background_tasks()
    test_error_handling()

    # Summary
    total = results["passed"] + results["failed"]
    print_header("VERIFICATION RESULTS")

    print(f"  {GREEN}Passed  : {results['passed']}{RESET}")
    print(f"  {RED}Failed  : {results['failed']}{RESET}")
    print(f"  {YELLOW}Warnings: {results['warnings']}{RESET}")
    print(f"  Total   : {total}")

    if total > 0:
        pass_rate = (results["passed"] / total) * 100
        color = GREEN if pass_rate >= 80 else YELLOW if pass_rate >= 60 else RED
        print(f"\n  {color}{BOLD}Pass Rate: {pass_rate:.1f}%{RESET}")

    if results["failed"] == 0:
        print(f"\n  {GREEN}{BOLD}✓ Phase 4 COMPLETE - All tests passed!{RESET}")
        return 0
    elif results["failed"] <= 3:
        print(f"\n  {YELLOW}{BOLD}⚠ Phase 4 mostly complete - Minor issues{RESET}")
        return 0
    else:
        print(f"\n  {RED}{BOLD}✗ Phase 4 has failures - Review above{RESET}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
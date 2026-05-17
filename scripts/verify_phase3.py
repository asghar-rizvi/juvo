"""
Phase 3 verification script
Tests all authentication and user management features
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"


def print_header(message):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {message}")
    print("="*60)


def print_success(message):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message):
    """Print error message"""
    print(f"✗ {message}")


def test_health_check():
    """Test health endpoint"""
    print_header("1. Testing Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print_success(f"Health check passed - Status: {data['status']}")
        return True
    except Exception as e:
        print_error(f"Health check failed: {str(e)}")
        return False


def test_user_registration():
    """Test user registration"""
    print_header("2. Testing User Registration")
    
    try:
        payload = {
            "email": f"test_user_{datetime.now().timestamp()}@example.com",
            "phone": "+923001234567",
            "password": "SecurePass123",
            "full_name": "Ahmed Khan",
            "city": "Islamabad",
            "address": "House #123, G-13/1"
        }
        
        response = requests.post(
            f"{API_V1}/auth/register/user",
            json=payload
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == payload["email"]
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        
        print_success(f"User registered: {data['user']['email']}")
        print_success(f"Access token received (length: {len(data['tokens']['access_token'])})")
        
        return True, data
        
    except AssertionError as e:
        print_error(f"Registration assertion failed: {str(e)}")
        return False, None
    except Exception as e:
        print_error(f"Registration failed: {str(e)}")
        return False, None


def test_user_login(email, password):
    """Test user login"""
    print_header("3. Testing User Login")
    
    try:
        payload = {
            "email": email,
            "password": password
        }
        
        response = requests.post(
            f"{API_V1}/auth/login/user",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user" in data
        assert "tokens" in data
        
        print_success(f"User logged in: {data['user']['email']}")
        print_success(f"Tokens received")
        
        return True, data
        
    except Exception as e:
        print_error(f"Login failed: {str(e)}")
        return False, None


def test_get_current_user(access_token):
    """Test getting current user profile"""
    print_header("4. Testing Get Current User")
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(
            f"{API_V1}/auth/me/user",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        print_success(f"Profile retrieved: {data['full_name']}")
        print_success(f"Email: {data['email']}")
        print_success(f"Phone: {data['phone']}")
        
        return True
        
    except Exception as e:
        print_error(f"Get profile failed: {str(e)}")
        return False


def test_provider_registration():
    """Test provider registration"""
    print_header("5. Testing Provider Registration")
    
    try:
        payload = {
            "email": f"provider_{datetime.now().timestamp()}@example.com",
            "password": "SecurePass123",
            "name": "Test AC Services",
            "phone": "+923009876543",
            "service_category_id": 1,
            "address_text": "Shop #45, Main Market, G-13/1, Islamabad",
            "city": "Islamabad",
            "years_experience": 8,
            "price_range": "Rs. 1500-3000"
        }
        
        response = requests.post(
            f"{API_V1}/auth/register/provider",
            json=payload
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "provider" in data
        assert "tokens" in data
        
        print_success(f"Provider registered: {data['provider']['provider_name']}")
        print_success(f"Service: {data['provider']['service_category']}")
        print_success(f"Email: {data['provider']['email']}")
        
        return True, data
        
    except Exception as e:
        print_error(f"Provider registration failed: {str(e)}")
        return False, None


def test_provider_login(email, password):
    """Test provider login"""
    print_header("6. Testing Provider Login")
    
    try:
        payload = {
            "email": email,
            "password": password
        }
        
        response = requests.post(
            f"{API_V1}/auth/login/provider",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        print_success(f"Provider logged in: {data['provider']['provider_name']}")
        
        return True, data
        
    except Exception as e:
        print_error(f"Provider login failed: {str(e)}")
        return False, None


def test_get_current_provider(access_token):
    """Test getting current provider profile"""
    print_header("7. Testing Get Current Provider")
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(
            f"{API_V1}/auth/me/provider",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        print_success(f"Provider profile retrieved: {data['provider_name']}")
        print_success(f"Rating: {data['rating']}/5")
        
        return True
        
    except Exception as e:
        print_error(f"Get provider profile failed: {str(e)}")
        return False


def test_token_refresh(refresh_token):
    """Test token refresh"""
    print_header("8. Testing Token Refresh")
    
    try:
        payload = {
            "refresh_token": refresh_token
        }
        
        response = requests.post(
            f"{API_V1}/auth/refresh",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        
        print_success("New access token received")
        print_success("New refresh token received")
        
        return True
        
    except Exception as e:
        print_error(f"Token refresh failed: {str(e)}")
        return False


def test_invalid_token():
    """Test with invalid token"""
    print_header("9. Testing Invalid Token Handling")
    
    try:
        headers = {
            "Authorization": "Bearer invalid_token_here"
        }
        
        response = requests.get(
            f"{API_V1}/auth/me/user",
            headers=headers
        )
        
        assert response.status_code == 401
        print_success("Invalid token correctly rejected")
        
        return True
        
    except Exception as e:
        print_error(f"Invalid token test failed: {str(e)}")
        return False


def test_validation_errors():
    """Test input validation"""
    print_header("10. Testing Input Validation")
    
    results = []
    
    # Test weak password
    try:
        response = requests.post(
            f"{API_V1}/auth/register/user",
            json={
                "email": "test@example.com",
                "phone": "+923001234567",
                "password": "weak",  # Too short
                "full_name": "Test"
            }
        )
        assert response.status_code == 422
        print_success("Weak password rejected")
        results.append(True)
    except:
        print_error("Weak password validation failed")
        results.append(False)
    
    # Test invalid phone
    try:
        response = requests.post(
            f"{API_V1}/auth/register/user",
            json={
                "email": "test2@example.com",
                "phone": "1234567890",  # Invalid format
                "password": "SecurePass123",
                "full_name": "Test"
            }
        )
        assert response.status_code == 422
        print_success("Invalid phone rejected")
        results.append(True)
    except:
        print_error("Phone validation failed")
        results.append(False)
    
    return all(results)


def run_all_tests():
    """Run all verification tests"""
    print("\n" + "="*60)
    print("  PHASE 3 VERIFICATION")
    print("  Authentication & User Management")
    print("="*60)
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health_check()))
    
    # Test 2: User registration
    user_success, user_data = test_user_registration()
    results.append(("User Registration", user_success))
    
    if user_success:
        user_email = user_data["user"]["email"]
        user_password = "SecurePass123"
        user_access_token = user_data["tokens"]["access_token"]
        user_refresh_token = user_data["tokens"]["refresh_token"]
        
        # Test 3: User login
        login_success, login_data = test_user_login(user_email, user_password)
        results.append(("User Login", login_success))
        
        # Test 4: Get current user
        results.append(("Get Current User", test_get_current_user(user_access_token)))
        
        # Test 8: Token refresh
        results.append(("Token Refresh", test_token_refresh(user_refresh_token)))
    
    # Test 5: Provider registration
    provider_success, provider_data = test_provider_registration()
    results.append(("Provider Registration", provider_success))
    
    if provider_success:
        provider_email = provider_data["provider"]["email"]
        provider_password = "SecurePass123"
        provider_access_token = provider_data["tokens"]["access_token"]
        
        # Test 6: Provider login
        prov_login_success, _ = test_provider_login(provider_email, provider_password)
        results.append(("Provider Login", prov_login_success))
        
        # Test 7: Get current provider
        results.append(("Get Current Provider", test_get_current_provider(provider_access_token)))
    
    # Test 9: Invalid token
    results.append(("Invalid Token Handling", test_invalid_token()))
    
    # Test 10: Validation
    results.append(("Input Validation", test_validation_errors()))
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Phase 3 Complete - All authentication working!")
        return True
    else:
        print("\n⚠ Phase 3 Incomplete - Please fix failing tests")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
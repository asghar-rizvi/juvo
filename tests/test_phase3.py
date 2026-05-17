import pytest
from fastapi.testclient import TestClient
from main import app
from src.database.connection import get_db
from src.database.models import User, ProviderAccount
from sqlalchemy.orm import Session

client = TestClient(app)


class TestUserAuth:
    """Test user authentication endpoints"""
    
    def test_user_registration(self):
        """Test user registration"""
        response = client.post(
            "/api/v1/auth/register/user",
            json={
                "email": f"test_user_{pytest.test_id}@example.com",
                "phone": "+923001111111",
                "password": "SecurePass123",
                "full_name": "Test User",
                "city": "Islamabad"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == f"test_user_{pytest.test_id}@example.com"
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
    
    def test_user_login(self):
        """Test user login"""
        # First register
        register_response = client.post(
            "/api/v1/auth/register/user",
            json={
                "email": "login_test@example.com",
                "phone": "+923002222222",
                "password": "SecurePass123",
                "full_name": "Login Test"
            }
        )
        assert register_response.status_code == 201
        
        # Then login
        login_response = client.post(
            "/api/v1/auth/login/user",
            json={
                "email": "login_test@example.com",
                "password": "SecurePass123"
            }
        )
        
        assert login_response.status_code == 200
        data = login_response.json()
        assert "user" in data
        assert "tokens" in data
    
    def test_invalid_login(self):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login/user",
            json={
                "email": "login_test@example.com",
                "password": "WrongPassword123"
            }
        )
        
        assert response.status_code == 401
    
    def test_get_current_user(self):
        """Test getting current user profile"""
        # Register and get token
        register_response = client.post(
            "/api/v1/auth/register/user",
            json={
                "email": "profile_test@example.com",
                "phone": "+923003333333",
                "password": "SecurePass123",
                "full_name": "Profile Test"
            }
        )
        
        tokens = register_response.json()["tokens"]
        access_token = tokens["access_token"]
        
        # Get profile
        profile_response = client.get(
            "/api/v1/auth/me/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert profile_response.status_code == 200
        data = profile_response.json()
        assert data["email"] == "profile_test@example.com"


class TestProviderAuth:
    """Test provider authentication endpoints"""
    
    def test_provider_registration(self):
        """Test provider registration"""
        response = client.post(
            "/api/v1/auth/register/provider",
            json={
                "email": "test_provider@example.com",
                "password": "SecurePass123",
                "name": "Test Provider Services",
                "phone": "+923004444444",
                "service_category_id": 1,
                "address_text": "Test Address, G-13",
                "city": "Islamabad",
                "years_experience": 5,
                "price_range": "Rs. 1000-2000"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "provider" in data
        assert "tokens" in data
        assert data["provider"]["email"] == "test_provider@example.com"
    
    def test_provider_login(self):
        """Test provider login"""
        # Register first
        client.post(
            "/api/v1/auth/register/provider",
            json={
                "email": "provider_login@example.com",
                "password": "SecurePass123",
                "name": "Login Provider",
                "phone": "+923005555555",
                "service_category_id": 1,
                "address_text": "Test Address",
                "city": "Islamabad"
            }
        )
        
        # Login
        response = client.post(
            "/api/v1/auth/login/provider",
            json={
                "email": "provider_login@example.com",
                "password": "SecurePass123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "tokens" in data


class TestTokenManagement:
    """Test token refresh and logout"""
    
    def test_refresh_token(self):
        """Test refreshing access token"""
        # Register and get tokens
        register_response = client.post(
            "/api/v1/auth/register/user",
            json={
                "email": "refresh_test@example.com",
                "phone": "+923006666666",
                "password": "SecurePass123",
                "full_name": "Refresh Test"
            }
        )
        
        tokens = register_response.json()["tokens"]
        refresh_token = tokens["refresh_token"]
        
        # Refresh token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_logout(self):
        """Test logout (token revocation)"""
        # Register
        register_response = client.post(
            "/api/v1/auth/register/user",
            json={
                "email": "logout_test@example.com",
                "phone": "+923007777777",
                "password": "SecurePass123",
                "full_name": "Logout Test"
            }
        )
        
        tokens = register_response.json()["tokens"]
        refresh_token = tokens["refresh_token"]
        
        # Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token}
        )
        
        assert logout_response.status_code == 204


class TestValidation:
    """Test input validation"""
    
    def test_weak_password(self):
        """Test registration with weak password"""
        response = client.post(
            "/api/v1/auth/register/user",
            json={
                "email": "weak@example.com",
                "phone": "+923008888888",
                "password": "weak",  # Too short, no uppercase, no digit
                "full_name": "Weak Password"
            }
        )
        
        assert response.status_code == 422
    
    def test_invalid_phone(self):
        """Test registration with invalid phone"""
        response = client.post(
            "/api/v1/auth/register/user",
            json={
                "email": "phone@example.com",
                "phone": "1234567890",  # Not Pakistani format
                "password": "SecurePass123",
                "full_name": "Invalid Phone"
            }
        )
        
        assert response.status_code == 422
    
    def test_duplicate_email(self):
        """Test registration with duplicate email"""
        # First registration
        client.post(
            "/api/v1/auth/register/user",
            json={
                "email": "duplicate@example.com",
                "phone": "+923009999999",
                "password": "SecurePass123",
                "full_name": "First User"
            }
        )
        
        # Duplicate registration
        response = client.post(
            "/api/v1/auth/register/user",
            json={
                "email": "duplicate@example.com",
                "phone": "+923009999998",
                "password": "SecurePass123",
                "full_name": "Second User"
            }
        )
        
        assert response.status_code == 400


# Add test ID for unique emails
pytest.test_id = 0

@pytest.fixture(autouse=True)
def increment_test_id():
    """Increment test ID for each test"""
    pytest.test_id += 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
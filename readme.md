# Pakistani Service Orchestrator - AI-Powered Informal Economy Platform

An intelligent service matching system for Pakistan's informal economy, built with Google Vertex AI (Antigravity), Gemini, and PostgreSQL/PostGIS.

## 🎯 Phase 1: Foundation & Core Infrastructure

### ✅ Completed Components

1. **Database Layer**
   - PostgreSQL 17.4 with PostGIS extension
   - Structured schema with ACID compliance
   - Geospatial indexing for location-based queries
   - Automatic triggers and constraints

2. **Data Models**
   - SQLAlchemy ORM models
   - Pydantic validation models
   - Multi-lingual support (Urdu, Roman Urdu, English)

3. **Database Tools**
   - Provider discovery with PostGIS
   - Time slot management
   - Booking creation with transaction safety
   - Conversation logging

4. **Seed Data**
   - 6 service categories
   - 7 sample providers (Islamabad locations)
   - 500+ time slots for next 7 days

---

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 17.4
- Google Cloud Project
- Gemini API Key
- Google Maps API Key

---

## 🚀 Installation Steps

### 1. Clone & Setup Environment

```bash
# Navigate to project directory
cd pakistani-service-orchestrator

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt



### **✅ Phase 3: Authentication & User Management (100% Complete)**

**Completed Features:**
- ✅ User registration & login (JWT)
- ✅ Service provider registration & login
- ✅ Password hashing with bcrypt (12 rounds)
- ✅ JWT access & refresh tokens
- ✅ Role-based access control (User vs Provider)
- ✅ Protected routes with authentication
- ✅ Token refresh mechanism
- ✅ Input validation (Pydantic)
- ✅ FastAPI REST endpoints
- ✅ Swagger/OpenAPI documentation
- ✅ CORS configuration
- ✅ Rate limiting
- ✅ Request/Response logging

**New API Endpoints:**

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/auth/register/user` | POST | Register customer | No |
| `/api/v1/auth/login/user` | POST | Login customer | No |
| `/api/v1/auth/register/provider` | POST | Register provider | No |
| `/api/v1/auth/login/provider` | POST | Login provider | No |
| `/api/v1/auth/refresh` | POST | Refresh access token | No |
| `/api/v1/auth/logout` | POST | Logout (revoke token) | No |
| `/api/v1/auth/me/user` | GET | Get user profile | Yes (User) |
| `/api/v1/auth/me/provider` | GET | Get provider profile | Yes (Provider) |

**Testing:**
```bash
# Start API server
python main.py

# Run verification tests
python scripts/verify_phase3.py

# Run pytest
pytest tests/test_phase3.py -v

# Access Swagger docs
open http://localhost:8000/docs
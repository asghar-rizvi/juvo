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

```

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


# 📋 **Phase 4 - Complete README.md**

```markdown
# Juvo Service Orchestrator - Phase 4

## 🎯 Overview

Phase 4 completes the service booking system with a **human-in-the-loop** workflow where users can:
1. Chat naturally with AI to describe service needs
2. View available providers with real-time time slots
3. Book instantly with provider + time slot selection
4. Manage bookings (list, view, cancel)

---

## 🏗️ Architecture

```
User → Chat Interface → AI Agent → Provider Discovery → Time Slot Selection → Instant Booking
```

### Core Components

| Component | Description |
|-----------|-------------|
| **Intent Agent** | Extracts service type, location, date/time using Gemini AI |
| **Discovery Agent** | Finds nearby providers using PostGIS spatial queries |
| **Booking Service** | Creates bookings with database trigger for double-booking prevention |
| **HTL Service** | Hold-to-Lock (5-minute temporary reservations) |
| **Background Tasks** | Auto-cleanup expired HTLs and inactive sessions |

---

## 🗄️ Database Schema (Phase 4)

### New/Modified Tables

| Table | Purpose |
|-------|---------|
| `bookings` | Service bookings with status tracking |
| `time_slots` | Provider availability (15-min to 2-hour slots) |
| `htl_reservations` | Temporary holds (5-minute expiry) |
| `chat_sessions` | Conversation state tracking |
| `conversation_logs` | Complete audit trail of AI interactions |
| `providers` | Service providers with geospatial location |
| `service_categories` | Service types (AC Technician, Plumber, Electrician) |

### Key Database Triggers

```sql
-- Prevents double-booking of time slots
CREATE TRIGGER prevent_double_booking 
  BEFORE INSERT ON bookings 
  FOR EACH ROW 
  EXECUTE FUNCTION prevent_double_booking();
```

---

## 🚀 API Endpoints (Phase 4)

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register/user` | Register new user |
| POST | `/api/v1/auth/login/user` | User login |
| POST | `/api/v1/auth/register/provider` | Register service provider |
| POST | `/api/v1/auth/login/provider` | Provider login |

### Chat & Booking Flow

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/start` | Start chat with initial message |
| POST | `/api/v1/chat/message` | Send message in existing chat |
| GET | `/api/v1/chat/history/{session_id}` | Get chat history |
| POST | `/api/v1/chat/end/{session_id}` | End chat session |

### Booking Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/bookings` | Create direct booking |
| GET | `/api/v1/bookings` | List user's bookings |
| GET | `/api/v1/bookings/{id}` | Get booking details |
| PATCH | `/api/v1/bookings/{id}/cancel` | Cancel booking |
| POST | `/api/v1/bookings/{id}/review` | Add review for completed booking |

### HTL (Hold-to-Lock)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/htl/reserve` | Reserve slot (5-min hold) |
| POST | `/api/v1/htl/confirm` | Convert HTL to booking |
| DELETE | `/api/v1/htl/cancel/{id}` | Cancel HTL |
| GET | `/api/v1/htl/active` | List active HTLs |

### Provider Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/providers/profile` | Get provider profile |
| PATCH | `/api/v1/providers/profile` | Update provider profile |
| GET | `/api/v1/providers/slots` | Get time slots |
| POST | `/api/v1/providers/slots` | Create time slots |
| GET | `/api/v1/providers/bookings` | Get provider's bookings |
| GET | `/api/v1/providers/analytics` | Get analytics |

---

## 🔄 Complete User Flow

### Step-by-Step Walkthrough

```
1. User: "I need an electrician today in F-10"
   ↓
2. Agent extracts intent:
   - Service: Electrician
   - Location: F-10
   - Date: Today
   ↓
3. Agent finds providers with time slots:
   {
     "providers": [{
       "provider_id": 4,
       "name": "Bright Spark Electricals",
       "rating": 4.8,
       "time_slots": [
         {"slot_id": 451, "slot_time": "09:00"},
         {"slot_id": 452, "slot_time": "10:00"}
       ]
     }]
   }
   ↓
4. Frontend renders provider cards with time slot buttons
   ↓
5. User clicks "Book" on Provider 1, Slot 1
   ↓
6. System creates booking instantly:
   {
     "booking_reference": "BK20260518-000020",
     "status": "pending",
     "scheduled_date": "2026-05-18",
     "scheduled_time": "09:00"
   }
   ↓
7. ✅ Booking confirmed!
```

---

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with PostGIS extension
- Google Gemini API key (for AI intent extraction)

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/juvo

# Gemini API
GEMINI_API_KEY=your_api_key_here

# JWT
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google Maps (for geocoding)
GOOGLE_MAPS_API_KEY=your_maps_api_key
```

### Installation

```bash
# Clone repository
git clone <repository-url>
cd juvo-phase-2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
createdb juvo
psql -d juvo -c "CREATE EXTENSION postgis;"

# Run migrations
alembic upgrade head

# Seed database
python scripts/seed_phase4.py

# Start server
python main.py
```

---

## 🧪 Testing

### Run Full Verification

```bash
python scripts/verify_phase_4.py
```

**Expected Output:**
```
============================================================
PHASE 4 VERIFICATION - Complete User Flow
============================================================

  ── Server & Health ──
  ✓ Root endpoint → 200
  ✓ Health check → healthy
  ✓ Database → connected

  ── Authentication ──
  ✓ User registration → 201
  ✓ User login → 200

  ── Chat Flow Tests (Direct Booking) ──
  ✓ Electrician booking successful
  ✓ Plumber booking successful

  ── List Bookings ──
  ✓ List bookings → 200

  ── Cancel Booking ──
  ✓ Cancel booking → 200

============================================================
  🎉 ALL TESTS PASSED!
============================================================
```

### Manual API Testing

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register/user \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","phone":"+923001234567","password":"TestPass123","full_name":"Test User","city":"Islamabad"}'

# Start chat
curl -X POST http://localhost:8000/api/v1/chat/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"initial_message":"I need an electrician today in F-10"}'

# Book provider
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","message":"provider 1, slot 1"}'
```

---

## 📊 Database Schema

### ER Diagram (Phase 4 Core Tables)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     users       │     │   providers     │     │ service_categories│
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │────<│ provider_id (FK)│     │ id (PK)         │
│ email           │     │ name            │────>│ name_en         │
│ phone           │     │ location (GIS)  │     │ name_ur         │
│ password_hash   │     │ rating          │     │ keywords        │
└─────────────────┘     │ is_available    │     └─────────────────┘
                        └─────────────────┘
                               │
                               │
                        ┌──────▼───────┐     ┌─────────────────┐
                        │  time_slots  │     │    bookings     │
                        ├──────────────┤     ├─────────────────┤
                        │ id (PK)      │────<│ time_slot_id(FK)│
                        │ provider_id  │     │ user_id (FK)    │
                        │ slot_date    │     │ booking_reference│
                        │ slot_time    │     │ status          │
                        │ is_booked    │     │ created_at      │
                        └──────────────┘     └─────────────────┘
                               │
                               │
                        ┌──────▼─────────┐
                        │htl_reservations│
                        ├────────────────┤
                        │ id (PK)        │
                        │ time_slot_id   │
                        │ expires_at     │
                        │ is_confirmed   │
                        └────────────────┘
```

---

## 🔑 Key Features Implemented

### ✅ Completed Features

| Feature | Status | Description |
|---------|--------|-------------|
| User Registration | ✅ | Email/phone based registration |
| JWT Authentication | ✅ | Access + refresh tokens |
| AI Intent Extraction | ✅ | Gemini API for multilingual support |
| Provider Discovery | ✅ | PostGIS spatial queries |
| Time Slot Management | ✅ | Create, list, check availability |
| Direct Booking | ✅ | Instant booking without HTL |
| HTL (Hold-to-Lock) | ✅ | 5-minute temporary reservations |
| Booking Management | ✅ | List, view, cancel, review |
| Provider Dashboard | ✅ | Profile, slots, analytics |
| Background Tasks | ✅ | Auto-cleanup HTL and sessions |
| Double-Booking Prevention | ✅ | Database trigger |

### 🚧 Planned Features (Phase 5)

- Payment integration (Stripe/JazzCash)
- Real-time notifications (WebSockets)
- Push notifications (Firebase)
- Provider verification workflow
- Advanced analytics dashboard
- Multi-language UI support

---

## 🐛 Common Issues & Solutions

### Issue: "Time slot already booked"

**Cause:** The slot was booked in a previous test run.

**Solution:** 
```sql
UPDATE time_slots SET is_booked = false WHERE is_booked = true;
```

### Issue: Gemini API quota exceeded

**Cause:** Free tier limit of 20 requests/day.

**Solution:** 
- Wait for daily reset
- Upgrade to paid API key
- Implement fallback intent parser

### Issue: PostGIS extension not found

**Solution:**
```sql
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
```

### Issue: Alembic tries to drop PostGIS tables

**Solution:** Add to `alembic/env.py`:
```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in ['spatial_ref_sys', 'topology', 'layer']:
        return False
    return True
```

---

## 📈 Performance Considerations

### Indexes for Optimization

```sql
-- Spatial indexes for location queries
CREATE INDEX idx_providers_location ON providers USING GIST (location);
CREATE INDEX idx_bookings_location ON bookings USING GIST (location_requested);

-- Time slot queries
CREATE INDEX idx_time_slots_provider_date ON time_slots(provider_id, slot_date);

-- Booking lookups
CREATE INDEX idx_bookings_user_status ON bookings(user_id, status);
CREATE INDEX idx_bookings_created ON bookings(created_at DESC);
```

### Background Jobs

| Job | Interval | Purpose |
|-----|----------|---------|
| `expire_htl_reservations` | 60s | Release expired HTLs |
| `cleanup_inactive_sessions` | 5min | End stale chat sessions |
| `cleanup_expired_notifications` | 1hour | Remove old notifications |

---

## 🔐 Security Considerations

- **Password Hashing:** bcrypt with salt rounds
- **JWT Tokens:** Short-lived access tokens (30min) + refresh tokens (7 days)
- **Role-Based Access:** Separate user/provider authentication
- **SQL Injection Prevention:** Parameterized queries via SQLAlchemy
- **Input Validation:** Pydantic models for all requests
- **Rate Limiting:** (To be implemented in Phase 5)

---

## 📱 Frontend Integration Guide

### 1. Authentication Flow

```javascript
// Register
const register = await fetch('/api/v1/auth/register/user', {
  method: 'POST',
  body: JSON.stringify({ email, phone, password, full_name, city })
});

// Login
const login = await fetch('/api/v1/auth/login/user', {
  method: 'POST', 
  body: JSON.stringify({ email, password })
});

// Store token in localStorage/context
localStorage.setItem('token', response.tokens.access_token);
```

### 2. Chat Component

```javascript
// Start chat with initial message
const startChat = await fetch('/api/v1/chat/start', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({ initial_message: userInput })
});

// Handle response - providers array will be present
const { session_id, providers, agent_message } = response;

// Render provider cards if providers array exists
if (providers?.length) {
  renderProviderCards(providers);
}

// Send subsequent messages
const sendMessage = await fetch('/api/v1/chat/message', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({ session_id, message: userMessage })
});
```

### 3. Provider Card Component

```jsx
{providers.map((provider, idx) => (
  <div key={provider.provider_id} className="provider-card">
    <h3>{provider.name}</h3>
    <div>⭐ {provider.rating} ({provider.total_reviews} reviews)</div>
    <div>📍 {provider.distance_km} km away</div>
    <div>💰 {provider.price_range}</div>
    
    <div className="time-slots">
      {provider.time_slots.map((slot, slotIdx) => (
        <button 
          key={slot.slot_id}
          onClick={() => selectProvider(idx + 1, slotIdx + 1)}
        >
          {slot.slot_time.slice(0, 5)}
        </button>
      ))}
    </div>
  </div>
))}
```

### 4. Booking Confirmation

```javascript
// When user clicks a time slot button
const selectProvider = async (providerNum, slotNum) => {
  const response = await fetch('/api/v1/chat/message', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ 
      session_id, 
      message: `provider ${providerNum}, slot ${slotNum}` 
    })
  });
  
  // Booking created instantly!
  const { booking_id, booking_reference, agent_message } = response;
  showBookingConfirmation(booking_reference);
};
```

---

## 🚀 Deployment

### Docker Setup

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/juvo
    depends_on:
      - db
  
  db:
    image: postgis/postgis:15-3.4
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=juvo
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Production Checklist

- [ ] Set `APP_ENV=production`
- [ ] Use production database (not SQLite)
- [ ] Configure CORS for frontend domain
- [ ] Set up SSL/TLS certificates
- [ ] Configure rate limiting
- [ ] Set up logging aggregation
- [ ] Configure backup strategy
- [ ] Set up monitoring (Prometheus/Grafana)

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| Phase 4.0 | 2026-05-18 | Initial Phase 4 release |
| | | - Complete booking system |
| | | - HTL (Hold-to-Lock) |
| | | - AI chat integration |
| | | - Provider dashboard |
| | | - Background tasks |

---

## 👥 Contributors

- Backend Development: [Your Name]
- Frontend Integration: [Frontend Engineer]

---

## 📄 License

[Your License Here]

---

## 🆘 Support

For issues or questions:
- API Documentation: `http://localhost:8000/docs`
- Email: [support@juvo.com]
- GitHub Issues: [Repository Link]

---

**Phase 4 is complete and ready for frontend integration! 🎉**
```
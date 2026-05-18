# 📋 **Juvo API Documentation - Phase 4**

## Complete API Reference for Frontend Integration

---

## 🌐 **Base URL**
```
http://localhost:8000/api/v1
```

## 🔐 **Authentication**

All authenticated endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## 1️⃣ **Authentication Endpoints**

### **1.1 User Registration**
Register a new customer account.

**Endpoint:** `POST /auth/register/user`

**Request Body:**
```json
{
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+923001234567",
    "password": "TestPass123",
    "city": "Islamabad"
}
```

**Field Requirements:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| full_name | string | Yes | User's full name |
| email | string | Yes | Valid email address |
| phone | string | Yes | Pakistani format: +923XXXXXXXXX |
| password | string | Yes | Min 8 chars, 1 uppercase, 1 number |
| city | string | Yes | City name |

**Response (201 Created):**
```json
{
    "user": {
        "id": 1,
        "email": "john@example.com",
        "phone": "+923001234567",
        "full_name": "John Doe",
        "city": "Islamabad",
        "is_verified": false,
        "is_phone_verified": false,
        "created_at": "2026-05-18T10:00:00"
    },
    "tokens": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
    }
}
```

---

### **1.2 Provider Registration**
Register a new service provider account.

**Endpoint:** `POST /auth/register/provider`

**Request Body:**
```json
{
    "name": "Ali AC Services",
    "email": "ali@acservices.com",
    "phone": "+923001234567",
    "password": "TestPass123",
    "service_category_id": 1,
    "address_text": "Shop #45, Main Market, G-13/1",
    "city": "Islamabad",
    "latitude": 33.6844,
    "longitude": 73.0479,
    "years_experience": 5,
    "price_range": "Rs. 1000-2000"
}
```

**Field Requirements:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Provider business name |
| email | string | Yes | Valid email |
| phone | string | Yes | Pakistani format |
| password | string | Yes | Min 8 chars, 1 uppercase, 1 number |
| service_category_id | integer | Yes | 1=AC, 2=Plumber, 3=Electrician |
| address_text | string | Yes | Full address |
| city | string | Yes | City name |
| latitude | float | Yes | GPS latitude |
| longitude | float | Yes | GPS longitude |
| years_experience | integer | No | Years of experience |
| price_range | string | No | Price range description |

**Response (201 Created):**
```json
{
    "provider": {
        "id": 1,
        "name": "Ali AC Services",
        "email": "ali@acservices.com",
        "phone": "+923001234567",
        "service_category_id": 1,
        "is_available": true,
        "rating": 0.0
    },
    "tokens": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
    }
}
```

---

### **1.3 User Login**
Login existing user.

**Endpoint:** `POST /auth/login/user`

**Request Body:**
```json
{
    "email": "john@example.com",
    "password": "TestPass123"
}
```

**Response (200 OK):**
```json
{
    "user": {
        "id": 1,
        "email": "john@example.com",
        "full_name": "John Doe"
    },
    "tokens": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
    }
}
```

---

### **1.4 Provider Login**
Login existing provider.

**Endpoint:** `POST /auth/login/provider`

**Request Body:**
```json
{
    "email": "ali@acservices.com",
    "password": "TestPass123"
}
```

**Response (200 OK):**
```json
{
    "provider": {
        "id": 1,
        "name": "Ali AC Services",
        "email": "ali@acservices.com"
    },
    "tokens": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
    }
}
```

---

### **1.5 Get Current User Profile**

**Endpoint:** `GET /auth/me/user`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
    "id": 1,
    "email": "john@example.com",
    "phone": "+923001234567",
    "full_name": "John Doe",
    "city": "Islamabad",
    "is_verified": false,
    "created_at": "2026-05-18T10:00:00"
}
```

---

### **1.6 Get Current Provider Profile**

**Endpoint:** `GET /auth/me/provider`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
    "id": 1,
    "name": "Ali AC Services",
    "email": "ali@acservices.com",
    "phone": "+923001234567",
    "service_category": "AC Technician",
    "rating": 4.8,
    "total_reviews": 156,
    "is_available": true,
    "is_verified": true,
    "years_experience": 8,
    "price_range": "Rs. 1500-3000"
}
```

---

## 2️⃣ **Chat & Booking Flow**

### **2.1 Start Chat Session**

**Endpoint:** `POST /chat/start`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
    "initial_message": "I need an electrician today in F-10"
}
```

**Response (201 Created):**

**Case 1: Intent extracted successfully (shows providers immediately)**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_step": "providers_shown",
    "agent_message": "📋 Available Providers for 2026-05-18:\n\n1. Bright Spark Electricals\n   ⭐ Rating: 4.8 (201 reviews)\n   📍 Distance: 5.06 km\n   💰 Price: Rs. 1200-3000\n\n⏰ Available times:\n   Slot 1: 09:00\n   Slot 2: 10:00\n   Slot 3: 11:00",
    "providers": [
        {
            "provider_id": 4,
            "name": "Bright Spark Electricals",
            "distance_km": 5.06,
            "rating": 4.8,
            "total_reviews": 201,
            "phone": "+923441234567",
            "price_range": "Rs. 1200-3000",
            "is_verified": false,
            "time_slots": [
                {
                    "slot_id": 451,
                    "slot_date": "2026-05-18",
                    "slot_time": "09:00:00",
                    "duration_minutes": 60
                },
                {
                    "slot_id": 452,
                    "slot_date": "2026-05-18",
                    "slot_time": "10:00:00",
                    "duration_minutes": 60
                }
            ]
        }
    ],
    "next_action": "Select a provider and time slot. Example: 'provider 1, slot 1'"
}
```

**Case 2: Intent unclear (asks for clarification)**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_step": "initial",
    "agent_message": "I couldn't understand your request. Please tell me what service you need and where.",
    "next_action": "Example: 'I need an AC technician tomorrow in G-13'"
}
```

---

### **2.2 Send Chat Message**

**Endpoint:** `POST /chat/message`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "provider 1, slot 1"
}
```

**Response (200 OK):**

**Case 1: Booking created successfully**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_step": "completed",
    "agent_message": "✅ Booking Confirmed!\n\n📋 Booking Reference: BK20260518-000001\n👤 Provider: Bright Spark Electricals\n⭐ Rating: 4.8 (201 reviews)\n📅 Date: 2026-05-18\n⏰ Time: 09:00:00",
    "booking_id": 1,
    "next_action": "Start a new conversation"
}
```

**Case 2: Slot already taken**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_step": "providers_shown",
    "agent_message": "Sorry, that time slot is no longer available. Please select another one.",
    "providers": [/* same provider list */],
    "next_action": "Select a different provider or time slot"
}
```

---

### **2.3 Get Chat History**

**Endpoint:** `GET /chat/history/{session_id}`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 1,
    "started_at": "2026-05-18T10:00:00",
    "current_step": "completed",
    "is_active": false,
    "messages": [
        {
            "user_input": "I need an electrician today in F-10",
            "agent_response": "Here are available providers...",
            "agent_name": "IntentAgent",
            "created_at": "2026-05-18T10:00:00"
        }
    ]
}
```

---

### **2.4 End Chat Session**

**Endpoint:** `POST /chat/end/{session_id}`

**Headers:** `Authorization: Bearer <token>`

**Response (204 No Content)**

---

## 3️⃣ **Booking Management**

### **3.1 Create Direct Booking**

**Endpoint:** `POST /bookings`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
    "provider_id": 4,
    "service_category_id": 1,
    "time_slot_id": 451,
    "special_instructions": "Please call before arriving"
}
```

**Response (201 Created):**
```json
{
    "id": 1,
    "booking_reference": "BK20260518-000001",
    "user_id": 1,
    "user_name": "John Doe",
    "user_phone": "+923001234567",
    "provider_id": 4,
    "provider_name": "Bright Spark Electricals",
    "service_type": "AC Technician",
    "scheduled_date": "2026-05-18",
    "scheduled_time": "09:00:00",
    "status": "pending",
    "special_instructions": "Please call before arriving",
    "created_at": "2026-05-18T10:00:00"
}
```

---

### **3.2 List User's Bookings**

**Endpoint:** `GET /bookings`

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter: pending, confirmed, in_progress, completed, cancelled |
| page | integer | Page number (default: 1) |
| page_size | integer | Results per page (default: 10, max: 50) |

**Response (200 OK):**
```json
{
    "bookings": [
        {
            "id": 1,
            "booking_reference": "BK20260518-000001",
            "user_name": "John Doe",
            "provider_name": "Bright Spark Electricals",
            "service_type": "Electrician",
            "scheduled_date": "2026-05-18",
            "scheduled_time": "09:00:00",
            "status": "pending",
            "created_at": "2026-05-18T10:00:00"
        }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 10
}
```

---

### **3.3 Get Booking Details**

**Endpoint:** `GET /bookings/{booking_id}`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
    "id": 1,
    "booking_reference": "BK20260518-000001",
    "user_id": 1,
    "user_name": "John Doe",
    "user_phone": "+923001234567",
    "provider_id": 4,
    "provider_name": "Bright Spark Electricals",
    "service_type": "Electrician",
    "scheduled_date": "2026-05-18",
    "scheduled_time": "09:00:00",
    "location": "F-10, Islamabad",
    "status": "pending",
    "special_instructions": "Please call before arriving",
    "estimated_price": null,
    "created_at": "2026-05-18T10:00:00",
    "confirmed_at": null
}
```

---

### **3.4 Cancel Booking**

**Endpoint:** `PATCH /bookings/{booking_id}/cancel`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
    "cancellation_reason": "Changed my mind"
}
```

**Response (200 OK):**
```json
{
    "id": 1,
    "booking_reference": "BK20260518-000001",
    "status": "cancelled",
    "cancelled_at": "2026-05-18T11:00:00",
    "cancellation_reason": "Changed my mind"
}
```

---

### **3.5 Add Review for Completed Booking**

**Endpoint:** `POST /bookings/{booking_id}/review`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
    "rating": 4.5,
    "review_text": "Excellent service, very professional!"
}
```

**Response (201 Created):**
```json
{
    "review_id": 1,
    "booking_id": 1,
    "rating": 4.5,
    "status": "submitted"
}
```

---

## 4️⃣ **HTL (Hold-to-Lock) Endpoints**

### **4.1 Reserve Time Slot (5-minute hold)**

**Endpoint:** `POST /htl/reserve`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "provider_id": 4,
    "time_slot_id": 451
}
```

**Response (201 Created):**
```json
{
    "id": 1,
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "provider_id": 4,
    "provider_name": "Bright Spark Electricals",
    "time_slot_id": 451,
    "slot_date": "2026-05-18",
    "slot_time": "09:00:00",
    "reserved_at": "2026-05-18T10:00:00",
    "expires_at": "2026-05-18T10:05:00",
    "time_remaining_seconds": 299,
    "is_confirmed": false,
    "is_expired": false
}
```

---

### **4.2 Confirm HTL to Create Booking**

**Endpoint:** `POST /htl/confirm`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
    "htl_reservation_id": 1,
    "special_instructions": "Please bring tools"
}
```

**Response (200 OK):**
```json
{
    "booking_id": 1,
    "booking_reference": "BK20260518-000001",
    "htl_id": 1,
    "status": "confirmed"
}
```

---

### **4.3 Cancel HTL Reservation**

**Endpoint:** `DELETE /htl/cancel/{htl_id}`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
    "message": "HTL cancelled",
    "htl_id": 1
}
```

---

### **4.4 Get Active HTL Reservations**

**Endpoint:** `GET /htl/active`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
    "active_reservations": [
        {
            "id": 1,
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "provider_id": 4,
            "provider_name": "Bright Spark Electricals",
            "time_slot_id": 451,
            "slot_date": "2026-05-18",
            "slot_time": "09:00:00",
            "reserved_at": "2026-05-18T10:00:00",
            "expires_at": "2026-05-18T10:05:00",
            "time_remaining_seconds": 299,
            "is_confirmed": false,
            "is_expired": false
        }
    ],
    "total_count": 1
}
```

---

## 5️⃣ **Provider Dashboard Endpoints**

### **5.1 Get Provider Profile**

**Endpoint:** `GET /providers/profile`

**Headers:** `Authorization: Bearer <token>` (Provider token)

**Response (200 OK):**
```json
{
    "id": 1,
    "name": "Ali AC Services",
    "phone": "+923001234567",
    "email": "ali@acservices.com",
    "service_category": "AC Technician",
    "address_text": "Shop #45, Main Market, G-13/1, Islamabad",
    "rating": 4.8,
    "total_reviews": 156,
    "is_available": true,
    "is_verified": true,
    "years_experience": 8,
    "price_range": "Rs. 1500-3000",
    "profile_image_url": null
}
```

---

### **5.2 Update Provider Profile**

**Endpoint:** `PATCH /providers/profile`

**Headers:** `Authorization: Bearer <token>` (Provider token)

**Request Body:**
```json
{
    "name": "Ali AC Services (Updated)",
    "phone": "+923001234567",
    "address_text": "New address",
    "years_experience": 10,
    "price_range": "Rs. 2000-4000",
    "is_available": true
}
```

**Response (200 OK):** Same as GET profile

---

### **5.3 Get Provider's Time Slots**

**Endpoint:** `GET /providers/slots`

**Headers:** `Authorization: Bearer <token>` (Provider token)

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| start_date | date | Filter from date (YYYY-MM-DD) |
| end_date | date | Filter to date |
| available_only | boolean | Show only available slots |

**Response (200 OK):**
```json
{
    "slots": [
        {
            "id": 451,
            "date": "2026-05-18",
            "time": "09:00:00",
            "duration_minutes": 60,
            "is_booked": false,
            "booking_id": null
        }
    ],
    "total_count": 10,
    "available_count": 8,
    "booked_count": 2
}
```

---

### **5.4 Create Time Slots**

**Endpoint:** `POST /providers/slots`

**Headers:** `Authorization: Bearer <token>` (Provider token)

**Request Body:**
```json
{
    "slot_date": "2026-05-19",
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "duration_minutes": 60
}
```

**Response (201 Created):**
```json
{
    "slots": [
        {
            "id": 460,
            "date": "2026-05-19",
            "time": "09:00:00",
            "duration_minutes": 60,
            "is_booked": false,
            "booking_id": null
        }
    ],
    "total_count": 8,
    "available_count": 8,
    "booked_count": 0
}
```

---

### **5.5 Delete Time Slot**

**Endpoint:** `DELETE /providers/slots/{slot_id}`

**Headers:** `Authorization: Bearer <token>` (Provider token)

**Response (200 OK):**
```json
{
    "message": "Slot 451 deleted successfully"
}
```

---

### **5.6 Get Provider's Bookings**

**Endpoint:** `GET /providers/bookings`

**Headers:** `Authorization: Bearer <token>` (Provider token)

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by status |
| start_date | date | Filter from date |
| end_date | date | Filter to date |
| page | integer | Page number |
| page_size | integer | Results per page |

**Response (200 OK):**
```json
{
    "bookings": [
        {
            "id": 1,
            "booking_reference": "BK20260518-000001",
            "user_name": "John Doe",
            "user_phone": "+923001234567",
            "service_type": "Electrician",
            "scheduled_date": "2026-05-18",
            "scheduled_time": "09:00:00",
            "location": "F-10, Islamabad",
            "status": "pending",
            "special_instructions": null,
            "created_at": "2026-05-18T10:00:00"
        }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 20
}
```

---

### **5.7 Update Booking Status (Provider)**

**Endpoint:** `PATCH /providers/bookings/{booking_id}/status`

**Headers:** `Authorization: Bearer <token>` (Provider token)

**Request Body:**
```json
{
    "status": "confirmed",
    "notes": "Will arrive at 9 AM"
}
```

**Valid Status Transitions:**
| From | To |
|------|-----|
| pending | confirmed, cancelled |
| confirmed | in_progress, cancelled |
| in_progress | completed, cancelled |

**Response (200 OK):**
```json
{
    "id": 1,
    "booking_reference": "BK20260518-000001",
    "status": "confirmed",
    "user_name": "John Doe",
    "user_phone": "+923001234567",
    "scheduled_date": "2026-05-18",
    "scheduled_time": "09:00:00"
}
```

---

### **5.8 Get Provider Analytics**

**Endpoint:** `GET /providers/analytics`

**Headers:** `Authorization: Bearer <token>` (Provider token)

**Response (200 OK):**
```json
{
    "total_bookings": 150,
    "completed_bookings": 120,
    "cancelled_bookings": 10,
    "pending_bookings": 20,
    "completion_rate": 80.0,
    "cancellation_rate": 6.67,
    "current_month_bookings": 25,
    "average_rating": 4.8,
    "total_reviews": 156,
    "total_slots": 100,
    "available_slots": 65,
    "booked_slots": 35,
    "utilization_rate": 35.0
}
```

---

## 6️⃣ **Service Categories**

### **Service Category IDs**
| ID | Name |
|----|------|
| 1 | AC Technician |
| 2 | Plumber |
| 3 | Electrician |

---

## 7️⃣ **Error Responses**

### **400 Bad Request**
```json
{
    "detail": "Invalid request parameters"
}
```

### **401 Unauthorized**
```json
{
    "detail": "Could not validate credentials"
}
```

### **403 Forbidden**
```json
{
    "detail": "Not enough permissions"
}
```

### **404 Not Found**
```json
{
    "detail": "Resource not found"
}
```

### **409 Conflict**
```json
{
    "detail": "Time slot already booked"
}
```

### **422 Validation Error**
```json
{
    "detail": [
        {
            "field": "body -> password",
            "message": "Value error, Password must contain at least one uppercase letter",
            "type": "value_error"
        }
    ]
}
```

### **500 Internal Server Error**
```json
{
    "detail": "Internal server error"
}
```

---

## 8️⃣ **Booking Status Values**

| Status | Description |
|--------|-------------|
| pending | Booking created, awaiting provider confirmation |
| confirmed | Provider confirmed the booking |
| in_progress | Service is in progress |
| completed | Service completed successfully |
| cancelled | Booking cancelled |

---

## 9️⃣ **Chat Flow States**

| State | Description |
|-------|-------------|
| initial | Waiting for user input |
| providers_shown | Providers displayed, waiting for selection |
| completed | Booking completed, session ended |

---

## 🔟 **Complete User Journey Flow**

### **Step 1: User Registration**
```
POST /auth/register/user
→ Get access_token
```

### **Step 2: Start Chat with Service Request**
```
POST /chat/start
Body: {"initial_message": "I need an electrician today in F-10"}
→ Get session_id and providers array with time slots
```

### **Step 3: Display Provider Cards**
Frontend renders:
- Provider name, rating, distance
- Time slot buttons (each with slot_id)

### **Step 4: User Selects Provider & Time Slot**
```
POST /chat/message
Body: {"session_id": "...", "message": "provider 1, slot 1"}
→ Booking created instantly
→ Get booking_reference and booking_id
```

### **Step 5: View Bookings**
```
GET /bookings
→ List all user bookings
```

### **Step 6: Cancel if Needed**
```
PATCH /bookings/{id}/cancel
Body: {"cancellation_reason": "Changed mind"}
```

---

## 📱 **Frontend Integration Tips**

### **Store After Login:**
```javascript
localStorage.setItem('access_token', response.tokens.access_token);
localStorage.setItem('user_type', 'user'); // or 'provider'
```

### **Add Token to Requests:**
```javascript
headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
}
```

### **Handle 401 Response:**
```javascript
if (response.status === 401) {
    localStorage.clear();
    window.location.href = '/login.html';
}
```

### **Parse Provider Cards from Response:**
```javascript
if (response.providers && response.providers.length > 0) {
    response.providers.forEach(provider => {
        provider.time_slots.forEach(slot => {
            // Render time slot button with slot.slot_id
        });
    });
}
```

### **Booking Selection Format:**
```javascript
// When user clicks on Provider 1, Slot 2
const message = `provider 1, slot 2`;
```

---

## 📞 **Contact & Support**

- **API Documentation:** `http://localhost:8000/docs`
- **Support Email:** support@juvo.com

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-18  
**Phase:** 4 - Complete

---
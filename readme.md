# Juvo
## A Pakistani Service Orchestrator - AI-Powered Informal Economy Platform

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
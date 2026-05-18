"""
Phase 4 Database Seeding Script - Multi-City Version
Supports providers in Karachi, Islamabad, and Lahore
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
from src.database.connection import SessionLocal, engine
from src.database.models import (
    Base, ServiceCategory, Provider, TimeSlot, User, ProviderAccount,
    Booking, HTLReservation, ChatSession, ConversationLog,
    RefreshToken, Notification, ProviderReview
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# City Coordinates
CITIES = {
    "Islamabad": {
        "center": (73.0479, 33.6844),
        "areas": [
            {"name": "G-13", "lat": 33.6844, "lon": 73.0479},
            {"name": "G-11", "lat": 33.6995, "lon": 73.0412},
            {"name": "F-10", "lat": 33.6893, "lon": 73.0567},
            {"name": "F-7", "lat": 33.6923, "lon": 73.0623},
            {"name": "DHA Islamabad", "lat": 33.6630, "lon": 73.1070},
        ]
    },
    "Karachi": {
        "center": (67.0011, 24.8607),
        "areas": [
            {"name": "DHA Karachi", "lat": 24.8275, "lon": 67.0699},
            {"name": "Clifton", "lat": 24.8138, "lon": 67.0254},
            {"name": "Gulshan-e-Iqbal", "lat": 24.9325, "lon": 67.1000},
            {"name": "North Nazimabad", "lat": 24.9351, "lon": 67.0443},
            {"name": "Korangi", "lat": 24.8460, "lon": 67.1405},
        ]
    },
    "Lahore": {
        "center": (74.3436, 31.5497),
        "areas": [
            {"name": "DHA Lahore", "lat": 31.4500, "lon": 74.4000},
            {"name": "Gulberg", "lat": 31.5204, "lon": 74.3587},
            {"name": "Johar Town", "lat": 31.4700, "lon": 74.3100},
            {"name": "Model Town", "lat": 31.4900, "lon": 74.3400},
            {"name": "Bahria Town Lahore", "lat": 31.4225, "lon": 74.3910},
        ]
    }
}


def truncate_all_tables(db):
    """Truncate all tables in correct order (respect foreign keys)"""
    logger.info("Truncating all tables...")
    
    db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    
    tables = [
        "conversation_logs", "provider_reviews", "refresh_tokens",
        "notifications", "chat_sessions", "htl_reservations", "bookings",
        "time_slots", "provider_accounts", "providers", "service_categories", "users",
    ]
    
    for table in tables:
        try:
            db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
            logger.info(f"  ✓ Truncated: {table}")
        except Exception as e:
            logger.warning(f"  ⚠ Could not truncate {table}: {e}")
    
    db.commit()
    logger.info("All tables truncated successfully")


def seed_service_categories(db):
    """Seed service categories"""
    logger.info("Seeding service categories...")
    
    categories = [
        {
            "name_en": "AC Technician",
            "name_ur": "اے سی ٹیکنیشن",
            "name_roman_ur": "AC Technician",
            "keywords": ["AC", "air conditioner", "cooling", "repair", "maintenance"],
            "description": "Air conditioning installation, repair, and maintenance",
            "is_active": True
        },
        {
            "name_en": "Plumber",
            "name_ur": "پلمبر",
            "name_roman_ur": "Plumber",
            "keywords": ["plumber", "pipe", "water", "leak", "repair"],
            "description": "Plumbing installation and repair services",
            "is_active": True
        },
        {
            "name_en": "Electrician",
            "name_ur": "الیکٹریشن",
            "name_roman_ur": "Electrician",
            "keywords": ["electrician", "wiring", "electricity", "repair"],
            "description": "Electrical installation and repair services",
            "is_active": True
        },
        {
            "name_en": "Carpenter",
            "name_ur": "بڑھئی",
            "name_roman_ur": "Carpenter",
            "keywords": ["carpenter", "wood", "furniture", "repair"],
            "description": "Carpentry and furniture services",
            "is_active": True
        },
        {
            "name_en": "Painter",
            "name_ur": "پینٹر",
            "name_roman_ur": "Painter",
            "keywords": ["painter", "paint", "wall", "color"],
            "description": "Painting and wall finishing services",
            "is_active": True
        },
        {
            "name_en": "Cleaner",
            "name_ur": "صفائی",
            "name_roman_ur": "Cleaner",
            "keywords": ["cleaner", "cleaning", "housekeeping"],
            "description": "Cleaning and housekeeping services",
            "is_active": True
        }
    ]
    
    created = []
    for cat_data in categories:
        category = ServiceCategory(**cat_data)
        db.add(category)
        created.append(category)
        logger.info(f"  ✓ Created: {cat_data['name_en']}")
    
    db.commit()
    return created


def seed_providers(db):
    """Seed providers across multiple cities"""
    logger.info("Seeding providers across Karachi, Islamabad, and Lahore...")
    
    categories = db.query(ServiceCategory).all()
    cat_map = {c.name_en: c.id for c in categories}
    
    providers_data = [
        # ========== ISLAMABAD PROVIDERS ==========
        # AC Technicians - Islamabad
        {
            "name": "Ali AC Services (Islamabad)",
            "phone": "+923001234567",
            "email": "ali.isb@acservices.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(73.0479 33.6844)",
            "address_text": "Main Market, G-13/1, Islamabad",
            "rating": Decimal("4.9"), "total_reviews": 156,
            "is_available": True, "is_verified": True,
            "years_experience": 10, "price_range": "Rs. 1500-3000",
            "city": "Islamabad"
        },
        {
            "name": "Cool Breeze AC (Islamabad)",
            "phone": "+923112345678",
            "email": "cool.isb@ac.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(73.0567 33.6893)",
            "address_text": "F-10 Markaz, Islamabad",
            "rating": Decimal("4.7"), "total_reviews": 89,
            "is_available": True, "is_verified": True,
            "years_experience": 7, "price_range": "Rs. 1200-2500",
            "city": "Islamabad"
        },
        
        # Plumbers - Islamabad
        {
            "name": "Quick Fix Plumbing (Islamabad)",
            "phone": "+923221234567",
            "email": "quickfix.isb@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(73.0412 33.6995)",
            "address_text": "G-11/2, Islamabad",
            "rating": Decimal("4.6"), "total_reviews": 123,
            "is_available": True, "is_verified": True,
            "years_experience": 8, "price_range": "Rs. 800-2000",
            "city": "Islamabad"
        },
        {
            "name": "Hassan Plumbing Works",
            "phone": "+923331234567",
            "email": "hassan.isb@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(73.0623 33.6923)",
            "address_text": "F-7 Markaz, Islamabad",
            "rating": Decimal("4.5"), "total_reviews": 98,
            "is_available": True, "is_verified": False,
            "years_experience": 6, "price_range": "Rs. 1000-2500",
            "city": "Islamabad"
        },
        
        # Electricians - Islamabad
        {
            "name": "Bright Spark Electricals (Islamabad)",
            "phone": "+923441234567",
            "email": "bright.isb@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(73.0598 33.6845)",
            "address_text": "G-9/4, Islamabad",
            "rating": Decimal("4.8"), "total_reviews": 201,
            "is_available": True, "is_verified": True,
            "years_experience": 12, "price_range": "Rs. 1200-3000",
            "city": "Islamabad"
        },
        {
            "name": "Power Tech Electricals",
            "phone": "+923551234567",
            "email": "power.isb@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(73.1060 33.6630)",
            "address_text": "DHA Phase 1, Islamabad",
            "rating": Decimal("4.4"), "total_reviews": 67,
            "is_available": True, "is_verified": True,
            "years_experience": 5, "price_range": "Rs. 1000-2500",
            "city": "Islamabad"
        },
        
        # ========== KARACHI PROVIDERS ==========
        # AC Technicians - Karachi
        {
            "name": "Karachi AC Services (DHA)",
            "phone": "+923342345678",
            "email": "karachi@acservices.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(67.0699 24.8275)",
            "address_text": "DHA Phase 8, Karachi",
            "rating": Decimal("4.8"), "total_reviews": 234,
            "is_available": True, "is_verified": True,
            "years_experience": 15, "price_range": "Rs. 2000-5000",
            "city": "Karachi"
        },
        {
            "name": "Cool Air Solutions",
            "phone": "+923352345678",
            "email": "cool@acservices.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(67.0254 24.8138)",
            "address_text": "Clifton Block 5, Karachi",
            "rating": Decimal("4.7"), "total_reviews": 178,
            "is_available": True, "is_verified": True,
            "years_experience": 12, "price_range": "Rs. 1800-4000",
            "city": "Karachi"
        },
        
        # Plumbers - Karachi
        {
            "name": "Sindh Plumbing Services",
            "phone": "+923362345678",
            "email": "sindh@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(67.1000 24.9325)",
            "address_text": "Gulshan-e-Iqbal Block 13, Karachi",
            "rating": Decimal("4.5"), "total_reviews": 156,
            "is_available": True, "is_verified": True,
            "years_experience": 10, "price_range": "Rs. 1000-2500",
            "city": "Karachi"
        },
        {
            "name": "Water Fix Plumbing",
            "phone": "+923372345678",
            "email": "waterfix@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(67.0443 24.9351)",
            "address_text": "North Nazimabad, Karachi",
            "rating": Decimal("4.6"), "total_reviews": 112,
            "is_available": True, "is_verified": False,
            "years_experience": 8, "price_range": "Rs. 800-2000",
            "city": "Karachi"
        },
        
        # Electricians - Karachi
        {
            "name": "Karachi Electric Solutions",
            "phone": "+923382345678",
            "email": "karachi@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(67.1405 24.8460)",
            "address_text": "Korangi Industrial Area, Karachi",
            "rating": Decimal("4.7"), "total_reviews": 189,
            "is_available": True, "is_verified": True,
            "years_experience": 14, "price_range": "Rs. 1500-3500",
            "city": "Karachi"
        },
        {
            "name": "Bright Home Electricals",
            "phone": "+923392345678",
            "email": "brighthome@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(67.0260 24.8145)",
            "address_text": "Clifton, Karachi",
            "rating": Decimal("4.9"), "total_reviews": 245,
            "is_available": True, "is_verified": True,
            "years_experience": 18, "price_range": "Rs. 2000-4500",
            "city": "Karachi"
        },
        
        # ========== LAHORE PROVIDERS ==========
        # AC Technicians - Lahore
        {
            "name": "Lahore AC Experts",
            "phone": "+923402345678",
            "email": "lahore@acservices.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(74.4000 31.4500)",
            "address_text": "DHA Phase 6, Lahore",
            "rating": Decimal("4.8"), "total_reviews": 201,
            "is_available": True, "is_verified": True,
            "years_experience": 12, "price_range": "Rs. 1800-4000",
            "city": "Lahore"
        },
        {
            "name": "Cool Tech Lahore",
            "phone": "+923412345678",
            "email": "cooltech@acservices.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(74.3587 31.5204)",
            "address_text": "Gulberg III, Lahore",
            "rating": Decimal("4.6"), "total_reviews": 145,
            "is_available": True, "is_verified": True,
            "years_experience": 9, "price_range": "Rs. 1500-3500",
            "city": "Lahore"
        },
        
        # Plumbers - Lahore
        {
            "name": "Punjab Plumbing Services",
            "phone": "+923422345678",
            "email": "punjab@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(74.3100 31.4700)",
            "address_text": "Johar Town, Lahore",
            "rating": Decimal("4.5"), "total_reviews": 134,
            "is_available": True, "is_verified": True,
            "years_experience": 11, "price_range": "Rs. 1000-2500",
            "city": "Lahore"
        },
        {
            "name": "Lahore Pipe Fix",
            "phone": "+923432345678",
            "email": "pipefix@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(74.3400 31.4900)",
            "address_text": "Model Town, Lahore",
            "rating": Decimal("4.4"), "total_reviews": 98,
            "is_available": True, "is_verified": False,
            "years_experience": 7, "price_range": "Rs. 800-2000",
            "city": "Lahore"
        },
        
        # Electricians - Lahore
        {
            "name": "Lahore Electricians",
            "phone": "+923442345678",
            "email": "lahore@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(74.3910 31.4225)",
            "address_text": "Bahria Town, Lahore",
            "rating": Decimal("4.7"), "total_reviews": 167,
            "is_available": True, "is_verified": True,
            "years_experience": 10, "price_range": "Rs. 1500-3500",
            "city": "Lahore"
        },
        {
            "name": "Power House Electricals",
            "phone": "+923452345678",
            "email": "powerhouse@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(74.3600 31.5250)",
            "address_text": "Gulberg, Lahore",
            "rating": Decimal("4.8"), "total_reviews": 189,
            "is_available": True, "is_verified": True,
            "years_experience": 13, "price_range": "Rs. 1800-4000",
            "city": "Lahore"
        },
        
        # ========== CARPENTERS (All Cities) ==========
        {
            "name": "Master Wood Works (Islamabad)",
            "phone": "+923462345678",
            "email": "wood.isb@carpentry.com",
            "service_category_id": cat_map.get("Carpenter"),
            "location": "SRID=4326;POINT(73.0479 33.6844)",
            "address_text": "G-13, Islamabad",
            "rating": Decimal("4.7"), "total_reviews": 89,
            "is_available": True, "is_verified": True,
            "years_experience": 15, "price_range": "Rs. 3000-8000",
            "city": "Islamabad"
        },
        {
            "name": "Karachi Furniture Works",
            "phone": "+923472345678",
            "email": "wood.khi@carpentry.com",
            "service_category_id": cat_map.get("Carpenter"),
            "location": "SRID=4326;POINT(67.0699 24.8275)",
            "address_text": "DHA Karachi",
            "rating": Decimal("4.6"), "total_reviews": 112,
            "is_available": True, "is_verified": True,
            "years_experience": 12, "price_range": "Rs. 3500-9000",
            "city": "Karachi"
        },
        {
            "name": "Lahore Carpentry Experts",
            "phone": "+923482345678",
            "email": "wood.lhe@carpentry.com",
            "service_category_id": cat_map.get("Carpenter"),
            "location": "SRID=4326;POINT(74.4000 31.4500)",
            "address_text": "DHA Lahore",
            "rating": Decimal("4.8"), "total_reviews": 134,
            "is_available": True, "is_verified": True,
            "years_experience": 14, "price_range": "Rs. 3000-8500",
            "city": "Lahore"
        },
        
        # ========== PAINTERS (All Cities) ==========
        {
            "name": "Elite Painters (Islamabad)",
            "phone": "+923492345678",
            "email": "paint.isb@painting.com",
            "service_category_id": cat_map.get("Painter"),
            "location": "SRID=4326;POINT(73.0567 33.6893)",
            "address_text": "F-10, Islamabad",
            "rating": Decimal("4.5"), "total_reviews": 76,
            "is_available": True, "is_verified": True,
            "years_experience": 8, "price_range": "Rs. 5000-15000",
            "city": "Islamabad"
        },
        {
            "name": "Karachi Color Splash",
            "phone": "+923502345678",
            "email": "color.khi@painting.com",
            "service_category_id": cat_map.get("Painter"),
            "location": "SRID=4326;POINT(67.0254 24.8138)",
            "address_text": "Clifton, Karachi",
            "rating": Decimal("4.7"), "total_reviews": 98,
            "is_available": True, "is_verified": True,
            "years_experience": 10, "price_range": "Rs. 6000-18000",
            "city": "Karachi"
        },
        
        # ========== CLEANERS (All Cities) ==========
        {
            "name": "Sparkle Cleaners (Islamabad)",
            "phone": "+923512345678",
            "email": "clean.isb@cleaning.com",
            "service_category_id": cat_map.get("Cleaner"),
            "location": "SRID=4326;POINT(73.0598 33.6845)",
            "address_text": "G-9, Islamabad",
            "rating": Decimal("4.4"), "total_reviews": 67,
            "is_available": True, "is_verified": False,
            "years_experience": 6, "price_range": "Rs. 3000-8000",
            "city": "Islamabad"
        },
        {
            "name": "Karachi Clean Team",
            "phone": "+923522345678",
            "email": "clean.khi@cleaning.com",
            "service_category_id": cat_map.get("Cleaner"),
            "location": "SRID=4326;POINT(67.1000 24.9325)",
            "address_text": "Gulshan, Karachi",
            "rating": Decimal("4.5"), "total_reviews": 89,
            "is_available": True, "is_verified": True,
            "years_experience": 8, "price_range": "Rs. 3500-10000",
            "city": "Karachi"
        }
    ]
    
    created = []
    for prov_data in providers_data:
        provider = Provider(
            name=prov_data["name"],
            phone=prov_data["phone"],
            email=prov_data["email"],
            service_category_id=prov_data["service_category_id"],
            location=prov_data["location"],
            address_text=prov_data["address_text"],
            rating=prov_data["rating"],
            total_reviews=prov_data["total_reviews"],
            is_available=prov_data["is_available"],
            is_verified=prov_data["is_verified"],
            years_experience=prov_data["years_experience"],
            price_range=prov_data["price_range"]
        )
        db.add(provider)
        created.append(provider)
        logger.info(f"  ✓ Created: {prov_data['name']} ({prov_data['city']})")
    
    db.commit()
    logger.info(f"✅ Total providers seeded: {len(created)}")
    return created


def seed_time_slots(db):
    """Seed time slots for next 30 days for all providers"""
    logger.info("Seeding time slots for 30 days...")
    
    providers = db.query(Provider).all()
    
    # Time slots from 8 AM to 8 PM, 1-hour intervals
    slot_times = [time(hour=h, minute=0) for h in range(8, 21)]
    
    start_date = date.today()
    end_date = start_date + timedelta(days=30)
    
    created_count = 0
    
    for provider in providers:
        current_date = start_date
        while current_date <= end_date:
            for slot_time in slot_times:
                time_slot = TimeSlot(
                    provider_id=provider.id,
                    slot_date=current_date,
                    slot_time=slot_time,
                    duration_minutes=60,
                    is_booked=False
                )
                db.add(time_slot)
                created_count += 1
            current_date += timedelta(days=1)
    
    db.commit()
    logger.info(f"  ✓ Created {created_count} time slots for {len(providers)} providers")


def seed_test_users(db):
    """Seed test users for different cities"""
    logger.info("Seeding test users...")
    
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    users_data = [
        {
            "email": "testuser_islamabad@example.com",
            "phone": "+923001234567",
            "full_name": "Test User Islamabad",
            "city": "Islamabad",
            "location": "SRID=4326;POINT(73.0479 33.6844)"
        },
        {
            "email": "testuser_karachi@example.com",
            "phone": "+923342345678",
            "full_name": "Test User Karachi",
            "city": "Karachi",
            "location": "SRID=4326;POINT(67.0699 24.8275)"
        },
        {
            "email": "testuser_lahore@example.com",
            "phone": "+923402345678",
            "full_name": "Test User Lahore",
            "city": "Lahore",
            "location": "SRID=4326;POINT(74.4000 31.4500)"
        }
    ]
    
    created = []
    for user_data in users_data:
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            logger.info(f"  ⚠ User {user_data['email']} already exists, skipping")
            created.append(existing)
            continue
        
        user = User(
            email=user_data["email"],
            phone=user_data["phone"],
            password_hash=pwd_context.hash("TestPass123"),
            full_name=user_data["full_name"],
            city=user_data["city"],
            location=user_data["location"],
            preferred_language="en",
            is_active=True,
            is_verified=True,
            is_phone_verified=True
        )
        db.add(user)
        created.append(user)
        logger.info(f"  ✓ Created test user: {user_data['email']}")
    
    db.commit()
    return created


def verify_seeded_data(db):
    """Verify seeded data"""
    logger.info("\n" + "="*50)
    logger.info("VERIFYING SEEDED DATA")
    logger.info("="*50)
    
    categories = db.query(ServiceCategory).count()
    providers = db.query(Provider).count()
    time_slots = db.query(TimeSlot).count()
    users = db.query(User).count()
    
    logger.info(f"Service Categories: {categories}")
    logger.info(f"Providers: {providers}")
    logger.info(f"Time Slots: {time_slots}")
    logger.info(f"Users: {users}")
    
    # Show providers by city
    logger.info("\n--- Providers by City ---")
    result = db.execute(text("""
        SELECT city, COUNT(*) as count 
        FROM providers 
        GROUP BY city 
        ORDER BY count DESC
    """))
    for row in result:
        logger.info(f"  {row[0]}: {row[1]} providers")
    
    # Show providers with their time slot counts
    logger.info("\n--- Provider Summary ---")
    for provider in db.query(Provider).limit(10).all():
        slot_count = db.query(TimeSlot).filter(
            TimeSlot.provider_id == provider.id,
            TimeSlot.slot_date >= date.today()
        ).count()
        logger.info(f"  {provider.name[:40]}: {slot_count} upcoming slots")
    
    return {
        "categories": categories,
        "providers": providers,
        "time_slots": time_slots,
        "users": users
    }


def main():
    """Main seeding function"""
    logger.info("\n" + "="*60)
    logger.info("PHASE 4 DATABASE SEEDING - MULTI-CITY VERSION")
    logger.info("Seeding Karachi, Islamabad, and Lahore providers")
    logger.info("="*60)
    
    db = SessionLocal()
    
    try:
        # Step 1: Truncate all existing data
        logger.info("\n[1/5] Cleaning existing data...")
        truncate_all_tables(db)
        
        # Step 2: Seed service categories
        logger.info("\n[2/5] Seeding service categories...")
        seed_service_categories(db)
        
        # Step 3: Seed providers (multi-city)
        logger.info("\n[3/5] Seeding providers across cities...")
        seed_providers(db)
        
        # Step 4: Seed time slots
        logger.info("\n[4/5] Seeding time slots for 30 days...")
        seed_time_slots(db)
        
        # Step 5: Seed test users
        logger.info("\n[5/5] Seeding test users...")
        seed_test_users(db)
        
        # Verify everything
        stats = verify_seeded_data(db)
        
        logger.info("\n" + "="*60)
        logger.info("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        logger.info(f"   Total Providers: {stats['providers']}")
        logger.info(f"   Total Time Slots: {stats['time_slots']}")
        logger.info("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
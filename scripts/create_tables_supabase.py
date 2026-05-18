"""
Phase 4 Database Seeding Script - Multi-City Version with City Column
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
        {"name_en": "AC Technician", "name_ur": "اے سی ٹیکنیشن", "name_roman_ur": "AC Technician",
         "keywords": ["AC", "air conditioner", "cooling", "repair", "maintenance"],
         "description": "Air conditioning installation, repair, and maintenance", "is_active": True},
        {"name_en": "Plumber", "name_ur": "پلمبر", "name_roman_ur": "Plumber",
         "keywords": ["plumber", "pipe", "water", "leak", "repair"],
         "description": "Plumbing installation and repair services", "is_active": True},
        {"name_en": "Electrician", "name_ur": "الیکٹریشن", "name_roman_ur": "Electrician",
         "keywords": ["electrician", "wiring", "electricity", "repair"],
         "description": "Electrical installation and repair services", "is_active": True},
        {"name_en": "Carpenter", "name_ur": "بڑھئی", "name_roman_ur": "Carpenter",
         "keywords": ["carpenter", "wood", "furniture", "repair"],
         "description": "Carpentry and furniture services", "is_active": True},
        {"name_en": "Painter", "name_ur": "پینٹر", "name_roman_ur": "Painter",
         "keywords": ["painter", "paint", "wall", "color"],
         "description": "Painting and wall finishing services", "is_active": True},
        {"name_en": "Cleaner", "name_ur": "صفائی", "name_roman_ur": "Cleaner",
         "keywords": ["cleaner", "cleaning", "housekeeping"],
         "description": "Cleaning and housekeeping services", "is_active": True}
    ]
    
    for cat_data in categories:
        existing = db.query(ServiceCategory).filter(ServiceCategory.name_en == cat_data["name_en"]).first()
        if not existing:
            category = ServiceCategory(**cat_data)
            db.add(category)
    
    db.commit()
    logger.info(f"  ✓ Created {len(categories)} categories")


def seed_providers(db):
    """Seed providers across multiple cities with city column"""
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
            "city": "Islamabad",
            "rating": Decimal("4.9"), "total_reviews": 156,
            "is_available": True, "is_verified": True,
            "years_experience": 10, "price_range": "Rs. 1500-3000"
        },
        {
            "name": "Cool Breeze AC (Islamabad)",
            "phone": "+923112345678",
            "email": "cool.isb@ac.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(73.0567 33.6893)",
            "address_text": "F-10 Markaz, Islamabad",
            "city": "Islamabad",
            "rating": Decimal("4.7"), "total_reviews": 89,
            "is_available": True, "is_verified": True,
            "years_experience": 7, "price_range": "Rs. 1200-2500"
        },
        
        # Plumbers - Islamabad
        {
            "name": "Quick Fix Plumbing (Islamabad)",
            "phone": "+923221234567",
            "email": "quickfix.isb@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(73.0412 33.6995)",
            "address_text": "G-11/2, Islamabad",
            "city": "Islamabad",
            "rating": Decimal("4.6"), "total_reviews": 123,
            "is_available": True, "is_verified": True,
            "years_experience": 8, "price_range": "Rs. 800-2000"
        },
        
        # Electricians - Islamabad
        {
            "name": "Bright Spark Electricals (Islamabad)",
            "phone": "+923441234567",
            "email": "bright.isb@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(73.0598 33.6845)",
            "address_text": "G-9/4, Islamabad",
            "city": "Islamabad",
            "rating": Decimal("4.8"), "total_reviews": 201,
            "is_available": True, "is_verified": True,
            "years_experience": 12, "price_range": "Rs. 1200-3000"
        },
        
        # ========== KARACHI PROVIDERS ==========
        {
            "name": "Karachi AC Services (DHA)",
            "phone": "+923342345678",
            "email": "karachi@acservices.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(67.0699 24.8275)",
            "address_text": "DHA Phase 8, Karachi",
            "city": "Karachi",
            "rating": Decimal("4.8"), "total_reviews": 234,
            "is_available": True, "is_verified": True,
            "years_experience": 15, "price_range": "Rs. 2000-5000"
        },
        {
            "name": "Sindh Plumbing Services",
            "phone": "+923362345678",
            "email": "sindh@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(67.1000 24.9325)",
            "address_text": "Gulshan-e-Iqbal, Karachi",
            "city": "Karachi",
            "rating": Decimal("4.5"), "total_reviews": 156,
            "is_available": True, "is_verified": True,
            "years_experience": 10, "price_range": "Rs. 1000-2500"
        },
        {
            "name": "Karachi Electric Solutions",
            "phone": "+923382345678",
            "email": "karachi@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(67.1405 24.8460)",
            "address_text": "Korangi, Karachi",
            "city": "Karachi",
            "rating": Decimal("4.7"), "total_reviews": 189,
            "is_available": True, "is_verified": True,
            "years_experience": 14, "price_range": "Rs. 1500-3500"
        },
        
        # ========== LAHORE PROVIDERS ==========
        {
            "name": "Lahore AC Experts",
            "phone": "+923402345678",
            "email": "lahore@acservices.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(74.4000 31.4500)",
            "address_text": "DHA Phase 6, Lahore",
            "city": "Lahore",
            "rating": Decimal("4.8"), "total_reviews": 201,
            "is_available": True, "is_verified": True,
            "years_experience": 12, "price_range": "Rs. 1800-4000"
        },
        {
            "name": "Punjab Plumbing Services",
            "phone": "+923422345678",
            "email": "punjab@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(74.3100 31.4700)",
            "address_text": "Johar Town, Lahore",
            "city": "Lahore",
            "rating": Decimal("4.5"), "total_reviews": 134,
            "is_available": True, "is_verified": True,
            "years_experience": 11, "price_range": "Rs. 1000-2500"
        },
        {
            "name": "Lahore Electricians",
            "phone": "+923442345678",
            "email": "lahore@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(74.3910 31.4225)",
            "address_text": "Bahria Town, Lahore",
            "city": "Lahore",
            "rating": Decimal("4.7"), "total_reviews": 167,
            "is_available": True, "is_verified": True,
            "years_experience": 10, "price_range": "Rs. 1500-3500"
        },
    ]
    
    created = []
    for prov_data in providers_data:
        existing = db.query(Provider).filter(Provider.phone == prov_data["phone"]).first()
        if not existing:
            provider = Provider(**prov_data)
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
    slot_times = [time(hour=h, minute=0) for h in range(8, 21)]
    start_date = date.today()
    end_date = start_date + timedelta(days=30)
    
    created_count = 0
    for provider in providers:
        current_date = start_date
        while current_date <= end_date:
            for slot_time in slot_times:
                existing = db.query(TimeSlot).filter(
                    TimeSlot.provider_id == provider.id,
                    TimeSlot.slot_date == current_date,
                    TimeSlot.slot_time == slot_time
                ).first()
                if not existing:
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
    logger.info(f"  ✓ Created {created_count} time slots")


def seed_test_users(db):
    """Seed test users"""
    logger.info("Seeding test users...")
    
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    users_data = [
        {"email": "testuser_islamabad@example.com", "phone": "+923001234567", 
         "full_name": "Test User Islamabad", "city": "Islamabad",
         "location": "SRID=4326;POINT(73.0479 33.6844)"},
        {"email": "testuser_karachi@example.com", "phone": "+923342345678", 
         "full_name": "Test User Karachi", "city": "Karachi",
         "location": "SRID=4326;POINT(67.0699 24.8275)"},
        {"email": "testuser_lahore@example.com", "phone": "+923402345678", 
         "full_name": "Test User Lahore", "city": "Lahore",
         "location": "SRID=4326;POINT(74.4000 31.4500)"}
    ]
    
    created = []
    for user_data in users_data:
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing:
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
        WHERE city IS NOT NULL
        GROUP BY city 
        ORDER BY count DESC
    """))
    for row in result:
        logger.info(f"  {row[0]}: {row[1]} providers")
    
    # Show providers by service category
    logger.info("\n--- Providers by Service Category ---")
    result = db.execute(text("""
        SELECT sc.name_en, COUNT(p.id) as count 
        FROM providers p
        JOIN service_categories sc ON sc.id = p.service_category_id
        GROUP BY sc.name_en 
        ORDER BY count DESC
    """))
    for row in result:
        logger.info(f"  {row[0]}: {row[1]} providers")
    
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
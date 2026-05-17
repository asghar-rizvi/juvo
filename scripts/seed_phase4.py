"""
Phase 4 Database Seeding Script
Cleans existing data and seeds fresh test data
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
    
    # Disable triggers to handle foreign key constraints
    db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    
    # Tables in reverse order of dependencies
    tables = [
        "conversation_logs",
        "provider_reviews",
        "refresh_tokens",
        "notifications",
        "chat_sessions",
        "htl_reservations",
        "bookings",
        "time_slots",
        "provider_accounts",
        "providers",
        "service_categories",
        "users",
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
    """Seed providers with proper locations and availability"""
    logger.info("Seeding providers...")
    
    categories = db.query(ServiceCategory).all()
    cat_map = {c.name_en: c.id for c in categories}
    
    providers_data = [
        # AC Technicians - Highly rated, verified
        {
            "name": "⭐ Ali AC Services (Best Rated)",
            "phone": "+923001234567",
            "email": "ali@acservices.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(73.0479 33.6844)",  # G-13
            "address_text": "Main Market, G-13/1, Islamabad",
            "rating": Decimal("4.9"),
            "total_reviews": 156,
            "is_available": True,
            "is_verified": True,
            "years_experience": 10,
            "price_range": "Rs. 1500-3000"
        },
        {
            "name": "Cool Care AC Services",
            "phone": "+923112345678",
            "email": "coolcare@ac.com",
            "service_category_id": cat_map.get("AC Technician"),
            "location": "SRID=4326;POINT(73.0567 33.6893)",  # F-10
            "address_text": "F-10 Markaz, Islamabad",
            "rating": Decimal("4.7"),
            "total_reviews": 89,
            "is_available": True,
            "is_verified": True,
            "years_experience": 7,
            "price_range": "Rs. 1200-2500"
        },
        # Plumbers
        {
            "name": "Quick Fix Plumbing",
            "phone": "+923221234567",
            "email": "quickfix@plumbing.com",
            "service_category_id": cat_map.get("Plumber"),
            "location": "SRID=4326;POINT(73.0412 33.6995)",  # G-11
            "address_text": "G-11/2, Islamabad",
            "rating": Decimal("4.6"),
            "total_reviews": 123,
            "is_available": True,
            "is_verified": True,
            "years_experience": 8,
            "price_range": "Rs. 800-2000"
        },
        # Electricians
        {
            "name": "Bright Spark Electricals",
            "phone": "+923441234567",
            "email": "brightspark@electric.com",
            "service_category_id": cat_map.get("Electrician"),
            "location": "SRID=4326;POINT(73.0598 33.6845)",  # G-9
            "address_text": "G-9/4, Islamabad",
            "rating": Decimal("4.8"),
            "total_reviews": 201,
            "is_available": True,
            "is_verified": True,
            "years_experience": 12,
            "price_range": "Rs. 1200-3000"
        }
    ]
    
    created = []
    for prov_data in providers_data:
        provider = Provider(**prov_data)
        db.add(provider)
        created.append(provider)
        logger.info(f"  ✓ Created: {prov_data['name']}")
    
    db.commit()
    return created


def seed_time_slots(db):
    """Seed time slots for next 14 days for all providers"""
    logger.info("Seeding time slots...")
    
    providers = db.query(Provider).all()
    
    # Time slots from 9 AM to 6 PM, 1-hour intervals
    slot_times = [time(hour=h, minute=0) for h in range(9, 19)]
    
    start_date = date.today()
    end_date = start_date + timedelta(days=14)
    
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
    logger.info(f"  ✓ Created {created_count} time slots")


def seed_test_user(db):
    """Seed a test user for API testing"""
    logger.info("Seeding test user...")
    
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = User(
        email="testuser@example.com",
        phone="+923001234567",
        password_hash=pwd_context.hash("TestPass123"),
        full_name="Test User",
        city="Islamabad",
        location="SRID=4326;POINT(73.0479 33.6844)",
        preferred_language="en",
        is_active=True,
        is_verified=True,
        is_phone_verified=True
    )
    
    # Check if user already exists
    existing = db.query(User).filter(User.email == "testuser@example.com").first()
    if existing:
        logger.info("  ⚠ Test user already exists, skipping")
        return existing
    
    db.add(user)
    db.commit()
    logger.info(f"  ✓ Created test user: {user.email}")
    return user


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
    
    # Show providers with their time slot counts
    logger.info("\n--- Provider Summary ---")
    for provider in db.query(Provider).all():
        slot_count = db.query(TimeSlot).filter(
            TimeSlot.provider_id == provider.id,
            TimeSlot.slot_date >= date.today()
        ).count()
        logger.info(f"  {provider.name}: {slot_count} upcoming slots")
    
    return {
        "categories": categories,
        "providers": providers,
        "time_slots": time_slots,
        "users": users
    }


def main():
    """Main seeding function"""
    logger.info("\n" + "="*60)
    logger.info("PHASE 4 DATABASE SEEDING")
    logger.info("="*60)
    
    db = SessionLocal()
    
    try:
        # Step 1: Truncate all existing data
        logger.info("\n[1/5] Cleaning existing data...")
        truncate_all_tables(db)
        
        # Step 2: Seed service categories
        logger.info("\n[2/5] Seeding service categories...")
        seed_service_categories(db)
        
        # Step 3: Seed providers
        logger.info("\n[3/5] Seeding providers...")
        seed_providers(db)
        
        # Step 4: Seed time slots
        logger.info("\n[4/5] Seeding time slots...")
        seed_time_slots(db)
        
        # Step 5: Seed test user
        logger.info("\n[5/5] Seeding test user...")
        seed_test_user(db)
        
        # Verify everything
        stats = verify_seeded_data(db)
        
        logger.info("\n" + "="*60)
        logger.info("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
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
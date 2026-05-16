from sqlalchemy.orm import Session
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging

from src.database.models import ServiceCategory, Provider, TimeSlot
from src.database.connection import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_service_categories(db: Session):
    """Create service categories"""
    categories = [
        {
            "name_en": "AC Technician",
            "name_ur": "اے سی ٹیکنیشن",
            "name_roman_ur": "AC Technician",
            "keywords": ["AC", "air conditioner", "cooling", "technician", "ٹیکنیشن", "کولنگ"],
            "description": "Air conditioning installation, repair, and maintenance"
        },
        {
            "name_en": "Plumber",
            "name_ur": "پلمبر",
            "name_roman_ur": "Plumber",
            "keywords": ["plumber", "pipe", "water", "leak", "پلمبر", "پانی", "لیک"],
            "description": "Plumbing installation and repair services"
        },
        {
            "name_en": "Electrician",
            "name_ur": "بجلی کا کام کرنے والا",
            "name_roman_ur": "Electrician",
            "keywords": ["electrician", "wiring", "electricity", "بجلی", "وائرنگ"],
            "description": "Electrical installation and repair services"
        },
        {
            "name_en": "Tutor",
            "name_ur": "ٹیوٹر",
            "name_roman_ur": "Tutor",
            "keywords": ["tutor", "teacher", "education", "ٹیوٹر", "استاد", "تعلیم"],
            "description": "Home tutoring services for various subjects"
        },
        {
            "name_en": "Beautician",
            "name_ur": "بیوٹیشن",
            "name_roman_ur": "Beautician",
            "keywords": ["beautician", "makeup", "beauty", "بیوٹی", "میک اپ"],
            "description": "Beauty and makeup services"
        },
        {
            "name_en": "Carpenter",
            "name_ur": "بڑھئی",
            "name_roman_ur": "Barhai",
            "keywords": ["carpenter", "wood", "furniture", "بڑھئی", "لکڑی", "فرنیچر"],
            "description": "Carpentry and furniture services"
        }
    ]
    
    created_categories = []
    for cat_data in categories:
        existing = db.query(ServiceCategory).filter(
            ServiceCategory.name_en == cat_data["name_en"]
        ).first()
        
        if not existing:
            category = ServiceCategory(**cat_data)
            db.add(category)
            created_categories.append(category)
            logger.info(f"Created category: {cat_data['name_en']}")
    
    db.commit()
    return created_categories


def seed_providers(db: Session):
    """Create sample providers with locations in Islamabad"""
    # Get service categories
    categories = db.query(ServiceCategory).all()
    category_map = {cat.name_en: cat.id for cat in categories}
    
    providers_data = [
        # AC Technicians
        {
            "name": "Ali AC Services",
            "phone": "+923001234567",
            "email": "ali.ac@example.com",
            "service_category_id": category_map.get("AC Technician"),
            "location": "SRID=4326;POINT(73.0479 33.6844)",  # G-13, Islamabad
            "address_text": "Shop #45, Main Market, G-13/1, Islamabad",
            "rating": Decimal("4.8"),
            "total_reviews": 156,
            "is_available": True,
            "is_verified": True,
            "years_experience": 8,
            "price_range": "Rs. 1500-3000"
        },
        {
            "name": "Cool Breeze AC",
            "phone": "+923112345678",
            "service_category_id": category_map.get("AC Technician"),
            "location": "SRID=4326;POINT(73.0567 33.6893)",  # F-10, Islamabad
            "address_text": "Plaza 12, F-10 Markaz, Islamabad",
            "rating": Decimal("4.5"),
            "total_reviews": 89,
            "is_available": True,
            "is_verified": True,
            "years_experience": 5,
            "price_range": "Rs. 1000-2500"
        },
        
        # Plumbers
        {
            "name": "Quick Fix Plumbing",
            "phone": "+923221234567",
            "service_category_id": category_map.get("Plumber"),
            "location": "SRID=4326;POINT(73.0412 33.6995)",  # G-11, Islamabad
            "address_text": "House #234, Street 15, G-11/2, Islamabad",
            "rating": Decimal("4.6"),
            "total_reviews": 123,
            "is_available": True,
            "is_verified": True,
            "years_experience": 10,
            "price_range": "Rs. 800-2000"
        },
        {
            "name": "Hassan Plumbing Works",
            "phone": "+923331234567",
            "service_category_id": category_map.get("Plumber"),
            "location": "SRID=4326;POINT(73.0534 33.7001)",  # F-8, Islamabad
            "address_text": "Shop #78, F-8 Markaz, Islamabad",
            "rating": Decimal("4.7"),
            "total_reviews": 98,
            "is_available": True,
            "is_verified": False,
            "years_experience": 7,
            "price_range": "Rs. 1000-2500"
        },
        
        # Electricians
        {
            "name": "Bright Spark Electricals",
            "phone": "+923441234567",
            "service_category_id": category_map.get("Electrician"),
            "location": "SRID=4326;POINT(73.0598 33.6845)",  # G-9, Islamabad
            "address_text": "Building 45, G-9/4, Islamabad",
            "rating": Decimal("4.9"),
            "total_reviews": 201,
            "is_available": True,
            "is_verified": True,
            "years_experience": 12,
            "price_range": "Rs. 1200-3000"
        },
        
        # Tutors
        {
            "name": "Sir Ahmed - Math Tutor",
            "phone": "+923551234567",
            "service_category_id": category_map.get("Tutor"),
            "location": "SRID=4326;POINT(73.0445 33.6878)",  # G-10, Islamabad
            "address_text": "House #456, Street 22, G-10/3, Islamabad",
            "rating": Decimal("4.8"),
            "total_reviews": 67,
            "is_available": True,
            "is_verified": True,
            "years_experience": 6,
            "price_range": "Rs. 2000-4000/month"
        },
        
        # Beauticians
        {
            "name": "Glam Studio",
            "phone": "+923661234567",
            "service_category_id": category_map.get("Beautician"),
            "location": "SRID=4326;POINT(73.0623 33.6923)",  # F-7, Islamabad
            "address_text": "2nd Floor, F-7 Markaz, Islamabad",
            "rating": Decimal("4.7"),
            "total_reviews": 134,
            "is_available": True,
            "is_verified": True,
            "years_experience": 5,
            "price_range": "Rs. 3000-8000"
        }
    ]
    
    created_providers = []
    for prov_data in providers_data:
        existing = db.query(Provider).filter(
            Provider.phone == prov_data["phone"]
        ).first()
        
        if not existing:
            provider = Provider(**prov_data)
            db.add(provider)
            created_providers.append(provider)
            logger.info(f"Created provider: {prov_data['name']}")
    
    db.commit()
    return created_providers


def seed_time_slots(db: Session):
    """Create time slots for next 7 days for all providers"""
    providers = db.query(Provider).all()
    
    # Time slots: 9 AM to 5 PM, 1-hour intervals
    time_slots = [
        time(hour=h, minute=0) 
        for h in range(9, 18)  # 9 AM to 5 PM
    ]
    
    # Create slots for next 7 days
    start_date = date.today()
    created_count = 0
    
    for provider in providers:
        for day_offset in range(7):
            slot_date = start_date + timedelta(days=day_offset)
            
            for slot_time in time_slots:
                existing = db.query(TimeSlot).filter(
                    TimeSlot.provider_id == provider.id,
                    TimeSlot.slot_date == slot_date,
                    TimeSlot.slot_time == slot_time
                ).first()
                
                if not existing:
                    time_slot = TimeSlot(
                        provider_id=provider.id,
                        slot_date=slot_date,
                        slot_time=slot_time,
                        duration_minutes=60,
                        is_booked=False
                    )
                    db.add(time_slot)
                    created_count += 1
    
    db.commit()
    logger.info(f"Created {created_count} time slots")


def seed_all():
    logger.info("Starting database seeding...")
    
    with get_db() as db:
        logger.info("Seeding service categories...")
        seed_service_categories(db)
        
        logger.info("Seeding providers...")
        seed_providers(db)
        
        logger.info("Seeding time slots...")
        seed_time_slots(db)
    
    logger.info("✓ Database seeding completed successfully!")


if __name__ == "__main__":
    seed_all()
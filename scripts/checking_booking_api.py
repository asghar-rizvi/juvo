#!/usr/bin/env python
"""Direct test of booking creation - bypasses API"""
import sys
sys.path.append('.')

from src.database.connection import SessionLocal
from src.database.models import User, TimeSlot
from src.tools import DatabaseTools
import uuid

def test_booking():
    db = SessionLocal()
    
    # Get a test user
    user = db.query(User).filter(User.email == "testbooking2@example.com").first()
    if not user:
        print("User not found! Creating one...")
        from src.core.security import get_password_hash
        user = User(
            email="testbooking2@example.com",
            phone="+92300123456",
            password_hash=get_password_hash("TestPass123"),
            full_name="Test User",
            city="Islamabad"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    print(f"User: {user.id} - {user.email}")
    
    # Get a slot
    slot = db.query(TimeSlot).filter(TimeSlot.id == 11).first()
    print(f"Slot: {slot.id} - provider={slot.provider_id}, date={slot.slot_date}, booked={slot.is_booked}")
    
    # Try to create booking
    tools = DatabaseTools(db)
    print("Calling create_booking_record...")
    
    booking = tools.create_booking_record(
        session_id=str(uuid.uuid4()),
        user_phone=user.phone,
        provider_id=1,
        service_category_id=1,
        time_slot_id=11,
        user_name=user.full_name
    )
    
    if booking:
        print(f"SUCCESS! Booking created: {booking.booking_reference}")
    else:
        print("FAILED! Booking creation returned None")
    
    db.close()

if __name__ == "__main__":
    test_booking()
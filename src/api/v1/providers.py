"""
Provider dashboard endpoints
/api/v1/providers/*
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, time as time_type

from src.models.provider import (
    TimeSlotCreateRequest,
    TimeSlotListResponse,
    ProviderProfileUpdateRequest,
    ProviderProfileResponse,
    ProviderAnalyticsResponse,
    BookingStatusUpdateRequest
)
from src.models.booking import ProviderBookingResponse
from src.services.provider_service import ProviderService
from src.api.dependencies import get_db, CurrentProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/providers", tags=["Provider Dashboard"])


# ============================================
# Booking Management
# ============================================

@router.get(
    "/bookings",
    response_model=dict,
    summary="Get provider's bookings",
    description="List all bookings for the authenticated provider"
)
def get_provider_bookings(
    current_provider: CurrentProvider,
    db: Session = Depends(get_db),
    booking_status: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by: pending, confirmed, in_progress, completed, cancelled"
    ),
    start_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page")
):
    """
    Get provider's bookings with filters.

    **Filters:**
    - status: pending, confirmed, in_progress, completed, cancelled
    - start_date / end_date: Date range filter
    - Pagination with page & page_size

    **Returns:**
    - List of bookings with user info
    - Total count and pagination info
    """
    provider_service = ProviderService(db)

    return provider_service.get_provider_bookings(
        provider_account=current_provider,
        booking_status=booking_status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )


@router.patch(
    "/bookings/{booking_id}/status",
    response_model=ProviderBookingResponse,
    summary="Update booking status",
    description="Provider updates booking status (confirm, start, complete)"
)
def update_booking_status(
    booking_id: int,
    request: BookingStatusUpdateRequest,
    current_provider: CurrentProvider,
    db: Session = Depends(get_db)
):
    """
    Update booking status.

    **Valid transitions:**
    - pending → confirmed, cancelled
    - confirmed → in_progress, cancelled
    - in_progress → completed, cancelled

    **Notes:**
    - completed → logs completion timestamp
    - cancelled → logs reason and timestamp
    """
    provider_service = ProviderService(db)

    return provider_service.update_booking_status(
        provider_account=current_provider,
        booking_id=booking_id,
        new_status=request.status,
        notes=request.notes
    )


# ============================================
# Time Slot Management
# ============================================

@router.get(
    "/slots",
    response_model=TimeSlotListResponse,
    summary="Get provider's time slots",
    description="List time slots with availability info"
)
def get_time_slots(
    current_provider: CurrentProvider,
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(
        None,
        description="Start date filter (defaults to today)"
    ),
    end_date: Optional[date] = Query(
        None,
        description="End date filter"
    ),
    available_only: bool = Query(
        False,
        description="Show only available (unbooked) slots"
    )
):
    """
    Get provider's time slots.

    **Defaults:**
    - Shows today onwards
    - Includes both booked and available slots

    **Returns:**
    - All slots in range
    - Count of available vs booked
    """
    provider_service = ProviderService(db)

    return provider_service.get_time_slots(
        provider_account=current_provider,
        start_date=start_date,
        end_date=end_date,
        include_booked=not available_only
    )


@router.post(
    "/slots",
    response_model=TimeSlotListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create time slots",
    description="Add new time slots for a specific date"
)
def create_time_slots(
    request: TimeSlotCreateRequest,
    current_provider: CurrentProvider,
    db: Session = Depends(get_db)
):
    """
    Create time slots for a day.

    **Example:**
    Create hourly slots from 9 AM to 5 PM on Jan 15:
    ```json
    {
      "slot_date": "2024-01-15",
      "start_time": "09:00:00",
      "end_time": "17:00:00",
      "duration_minutes": 60
    }
    ```

    **Result:**
    - 8 slots created (9:00, 10:00, ..., 16:00)
    - Skips already existing slots
    - Returns all newly created slots
    """
    provider_service = ProviderService(db)

    return provider_service.create_time_slots(
        provider_account=current_provider,
        slot_date=request.slot_date,
        start_time=request.start_time,
        end_time=request.end_time,
        duration_minutes=request.duration_minutes
    )


@router.delete(
    "/slots/{slot_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete time slot",
    description="Remove an unbooked time slot"
)
def delete_time_slot(
    slot_id: int,
    current_provider: CurrentProvider,
    db: Session = Depends(get_db)
):
    """
    Delete an unbooked time slot.

    **Restrictions:**
    - Cannot delete booked slots
    - Must belong to current provider
    """
    provider_service = ProviderService(db)
    provider_service.delete_time_slot(current_provider, slot_id)

    return {"message": f"Slot {slot_id} deleted successfully"}


# ============================================
# Profile Management
# ============================================

@router.get(
    "/profile",
    response_model=ProviderProfileResponse,
    summary="Get provider profile",
    description="Get current provider's complete profile"
)
def get_profile(
    current_provider: CurrentProvider,
    db: Session = Depends(get_db)
):
    """
    Get provider profile.

    Returns complete profile including:
    - Basic info (name, phone, address)
    - Rating and reviews
    - Availability status
    - Experience and pricing
    """
    provider_service = ProviderService(db)
    return provider_service.get_provider_profile(current_provider)


@router.patch(
    "/profile",
    response_model=ProviderProfileResponse,
    summary="Update provider profile",
    description="Update provider's profile information"
)
def update_profile(
    request: ProviderProfileUpdateRequest,
    current_provider: CurrentProvider,
    db: Session = Depends(get_db)
):
    """
    Update provider profile.

    **Updatable fields:**
    - name, phone, address_text
    - years_experience, price_range
    - is_available (toggle availability)
    - profile_image_url

    Only provided fields will be updated (partial update).
    """
    provider_service = ProviderService(db)
    return provider_service.update_provider_profile(current_provider, request)


# ============================================
# Analytics
# ============================================

@router.get(
    "/analytics",
    response_model=ProviderAnalyticsResponse,
    summary="Get provider analytics",
    description="Get comprehensive statistics for provider dashboard"
)
def get_analytics(
    current_provider: CurrentProvider,
    db: Session = Depends(get_db)
):
    """
    Get provider analytics.

    **Includes:**
    - Total, completed, cancelled bookings
    - Completion and cancellation rates
    - Current month bookings
    - Rating and review stats
    - Slot utilization rate
    - Available vs booked slots
    """
    provider_service = ProviderService(db)
    return provider_service.get_analytics(current_provider)
"""
Booking endpoints - Fixed version
/api/v1/bookings/*
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session
from typing import Optional

from src.models.booking import (
    BookingCreateRequest, BookingResponse, BookingListResponse,
    BookingCancelRequest, ReviewCreateRequest
)
from src.services.booking_service import BookingService
from src.api.dependencies import get_db, CurrentUser
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    response_model=BookingResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create booking directly",
    description="Book a time slot directly (without HTL reservation)"
)
def create_booking(
    request: BookingCreateRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Create a booking directly.

    Alternative to the HTL flow — books immediately without hold.

    **Validations:**
    - Provider must exist and be active
    - Time slot must be available
    - Service category must be valid
    """
    booking_service = BookingService(db)
    return booking_service.create_booking(
        user=current_user,
        provider_id=request.provider_id,
        service_category_id=request.service_category_id,
        time_slot_id=request.time_slot_id,
        special_instructions=request.special_instructions
    )


@router.get(
    "",
    response_model=BookingListResponse,
    summary="List user's bookings",
    description="Get all bookings for current user with optional filters"
)
def list_bookings(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    booking_status: Optional[str] = Query(
        None,
        alias="status",
        description="Filter: pending, confirmed, in_progress, completed, cancelled"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Results per page")
):
    """
    List user's bookings.

    **Filters:**
    - `status`: Filter by booking status
    - `page` / `page_size`: Pagination

    **Returns:**
    - Bookings with provider info
    - Total count
    - Pagination details
    """
    booking_service = BookingService(db)
    return booking_service.get_user_bookings(
        user=current_user,
        status=booking_status,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get booking details",
    description="Get complete details for a specific booking"
)
def get_booking(
    booking_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Get single booking details.

    Returns full booking info including:
    - Provider details
    - Scheduled date and time
    - Current status
    - Special instructions
    """
    booking_service = BookingService(db)
    return booking_service.get_booking_details(current_user, booking_id)


@router.patch(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Cancel booking",
    description="Cancel an active booking and release the time slot"
)
def cancel_booking(
    booking_id: int,
    request: BookingCancelRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Cancel a booking.

    **Actions taken:**
    - Marks booking as cancelled
    - Frees up the time slot for others
    - Records cancellation reason and timestamp

    **Restrictions:**
    - Cannot cancel completed bookings
    - Cannot cancel already cancelled bookings
    """
    booking_service = BookingService(db)
    return booking_service.cancel_booking(
        user=current_user,
        booking_id=booking_id,
        cancellation_reason=request.cancellation_reason
    )


@router.post(
    "/{booking_id}/review",
    response_model=dict,
    status_code=http_status.HTTP_201_CREATED,
    summary="Add review for completed booking",
    description="Submit a rating and review for a completed service"
)
def add_review(
    booking_id: int,
    review: ReviewCreateRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Add review for a completed booking.

    **Requirements:**
    - Booking must be in `completed` status
    - User must be the booking owner
    - Cannot review the same booking twice

    **Effect:**
    - Saves rating (0-5) and review text
    - Updates provider's average rating via DB trigger
    """
    booking_service = BookingService(db)
    return booking_service.add_review(current_user, booking_id, review)
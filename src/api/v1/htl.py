"""
HTL (Hold-to-Lock) endpoints - Fixed version
/api/v1/htl/*
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.models.htl import (
    HTLReserveRequest, HTLConfirmRequest,
    HTLReservationResponse, HTLListResponse
)
from src.services.htl_service import HTLService
from src.api.dependencies import get_db, CurrentUser
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/htl", tags=["HTL Reservations"])


@router.post(
    "/reserve",
    response_model=HTLReservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve time slot - 5 minute hold",
    description=(
        "Lock a time slot for 5 minutes. "
        "Auto-expires if not confirmed within time limit."
    )
)
def reserve_slot(
    request: HTLReserveRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Reserve a time slot (HTL - Hold To Lock).

    **Flow:**
    1. User selects provider from chat
    2. System creates 5-minute hold
    3. User confirms → booking created
    4. If not confirmed → slot released automatically

    **Errors:**
    - 409: Slot already booked or held
    - 404: Slot or session not found
    """
    htl_service = HTLService(db)
    return htl_service.reserve_slot(
        user=current_user,
        session_id=request.session_id,
        provider_id=request.provider_id,
        time_slot_id=request.time_slot_id
    )


@router.post(
    "/confirm",
    response_model=dict,
    summary="Confirm HTL - create booking",
    description="Convert active HTL reservation into confirmed booking"
)
def confirm_reservation(
    request: HTLConfirmRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Confirm HTL reservation and create booking.

    **Requirements:**
    - HTL must not be expired (within 5 minutes)
    - HTL must belong to current user
    - Slot must still be available

    **Returns:**
    ```json
    {
      "booking_id": 1,
      "booking_reference": "BK20240115-000001",
      "htl_id": 123,
      "status": "confirmed"
    }
    ```
    """
    htl_service = HTLService(db)
    return htl_service.confirm_reservation(
        user=current_user,
        htl_reservation_id=request.htl_reservation_id,
        special_instructions=request.special_instructions
    )


@router.delete(
    "/cancel/{htl_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel HTL reservation",
    description="Cancel hold and immediately free the time slot"
)
def cancel_reservation(
    htl_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Cancel HTL reservation.

    Immediately releases the slot for others to book.
    Only unconfirmed HTLs can be cancelled.
    """
    htl_service = HTLService(db)
    success = htl_service.cancel_reservation(current_user, htl_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTL reservation not found or already confirmed"
        )

    return {"message": "HTL cancelled", "htl_id": htl_id}


@router.get(
    "/active",
    response_model=HTLListResponse,
    summary="Get active HTL reservations",
    description="List all currently active (non-expired) HTL reservations"
)
def get_active_reservations(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Get user's active HTL reservations.

    Shows all slots currently held by the user with:
    - Time remaining before expiry
    - Provider and slot details
    - Confirmation status
    """
    htl_service = HTLService(db)
    reservations = htl_service.get_active_reservations(current_user)

    return HTLListResponse(
        active_reservations=reservations,
        total_count=len(reservations)
    )
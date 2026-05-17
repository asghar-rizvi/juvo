"""
Background tasks for Phase 4
- HTL expiration cleanup
- Notification sending
- Session cleanup
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import threading

from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Global flag to control background tasks
_tasks_running = False
_task_thread: Optional[threading.Thread] = None


# ============================================
# HTL Expiration Task
# ============================================

def expire_htl_reservations() -> int:
    """
    Expire overdue HTL reservations.
    Called periodically by background scheduler.

    Returns:
        Number of reservations expired
    """
    try:
        from src.database.connection import get_db_session
        from src.database.models import HTLReservation

        db = get_db_session()

        try:
            expired_htls = db.query(HTLReservation).filter(
                HTLReservation.is_confirmed == False,
                HTLReservation.is_expired == False,
                HTLReservation.expires_at < datetime.utcnow()
            ).all()

            count = len(expired_htls)

            for htl in expired_htls:
                htl.is_expired = True
                htl.expired_at = datetime.utcnow()
                logger.debug(
                    f"Expiring HTL {htl.id} "
                    f"(expired at {htl.expires_at})"
                )

            db.commit()

            if count > 0:
                logger.info(f"Background: Expired {count} HTL reservations")

            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Error expiring HTL reservations: {str(e)}")
            return 0

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Background task (HTL) failed: {str(e)}")
        return 0


# ============================================
# Chat Session Cleanup Task
# ============================================

def cleanup_inactive_sessions() -> int:
    """
    Mark old inactive chat sessions as completed.
    Sessions older than 24 hours without activity get cleaned up.

    Returns:
        Number of sessions cleaned
    """
    try:
        from src.database.connection import get_db_session
        from src.database.models import ChatSession

        db = get_db_session()

        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            stale_sessions = db.query(ChatSession).filter(
                ChatSession.is_active == True,
                ChatSession.last_message_at < cutoff_time
            ).all()

            count = len(stale_sessions)

            for session in stale_sessions:
                session.is_active = False
                session.completed_at = datetime.utcnow()

            db.commit()

            if count > 0:
                logger.info(f"Background: Cleaned {count} stale chat sessions")

            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning sessions: {str(e)}")
            return 0

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Background task (sessions) failed: {str(e)}")
        return 0


# ============================================
# Notification Task
# ============================================

def send_pending_notifications() -> int:
    """
    Process and send any pending notifications.
    Currently logs them — extend with SMS/push in Phase 5.

    Returns:
        Number of notifications processed
    """
    try:
        from src.database.connection import get_db_session
        from src.database.models import Notification

        db = get_db_session()

        try:
            # Get unread notifications older than 1 minute (batch process)
            cutoff = datetime.utcnow() - timedelta(minutes=1)

            pending = db.query(Notification).filter(
                Notification.is_read == False,
                Notification.created_at <= cutoff
            ).limit(settings.NOTIFICATION_BATCH_SIZE).all()

            count = len(pending)

            for notification in pending:
                # Log notification (Phase 5: send SMS/push here)
                logger.debug(
                    f"Notification [{notification.notification_type}]: "
                    f"{notification.title} -> "
                    f"user={notification.user_id}, "
                    f"provider={notification.provider_account_id}"
                )

            if count > 0:
                logger.info(f"Background: Processed {count} notifications")

            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Error processing notifications: {str(e)}")
            return 0

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Background task (notifications) failed: {str(e)}")
        return 0


# ============================================
# Main Background Loop
# ============================================

def _background_loop():
    """
    Main background task loop.
    Runs in a separate daemon thread.
    Executes tasks at their respective intervals.
    """
    logger.info("Background task loop started")

    # Track last run times
    last_htl_check = datetime.utcnow()
    last_session_cleanup = datetime.utcnow()
    last_notification_check = datetime.utcnow()

    # Intervals
    htl_interval = settings.HTL_CLEANUP_INTERVAL_SECONDS       # 60s default
    session_cleanup_interval = 3600                             # 1 hour
    notification_interval = 30                                  # 30s

    while _tasks_running:
        try:
            now = datetime.utcnow()

            # HTL expiration check
            if (now - last_htl_check).total_seconds() >= htl_interval:
                expire_htl_reservations()
                last_htl_check = now

            # Session cleanup
            if (now - last_session_cleanup).total_seconds() >= session_cleanup_interval:
                cleanup_inactive_sessions()
                last_session_cleanup = now

            # Notification processing
            if (now - last_notification_check).total_seconds() >= notification_interval:
                if settings.ENABLE_NOTIFICATIONS:
                    send_pending_notifications()
                last_notification_check = now

        except Exception as e:
            logger.error(f"Background loop error: {str(e)}", exc_info=True)

        # Sleep for 10 seconds between each loop iteration
        threading.Event().wait(10)


# ============================================
# Task Management
# ============================================

def start_background_tasks():
    """
    Start background task thread.
    Called from FastAPI startup event.
    """
    global _tasks_running, _task_thread

    if _tasks_running:
        logger.warning("Background tasks already running")
        return

    _tasks_running = True

    _task_thread = threading.Thread(
        target=_background_loop,
        daemon=True,    # Dies with main process
        name="BackgroundTaskThread"
    )
    _task_thread.start()

    logger.info(
        f"✓ Background tasks started "
        f"(HTL cleanup every {settings.HTL_CLEANUP_INTERVAL_SECONDS}s)"
    )


def stop_background_tasks():
    """
    Stop background task thread.
    Called from FastAPI shutdown event.
    """
    global _tasks_running, _task_thread

    _tasks_running = False

    if _task_thread and _task_thread.is_alive():
        _task_thread.join(timeout=5)
        logger.info("Background tasks stopped")


def get_task_status() -> dict:
    """Get current status of background tasks"""
    return {
        "running": _tasks_running,
        "thread_alive": _task_thread.is_alive() if _task_thread else False,
        "thread_name": _task_thread.name if _task_thread else None,
        "htl_cleanup_interval_seconds": settings.HTL_CLEANUP_INTERVAL_SECONDS,
        "notifications_enabled": settings.ENABLE_NOTIFICATIONS
    }
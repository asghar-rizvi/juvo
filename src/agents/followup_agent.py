from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from src.utils.gemini_client import get_gemini_client
from src.utils.logger import AgentLogger
from src.database.connection import get_db
from src.database.models import Booking, ConversationLog
from src.tools import DatabaseTools


class FollowUpAgent:
    """
    Agent responsible for automated follow-ups
    Schedules and sends reminders, status updates
    """
    
    def __init__(self):
        self.name = "FollowUpAgent"
        self.logger = AgentLogger(self.name)
        self.gemini = get_gemini_client()
        
        # Initialize scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        self.logger.log_workflow_step(
            "scheduler_init",
            "started",
            {"scheduler_running": self.scheduler.running}
        )
    
    def schedule_reminder(
        self,
        booking_id: int,
        session_id: str,
        hours_before: int = 1
    ) -> Dict[str, Any]:
        """
        Schedule a reminder before the appointment
        
        Args:
            booking_id: Booking ID
            session_id: Session identifier
            hours_before: Hours before appointment to send reminder
        
        Returns:
            Scheduling confirmation
        """
        try:
            with get_db() as db:
                booking = db.query(Booking).filter(
                    Booking.id == booking_id
                ).first()
                
                if not booking:
                    raise ValueError(f"Booking {booking_id} not found")
                
                # Calculate reminder time
                appointment_time = datetime.combine(
                    booking.time_slot.slot_date,
                    booking.time_slot.slot_time
                )
                reminder_time = appointment_time - timedelta(hours=hours_before)
                
                # Don't schedule if reminder time is in the past
                if reminder_time < datetime.now():
                    self.logger.log_workflow_step(
                        "schedule_reminder",
                        "skipped",
                        {"reason": "reminder_time_in_past"}
                    )
                    return {
                        'status': 'skipped',
                        'message': 'Reminder time is in the past'
                    }
                
                # Schedule job
                job = self.scheduler.add_job(
                    self._send_reminder,
                    trigger=DateTrigger(run_date=reminder_time),
                    args=[booking_id, session_id],
                    id=f'reminder_{booking_id}',
                    replace_existing=True
                )
                
                self.logger.log_decision(
                    {
                        "booking_id": booking_id,
                        "reminder_time": reminder_time.isoformat(),
                        "job_id": job.id
                    },
                    f"Scheduled reminder for {hours_before} hour(s) before appointment",
                    confidence=1.0
                )
                
                # Log to database
                tools = DatabaseTools(db)
                tools.log_conversation(
                    session_id=session_id,
                    agent_name=self.name,
                    agent_response=f"Reminder scheduled for {reminder_time.strftime('%Y-%m-%d %H:%M')}",
                    metadata={
                        "booking_id": booking_id,
                        "reminder_time": reminder_time.isoformat(),
                        "appointment_time": appointment_time.isoformat()
                    }
                )
            
            return {
                'status': 'scheduled',
                'reminder_time': reminder_time.isoformat(),
                'job_id': job.id
            }
            
        except Exception as e:
            self.logger.log_error(
                "schedule_reminder_error",
                str(e),
                {"booking_id": booking_id}
            )
            raise
    
    def _send_reminder(self, booking_id: int, session_id: str):
        """
        Send reminder message (called by scheduler)
        
        Args:
            booking_id: Booking ID
            session_id: Session identifier
        """
        try:
            with get_db() as db:
                booking = db.query(Booking).filter(
                    Booking.id == booking_id
                ).first()
                
                if not booking:
                    self.logger.log_error(
                        "booking_not_found",
                        f"Booking {booking_id} not found for reminder"
                    )
                    return
                
                # Get language from conversation log
                logs = db.query(ConversationLog).filter(
                    ConversationLog.session_id == session_id
                ).order_by(ConversationLog.created_at.desc()).limit(1).first()
                
                language = 'en'
                if logs and logs.user_input_language:
                    language = logs.user_input_language.value
                
                # Generate reminder message
                reminder_message = self.gemini.generate_user_message(
                    template="appointment_reminder",
                    language=language,
                    context={
                        "booking_reference": booking.booking_reference,
                        "provider_name": booking.provider.name,
                        "service_type": booking.service_category.name_en,
                        "appointment_time": booking.time_slot.slot_time.strftime('%I:%M %p'),
                        "appointment_date": booking.time_slot.slot_date.strftime('%A, %B %d'),
                        "provider_phone": booking.provider.phone,
                        "address": booking.address_requested
                    }
                )
                
                # Log reminder sent
                tools = DatabaseTools(db)
                tools.log_conversation(
                    session_id=session_id,
                    agent_name=self.name,
                    agent_response=reminder_message,
                    metadata={
                        "type": "reminder",
                        "booking_id": booking_id,
                        "sent_at": datetime.now().isoformat()
                    }
                )
                
                self.logger.log_workflow_step(
                    "send_reminder",
                    "completed",
                    {
                        "booking_id": booking_id,
                        "booking_reference": booking.booking_reference
                    }
                )
                
                # In production: Send via WhatsApp API
                print(f"\n{'='*60}")
                print(f"📱 REMINDER SENT (Booking: {booking.booking_reference})")
                print(f"{'='*60}")
                print(reminder_message)
                print(f"{'='*60}\n")
                
        except Exception as e:
            self.logger.log_error(
                "send_reminder_error",
                str(e),
                {"booking_id": booking_id}
            )
    
    def shutdown(self):
        """Shutdown scheduler gracefully"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.logger.log_workflow_step(
                "scheduler_shutdown",
                "completed",
                {}
            )
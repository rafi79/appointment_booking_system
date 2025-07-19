from celery import Celery
from celery.schedules import crontab
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.config import settings
from app.database import SessionLocal
from app.services.appointment_service import AppointmentService
from app.services.email_service import EmailService
from app.models.appointment import Appointment, AppointmentStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "appointment_scheduler",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Dhaka",
    enable_utc=True,
    beat_schedule={
        "send-daily-reminders": {
            "task": "app.core.scheduler.send_appointment_reminders",
            "schedule": crontab(hour=9, minute=0),  # Run daily at 9 AM
        },
        "generate-monthly-reports": {
            "task": "app.core.scheduler.generate_monthly_reports",
            "schedule": crontab(0, 0, day_of_month=1),  # Run on 1st day of month at midnight
        },
    },
)


def get_db():
    """Get database session for background tasks"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


@celery_app.task
def send_appointment_reminders():
    """
    Send appointment reminders for appointments scheduled for tomorrow
    """
    logger.info("Starting appointment reminder task")
    
    try:
        db = SessionLocal()
        appointment_service = AppointmentService(db)
        email_service = EmailService()
        
        # Get appointments for tomorrow that need reminders
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        
        appointments = db.query(Appointment).filter(
            Appointment.appointment_date == tomorrow,
            Appointment.status == AppointmentStatus.CONFIRMED
        ).all()
        
        logger.info(f"Found {len(appointments)} appointments for tomorrow")
        
        sent_count = 0
        failed_count = 0
        
        for appointment in appointments:
            try:
                success = email_service.send_appointment_reminder(appointment)
                if success:
                    sent_count += 1
                    logger.info(f"Reminder sent for appointment {appointment.id}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to send reminder for appointment {appointment.id}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending reminder for appointment {appointment.id}: {e}")
        
        logger.info(f"Reminder task completed. Sent: {sent_count}, Failed: {failed_count}")
        
        db.close()
        
        return {
            "total_appointments": len(appointments),
            "sent": sent_count,
            "failed": failed_count,
            "date": tomorrow.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in appointment reminder task: {e}")
        raise


@celery_app.task
def generate_monthly_reports():
    """
    Generate monthly reports for all doctors
    """
    logger.info("Starting monthly report generation task")
    
    try:
        from sqlalchemy import func, and_
        from app.models.doctor import Doctor
        from app.models.user import User
        from calendar import monthrange
        
        db = SessionLocal()
        
        # Get previous month
        now = datetime.now()
        if now.month == 1:
            report_year = now.year - 1
            report_month = 12
        else:
            report_year = now.year
            report_month = now.month - 1
        
        # Get the start and end dates for the month
        start_date = datetime(report_year, report_month, 1).date()
        _, last_day = monthrange(report_year, report_month)
        end_date = datetime(report_year, report_month, last_day).date()
        
        logger.info(f"Generating reports for {report_year}-{report_month:02d}")
        
        # Query to get doctor statistics for the month
        doctor_stats = db.query(
            Doctor.id,
            Doctor.user_id,
            Doctor.specialization,
            func.count(Appointment.id).label('total_appointments'),
            func.count(func.distinct(Appointment.patient_id)).label('total_patients'),
            func.sum(
                func.case(
                    (Appointment.status == AppointmentStatus.COMPLETED, Doctor.consultation_fee),
                    else_=0
                )
            ).label('total_earnings'),
            func.count(
                func.case(
                    (Appointment.status == AppointmentStatus.COMPLETED, 1),
                    else_=None
                )
            ).label('completed_appointments'),
            func.count(
                func.case(
                    (Appointment.status == AppointmentStatus.CANCELLED, 1),
                    else_=None
                )
            ).label('cancelled_appointments')
        ).join(
            Appointment, Doctor.id == Appointment.doctor_id
        ).join(
            User, Doctor.user_id == User.id
        ).filter(
            and_(
                Appointment.appointment_date >= start_date,
                Appointment.appointment_date <= end_date
            )
        ).group_by(
            Doctor.id, Doctor.user_id, Doctor.specialization
        ).all()
        
        # Store reports (you can save to database, file, or send via email)
        reports = []
        for stat in doctor_stats:
            doctor_user = db.query(User).filter(User.id == stat.user_id).first()
            
            report = {
                "doctor_id": stat.id,
                "doctor_name": doctor_user.full_name,
                "specialization": stat.specialization,
                "month": report_month,
                "year": report_year,
                "total_patients": stat.total_patients,
                "total_appointments": stat.total_appointments,
                "total_earnings": float(stat.total_earnings or 0),
                "completed_appointments": stat.completed_appointments,
                "cancelled_appointments": stat.cancelled_appointments
            }
            
            reports.append(report)
            logger.info(f"Generated report for Dr. {doctor_user.full_name}")
        
        # You can save these reports to a database table or send via email
        # For now, we'll just log the summary
        total_revenue = sum(report["total_earnings"] for report in reports)
        total_appointments = sum(report["total_appointments"] for report in reports)
        
        logger.info(f"Monthly report summary - Total doctors: {len(reports)}, "
                   f"Total appointments: {total_appointments}, Total revenue: {total_revenue}")
        
        db.close()
        
        return {
            "month": report_month,
            "year": report_year,
            "total_doctors": len(reports),
            "total_appointments": total_appointments,
            "total_revenue": total_revenue,
            "reports_generated": len(reports)
        }
        
    except Exception as e:
        logger.error(f"Error in monthly report generation task: {e}")
        raise


@celery_app.task
def send_appointment_confirmation_email(appointment_id: int):
    """
    Send appointment confirmation email (called after appointment creation)
    """
    try:
        db = SessionLocal()
        email_service = EmailService()
        
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appointment:
            success = email_service.send_appointment_confirmation(appointment)
            if success:
                logger.info(f"Confirmation email sent for appointment {appointment_id}")
            else:
                logger.error(f"Failed to send confirmation email for appointment {appointment_id}")
        
        db.close()
        return success
        
    except Exception as e:
        logger.error(f"Error sending confirmation email for appointment {appointment_id}: {e}")
        raise


@celery_app.task
def send_doctor_notification_email(appointment_id: int):
    """
    Send new appointment notification to doctor
    """
    try:
        db = SessionLocal()
        email_service = EmailService()
        
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appointment:
            success = email_service.send_doctor_new_appointment_notification(appointment)
            if success:
                logger.info(f"Doctor notification sent for appointment {appointment_id}")
            else:
                logger.error(f"Failed to send doctor notification for appointment {appointment_id}")
        
        db.close()
        return success
        
    except Exception as e:
        logger.error(f"Error sending doctor notification for appointment {appointment_id}: {e}")
        raise


@celery_app.task
def send_welcome_email_task(user_id: int):
    """
    Send welcome email to new user
    """
    try:
        db = SessionLocal()
        email_service = EmailService()
        
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            success = email_service.send_welcome_email(user)
            if success:
                logger.info(f"Welcome email sent to user {user_id}")
            else:
                logger.error(f"Failed to send welcome email to user {user_id}")
        
        db.close()
        return success
        
    except Exception as e:
        logger.error(f"Error sending welcome email to user {user_id}: {e}")
        raise


if __name__ == "__main__":
    # For testing individual tasks
    result = send_appointment_reminders.delay()
    print(f"Task result: {result.get()}")
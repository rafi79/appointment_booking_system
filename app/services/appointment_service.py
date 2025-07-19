from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime, date
from fastapi import HTTPException, status

from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentStatusUpdate


class AppointmentService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_appointment_by_id(self, appointment_id: int) -> Optional[Appointment]:
        """Get appointment by ID with related data"""
        return self.db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        ).filter(Appointment.id == appointment_id).first()
    
    def create_appointment(self, appointment_data: AppointmentCreate, patient_id: int) -> Appointment:
        """Create a new appointment"""
        
        # Check if doctor exists and is active
        doctor = self.db.query(Doctor).join(User).filter(
            Doctor.id == appointment_data.doctor_id,
            User.is_active == True
        ).first()
        
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found or inactive"
            )
        
        # Check if the requested time slot is available for the doctor
        appointment_day = appointment_data.appointment_date.strftime('%A').lower()
        available_slots = doctor.available_timeslots.get(appointment_day, [])
        
        if appointment_data.appointment_time not in available_slots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Doctor is not available at {appointment_data.appointment_time} on {appointment_day.title()}"
            )
        
        # Check for conflicting appointments
        existing_appointment = self._check_time_slot_conflict(
            appointment_data.doctor_id,
            appointment_data.appointment_date,
            appointment_data.appointment_time
        )
        
        if existing_appointment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This time slot is already booked"
            )
        
        try:
            # Create appointment
            db_appointment = Appointment(
                patient_id=patient_id,
                doctor_id=appointment_data.doctor_id,
                appointment_date=appointment_data.appointment_date,
                appointment_time=appointment_data.appointment_time,
                notes=appointment_data.notes,
                symptoms=appointment_data.symptoms
            )
            
            self.db.add(db_appointment)
            self.db.commit()
            self.db.refresh(db_appointment)
            
            # Load related data
            appointment = self.get_appointment_by_id(db_appointment.id)
            return appointment
            
        except Exception as e:
            self.db.rollback()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create appointment"
            )
    
    def update_appointment(
        self,
        appointment_id: int,
        appointment_update: AppointmentUpdate,
        user_id: int
    ) -> Appointment:
        """Update appointment (Patient only, before confirmation)"""
        
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == user_id
        ).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        if appointment.status != AppointmentStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending appointments can be updated"
            )
        
        try:
            # Check availability for new date/time if being updated
            if appointment_update.appointment_date or appointment_update.appointment_time:
                doctor = self.db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
                new_date = appointment_update.appointment_date or appointment.appointment_date
                new_time = appointment_update.appointment_time or appointment.appointment_time
                
                # Check if new time slot is available
                appointment_day = new_date.strftime('%A').lower()
                available_slots = doctor.available_timeslots.get(appointment_day, [])
                
                if new_time not in available_slots:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Doctor is not available at {new_time} on {appointment_day.title()}"
                    )
                
                # Check for conflicts (excluding current appointment)
                existing_appointment = self._check_time_slot_conflict(
                    appointment.doctor_id, new_date, new_time, exclude_appointment_id=appointment_id
                )
                
                if existing_appointment:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="This time slot is already booked"
                    )
            
            # Update appointment fields
            for field, value in appointment_update.dict(exclude_unset=True).items():
                setattr(appointment, field, value)
            
            self.db.commit()
            self.db.refresh(appointment)
            
            # Load related data
            appointment = self.get_appointment_by_id(appointment_id)
            return appointment
            
        except Exception as e:
            self.db.rollback()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update appointment"
            )
    
    def update_appointment_status(
        self,
        appointment_id: int,
        status_update: AppointmentStatusUpdate,
        current_user: User
    ) -> Appointment:
        """Update appointment status (Doctor/Admin only)"""
        
        appointment = self.db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        # Check permissions for doctors
        if current_user.user_type == UserType.DOCTOR:
            doctor = self.db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
            if not doctor or appointment.doctor_id != doctor.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        try:
            # Update appointment
            appointment.status = status_update.status
            if status_update.doctor_notes:
                appointment.doctor_notes = status_update.doctor_notes
            if status_update.prescription:
                appointment.prescription = status_update.prescription
            
            self.db.commit()
            self.db.refresh(appointment)
            
            # Load related data
            appointment = self.get_appointment_by_id(appointment_id)
            return appointment
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update appointment status"
            )
    
    def cancel_appointment(self, appointment_id: int, current_user: User) -> bool:
        """Cancel appointment"""
        
        appointment = self.db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        # Check permissions
        can_cancel = False
        if current_user.user_type == UserType.PATIENT and appointment.patient_id == current_user.id:
            can_cancel = True
        elif current_user.user_type == UserType.DOCTOR:
            doctor = self.db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
            if doctor and appointment.doctor_id == doctor.id:
                can_cancel = True
        elif current_user.user_type == UserType.ADMIN:
            can_cancel = True
        
        if not can_cancel:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel completed or already cancelled appointment"
            )
        
        try:
            appointment.status = AppointmentStatus.CANCELLED
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel appointment"
            )
    
    def get_appointments_for_user(
        self,
        user: User,
        skip: int = 0,
        limit: int = 20,
        status: Optional[AppointmentStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Appointment]:
        """Get appointments based on user type"""
        
        query = self.db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        )
        
        # Filter based on user type
        if user.user_type == UserType.PATIENT:
            query = query.filter(Appointment.patient_id == user.id)
        elif user.user_type == UserType.DOCTOR:
            doctor = self.db.query(Doctor).filter(Doctor.user_id == user.id).first()
            if doctor:
                query = query.filter(Appointment.doctor_id == doctor.id)
            else:
                return []
        elif user.user_type == UserType.ADMIN:
            pass  # Admin can see all appointments
        
        # Apply filters
        if status:
            query = query.filter(Appointment.status == status)
        
        if date_from:
            query = query.filter(Appointment.appointment_date >= date_from)
        
        if date_to:
            query = query.filter(Appointment.appointment_date <= date_to)
        
        return query.order_by(Appointment.appointment_date.desc()).offset(skip).limit(limit).all()
    
    def get_doctor_available_slots(self, doctor_id: int, appointment_date: date) -> List[str]:
        """Get available time slots for a doctor on a specific date"""
        
        doctor = self.db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found"
            )
        
        # Get day of week
        appointment_day = appointment_date.strftime('%A').lower()
        all_slots = doctor.available_timeslots.get(appointment_day, [])
        
        # Get booked slots for the date
        booked_appointments = self.db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
        ).all()
        
        booked_slots = [apt.appointment_time for apt in booked_appointments]
        
        # Return available slots
        available_slots = [slot for slot in all_slots if slot not in booked_slots]
        
        return available_slots
    
    def get_upcoming_appointments(self, user: User, days: int = 7) -> List[Appointment]:
        """Get upcoming appointments for a user"""
        
        from datetime import timedelta
        today = datetime.now().date()
        end_date = today + timedelta(days=days)
        
        return self.get_appointments_for_user(
            user=user,
            date_from=today,
            date_to=end_date,
            status=AppointmentStatus.CONFIRMED
        )
    
    def get_appointments_requiring_reminder(self, hours_ahead: int = 24) -> List[Appointment]:
        """Get appointments that need reminders (for background tasks)"""
        
        from datetime import timedelta
        reminder_time = datetime.now() + timedelta(hours=hours_ahead)
        reminder_date = reminder_time.date()
        
        return self.db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        ).filter(
            Appointment.appointment_date == reminder_date,
            Appointment.status == AppointmentStatus.CONFIRMED
        ).all()
    
    def _check_time_slot_conflict(
        self,
        doctor_id: int,
        appointment_date: date,
        appointment_time: str,
        exclude_appointment_id: Optional[int] = None
    ) -> Optional[Appointment]:
        """Check if a time slot is already booked"""
        
        query = self.db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
        )
        
        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)
        
        return query.first()
    
    def get_appointment_statistics(self, user: User) -> dict:
        """Get appointment statistics for a user"""
        
        from sqlalchemy import func
        
        base_query = self.db.query(Appointment)
        
        # Filter based on user type
        if user.user_type == UserType.PATIENT:
            base_query = base_query.filter(Appointment.patient_id == user.id)
        elif user.user_type == UserType.DOCTOR:
            doctor = self.db.query(Doctor).filter(Doctor.user_id == user.id).first()
            if doctor:
                base_query = base_query.filter(Appointment.doctor_id == doctor.id)
            else:
                return {
                    "total_appointments": 0,
                    "pending_appointments": 0,
                    "confirmed_appointments": 0,
                    "completed_appointments": 0,
                    "cancelled_appointments": 0,
                    "today_appointments": 0,
                    "this_month_appointments": 0
                }
        
        total_appointments = base_query.count()
        pending = base_query.filter(Appointment.status == AppointmentStatus.PENDING).count()
        confirmed = base_query.filter(Appointment.status == AppointmentStatus.CONFIRMED).count()
        completed = base_query.filter(Appointment.status == AppointmentStatus.COMPLETED).count()
        cancelled = base_query.filter(Appointment.status == AppointmentStatus.CANCELLED).count()
        
        today = datetime.now().date()
        today_appointments = base_query.filter(Appointment.appointment_date == today).count()
        
        current_month_start = today.replace(day=1)
        this_month = base_query.filter(Appointment.appointment_date >= current_month_start).count()
        
        return {
            "total_appointments": total_appointments,
            "pending_appointments": pending,
            "confirmed_appointments": confirmed,
            "completed_appointments": completed,
            "cancelled_appointments": cancelled,
            "today_appointments": today_appointments,
            "this_month_appointments": this_month
        }
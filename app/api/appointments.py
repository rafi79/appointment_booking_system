from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, date

from app.database import get_db
from app.core.dependencies import (
    get_current_user, get_current_doctor, get_current_patient,
    get_current_admin, get_current_doctor_or_admin
)
from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentResponse,
    AppointmentStatusUpdate, AppointmentSearch, AppointmentStats
)

router = APIRouter()


@router.post("/", response_model=AppointmentResponse)
async def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    """
    Create a new appointment (Patient only)
    """
    try:
        # Check if doctor exists and is active
        doctor = db.query(Doctor).join(User).filter(
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
        existing_appointment = db.query(Appointment).filter(
            Appointment.doctor_id == appointment_data.doctor_id,
            Appointment.appointment_date == appointment_data.appointment_date,
            Appointment.appointment_time == appointment_data.appointment_time,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
        ).first()
        
        if existing_appointment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This time slot is already booked"
            )
        
        # Create appointment
        db_appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=appointment_data.doctor_id,
            appointment_date=appointment_data.appointment_date,
            appointment_time=appointment_data.appointment_time,
            notes=appointment_data.notes,
            symptoms=appointment_data.symptoms
        )
        
        db.add(db_appointment)
        db.commit()
        db.refresh(db_appointment)
        
        # Load related data for response
        appointment = db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        ).filter(Appointment.id == db_appointment.id).first()
        
        return _format_appointment_response(appointment)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating appointment: {str(e)}"
        )


@router.get("/", response_model=List[AppointmentResponse])
async def get_appointments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    status: Optional[AppointmentStatus] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get appointments based on user type
    """
    try:
        query = db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        )
        
        # Filter based on user type
        if current_user.user_type == UserType.PATIENT:
            query = query.filter(Appointment.patient_id == current_user.id)
        elif current_user.user_type == UserType.DOCTOR:
            doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
            if doctor:
                query = query.filter(Appointment.doctor_id == doctor.id)
            else:
                return []
        elif current_user.user_type == UserType.ADMIN:
            pass  # Admin can see all appointments
        
        # Apply filters
        if status:
            query = query.filter(Appointment.status == status)
        
        if date_from:
            query = query.filter(Appointment.appointment_date >= date_from)
        
        if date_to:
            query = query.filter(Appointment.appointment_date <= date_to)
        
        appointments = query.order_by(Appointment.appointment_date.desc()).offset(skip).limit(limit).all()
        
        return [_format_appointment_response(apt) for apt in appointments]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointments: {str(e)}"
        )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get appointment by ID
    """
    try:
        appointment = db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        ).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        # Check permissions
        if current_user.user_type == UserType.PATIENT:
            if appointment.patient_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        elif current_user.user_type == UserType.DOCTOR:
            doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
            if not doctor or appointment.doctor_id != doctor.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        return _format_appointment_response(appointment)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointment: {str(e)}"
        )


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    current_user: User = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    """
    Update appointment (Patient only, before confirmation)
    """
    try:
        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == current_user.id
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
        
        # Update appointment fields
        for field, value in appointment_update.dict(exclude_unset=True).items():
            if field in ['appointment_date', 'appointment_time'] and value:
                # Check availability for new date/time
                doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
                new_date = value if field == 'appointment_date' else appointment.appointment_date
                new_time = value if field == 'appointment_time' else appointment.appointment_time
                
                appointment_day = new_date.strftime('%A').lower()
                available_slots = doctor.available_timeslots.get(appointment_day, [])
                
                if new_time not in available_slots:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Doctor is not available at {new_time} on {appointment_day.title()}"
                    )
                
                # Check for conflicts
                existing_appointment = db.query(Appointment).filter(
                    Appointment.doctor_id == appointment.doctor_id,
                    Appointment.appointment_date == new_date,
                    Appointment.appointment_time == new_time,
                    Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
                    Appointment.id != appointment_id
                ).first()
                
                if existing_appointment:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="This time slot is already booked"
                    )
            
            setattr(appointment, field, value)
        
        db.commit()
        db.refresh(appointment)
        
        # Load related data for response
        appointment = db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        ).filter(Appointment.id == appointment_id).first()
        
        return _format_appointment_response(appointment)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating appointment: {str(e)}"
        )


@router.put("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: int,
    status_update: AppointmentStatusUpdate,
    current_user: User = Depends(get_current_doctor_or_admin),
    db: Session = Depends(get_db)
):
    """
    Update appointment status (Doctor/Admin only)
    """
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        # Check permissions for doctors
        if current_user.user_type == UserType.DOCTOR:
            doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
            if not doctor or appointment.doctor_id != doctor.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        # Update appointment
        appointment.status = status_update.status
        if status_update.doctor_notes:
            appointment.doctor_notes = status_update.doctor_notes
        if status_update.prescription:
            appointment.prescription = status_update.prescription
        
        db.commit()
        db.refresh(appointment)
        
        # Load related data for response
        appointment = db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        ).filter(Appointment.id == appointment_id).first()
        
        return _format_appointment_response(appointment)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating appointment status: {str(e)}"
        )


@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel appointment
    """
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
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
            doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
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
        
        appointment.status = AppointmentStatus.CANCELLED
        db.commit()
        
        return {"message": "Appointment cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling appointment: {str(e)}"
        )


@router.get("/stats/overview", response_model=AppointmentStats)
async def get_appointment_stats(
    current_user: User = Depends(get_current_doctor_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get appointment statistics
    """
    try:
        query = db.query(Appointment)
        
        # Filter for doctors
        if current_user.user_type == UserType.DOCTOR:
            doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
            if doctor:
                query = query.filter(Appointment.doctor_id == doctor.id)
            else:
                return AppointmentStats(
                    total_appointments=0, pending_appointments=0,
                    confirmed_appointments=0, completed_appointments=0,
                    cancelled_appointments=0, today_appointments=0,
                    this_month_appointments=0
                )
        
        total_appointments = query.count()
        pending = query.filter(Appointment.status == AppointmentStatus.PENDING).count()
        confirmed = query.filter(Appointment.status == AppointmentStatus.CONFIRMED).count()
        completed = query.filter(Appointment.status == AppointmentStatus.COMPLETED).count()
        cancelled = query.filter(Appointment.status == AppointmentStatus.CANCELLED).count()
        
        today = datetime.now().date()
        today_appointments = query.filter(Appointment.appointment_date == today).count()
        
        current_month_start = today.replace(day=1)
        this_month = query.filter(Appointment.appointment_date >= current_month_start).count()
        
        return AppointmentStats(
            total_appointments=total_appointments,
            pending_appointments=pending,
            confirmed_appointments=confirmed,
            completed_appointments=completed,
            cancelled_appointments=cancelled,
            today_appointments=today_appointments,
            this_month_appointments=this_month
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointment stats: {str(e)}"
        )


def _format_appointment_response(appointment: Appointment) -> AppointmentResponse:
    """
    Format appointment for response
    """
    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        status=appointment.status,
        notes=appointment.notes,
        symptoms=appointment.symptoms,
        doctor_notes=appointment.doctor_notes,
        prescription=appointment.prescription,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
        patient_name=appointment.patient.full_name,
        patient_mobile=appointment.patient.mobile_number,
        doctor_name=appointment.doctor.user.full_name,
        doctor_specialization=appointment.doctor.specialization,
        consultation_fee=appointment.doctor.consultation_fee
    )
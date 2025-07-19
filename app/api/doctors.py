from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_doctor, get_current_admin
from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.schemas.doctor import DoctorResponse, DoctorUpdate, DoctorPublic, DoctorSearch

router = APIRouter()


@router.get("/", response_model=List[DoctorPublic])
async def get_doctors(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    specialization: Optional[str] = None,
    division_id: Optional[int] = None,
    district_id: Optional[int] = None,
    min_fee: Optional[float] = None,
    max_fee: Optional[float] = None,
    available_day: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all doctors with filters
    """
    try:
        query = db.query(Doctor).options(
            joinedload(Doctor.user).joinedload(User.division),
            joinedload(Doctor.user).joinedload(User.district),
            joinedload(Doctor.user).joinedload(User.thana)
        ).join(User).filter(User.is_active == True)
        
        # Apply filters
        if specialization:
            query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
        
        if division_id:
            query = query.filter(User.division_id == division_id)
        
        if district_id:
            query = query.filter(User.district_id == district_id)
        
        if min_fee:
            query = query.filter(Doctor.consultation_fee >= min_fee)
        
        if max_fee:
            query = query.filter(Doctor.consultation_fee <= max_fee)
        
        if available_day:
            # Check if the doctor has available timeslots for the specified day
            query = query.filter(Doctor.available_timeslots.op('?')(available_day.lower()))
        
        doctors = query.offset(skip).limit(limit).all()
        
        return [
            DoctorPublic(
                id=doctor.id,
                full_name=doctor.user.full_name,
                specialization=doctor.specialization,
                experience_years=doctor.experience_years,
                consultation_fee=doctor.consultation_fee,
                qualification=doctor.qualification,
                bio=doctor.bio,
                available_timeslots=doctor.available_timeslots,
                division_name=doctor.user.division.name if doctor.user.division else "",
                district_name=doctor.user.district.name if doctor.user.district else "",
                thana_name=doctor.user.thana.name if doctor.user.thana else "",
                profile_image=doctor.user.profile_image
            )
            for doctor in doctors
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching doctors: {str(e)}"
        )


@router.get("/search", response_model=List[DoctorPublic])
async def search_doctors(
    query: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    Search doctors by name or specialization
    """
    try:
        doctors = db.query(Doctor).options(
            joinedload(Doctor.user).joinedload(User.division),
            joinedload(Doctor.user).joinedload(User.district),
            joinedload(Doctor.user).joinedload(User.thana)
        ).join(User).filter(
            (User.full_name.ilike(f"%{query}%")) |
            (Doctor.specialization.ilike(f"%{query}%")),
            User.is_active == True
        ).offset(skip).limit(limit).all()
        
        return [
            DoctorPublic(
                id=doctor.id,
                full_name=doctor.user.full_name,
                specialization=doctor.specialization,
                experience_years=doctor.experience_years,
                consultation_fee=doctor.consultation_fee,
                qualification=doctor.qualification,
                bio=doctor.bio,
                available_timeslots=doctor.available_timeslots,
                division_name=doctor.user.division.name if doctor.user.division else "",
                district_name=doctor.user.district.name if doctor.user.district else "",
                thana_name=doctor.user.thana.name if doctor.user.thana else "",
                profile_image=doctor.user.profile_image
            )
            for doctor in doctors
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching doctors: {str(e)}"
        )


@router.get("/{doctor_id}", response_model=DoctorPublic)
async def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    """
    Get doctor by ID
    """
    try:
        doctor = db.query(Doctor).options(
            joinedload(Doctor.user).joinedload(User.division),
            joinedload(Doctor.user).joinedload(User.district),
            joinedload(Doctor.user).joinedload(User.thana)
        ).filter(Doctor.id == doctor_id).first()
        
        if not doctor or not doctor.user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found"
            )
        
        return DoctorPublic(
            id=doctor.id,
            full_name=doctor.user.full_name,
            specialization=doctor.specialization,
            experience_years=doctor.experience_years,
            consultation_fee=doctor.consultation_fee,
            qualification=doctor.qualification,
            bio=doctor.bio,
            available_timeslots=doctor.available_timeslots,
            division_name=doctor.user.division.name if doctor.user.division else "",
            district_name=doctor.user.district.name if doctor.user.district else "",
            thana_name=doctor.user.thana.name if doctor.user.thana else "",
            profile_image=doctor.user.profile_image
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching doctor: {str(e)}"
        )


@router.get("/specializations/list")
async def get_specializations(db: Session = Depends(get_db)):
    """
    Get list of all specializations with proper format
    """
    try:
        specializations = db.query(Doctor.specialization).distinct().all()
        return [{"value": spec[0], "label": spec[0]} for spec in specializations if spec[0]]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching specializations: {str(e)}"
        )


@router.get("/me/profile", response_model=DoctorResponse)
async def get_my_doctor_profile(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Get current doctor's profile
    """
    try:
        doctor = db.query(Doctor).options(
            joinedload(Doctor.user)
        ).filter(Doctor.id == current_doctor.id).first()
        
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found"
            )
        
        return doctor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching doctor profile: {str(e)}"
        )


@router.put("/me/profile", response_model=DoctorResponse)
async def update_my_doctor_profile(
    doctor_update: DoctorUpdate,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Update current doctor's profile
    """
    try:
        # Update doctor fields
        for field, value in doctor_update.dict(exclude_unset=True).items():
            if hasattr(current_doctor, field):
                setattr(current_doctor, field, value)
        
        db.commit()
        db.refresh(current_doctor)
        
        return current_doctor
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating doctor profile: {str(e)}"
        )


@router.get("/me/schedule")
async def get_my_schedule(
    current_doctor: Doctor = Depends(get_current_doctor)
):
    """
    Get current doctor's schedule
    """
    try:
        return {
            "doctor_id": current_doctor.id,
            "available_timeslots": current_doctor.available_timeslots or {}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching schedule: {str(e)}"
        )


@router.put("/me/schedule")
async def update_my_schedule(
    request: Request,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Update current doctor's schedule - handles various input formats
    """
    try:
        # Get request body
        request_body = await request.json()
        
        # Debug logging
        print(f"DEBUG: Received schedule data: {request_body}")
        
        # Handle different input formats
        available_timeslots = None
        
        # Case 1: Standard format with 'available_timeslots' key
        if 'available_timeslots' in request_body:
            available_timeslots = request_body['available_timeslots']
        
        # Case 2: Direct timeslots object (all keys are days)
        elif all(key.lower() in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] 
                for key in request_body.keys()):
            available_timeslots = request_body
        
        # Case 3: Filter out non-day keys and extract only day data
        else:
            valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            day_data = {}
            
            for key, value in request_body.items():
                if key.lower() in valid_days:
                    day_data[key.lower()] = value
            
            if day_data:
                available_timeslots = day_data
            else:
                # Log the problematic data for debugging
                print(f"ERROR: No valid day data found in request: {request_body}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request format. Expected schedule data with day keys. Received: {list(request_body.keys())}"
                )
        
        if not available_timeslots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid schedule data provided"
            )
        
        # Validate and clean the timeslots
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        cleaned_timeslots = {}
        
        for day, timeslots in available_timeslots.items():
            day_lower = day.lower().strip()
            
            if day_lower not in valid_days:
                print(f"WARNING: Skipping invalid day: {day}")
                continue
            
            if not isinstance(timeslots, list):
                if isinstance(timeslots, str):
                    # Convert single string to list
                    timeslots = [timeslots] if timeslots.strip() else []
                else:
                    print(f"WARNING: Invalid timeslots format for {day}: {timeslots}")
                    continue
            
            # Validate each timeslot
            valid_slots = []
            for slot in timeslots:
                if not isinstance(slot, str):
                    continue
                
                slot = slot.strip()
                if not slot:
                    continue
                
                # Basic validation - should contain : and -
                if ':' in slot and '-' in slot:
                    try:
                        start_time, end_time = slot.split('-', 1)
                        start_parts = start_time.strip().split(':')
                        end_parts = end_time.strip().split(':')
                        
                        if len(start_parts) == 2 and len(end_parts) == 2:
                            start_hour, start_min = int(start_parts[0]), int(start_parts[1])
                            end_hour, end_min = int(end_parts[0]), int(end_parts[1])
                            
                            # Validate ranges
                            if (0 <= start_hour <= 23 and 0 <= start_min <= 59 and
                                0 <= end_hour <= 23 and 0 <= end_min <= 59):
                                valid_slots.append(slot)
                                continue
                    except (ValueError, IndexError):
                        pass
                
                print(f"WARNING: Invalid timeslot format: {slot}")
            
            cleaned_timeslots[day_lower] = valid_slots
        
        # Update the doctor's schedule
        current_doctor.available_timeslots = cleaned_timeslots
        db.commit()
        
        print(f"SUCCESS: Updated schedule for doctor {current_doctor.id}: {cleaned_timeslots}")
        
        return {
            "success": True,
            "message": "Schedule updated successfully",
            "available_timeslots": current_doctor.available_timeslots
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"ERROR: Schedule update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating schedule: {str(e)}"
        )


@router.get("/me/appointments")
async def get_my_appointments(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Get current doctor's appointments
    """
    try:
        from app.models.appointment import Appointment
        
        appointments = db.query(Appointment).options(
            joinedload(Appointment.patient)
        ).filter(
            Appointment.doctor_id == current_doctor.id
        ).order_by(Appointment.appointment_date.desc()).all()
        
        return [
            {
                "id": apt.id,
                "patient_name": apt.patient.full_name,
                "patient_mobile": apt.patient.mobile_number,
                "appointment_date": apt.appointment_date,
                "appointment_time": apt.appointment_time,
                "status": apt.status,
                "notes": apt.notes,
                "symptoms": apt.symptoms,
                "doctor_notes": apt.doctor_notes,
                "prescription": apt.prescription
            }
            for apt in appointments
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointments: {str(e)}"
        )


@router.get("/me/stats")
async def get_my_stats(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Get current doctor's statistics
    """
    try:
        from app.models.appointment import Appointment, AppointmentStatus
        from datetime import datetime, date
        
        # Total appointments
        total_appointments = db.query(Appointment).filter(
            Appointment.doctor_id == current_doctor.id
        ).count()
        
        # Appointments by status
        pending = db.query(Appointment).filter(
            Appointment.doctor_id == current_doctor.id,
            Appointment.status == AppointmentStatus.PENDING
        ).count()
        
        confirmed = db.query(Appointment).filter(
            Appointment.doctor_id == current_doctor.id,
            Appointment.status == AppointmentStatus.CONFIRMED
        ).count()
        
        completed = db.query(Appointment).filter(
            Appointment.doctor_id == current_doctor.id,
            Appointment.status == AppointmentStatus.COMPLETED
        ).count()
        
        # Today's appointments
        today = date.today()
        today_appointments = db.query(Appointment).filter(
            Appointment.doctor_id == current_doctor.id,
            Appointment.appointment_date == today
        ).count()
        
        # This month's revenue
        current_month_start = today.replace(day=1)
        this_month_completed = db.query(Appointment).filter(
            Appointment.doctor_id == current_doctor.id,
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.appointment_date >= current_month_start
        ).count()
        
        this_month_revenue = this_month_completed * current_doctor.consultation_fee
        
        return {
            "total_appointments": total_appointments,
            "pending_appointments": pending,
            "confirmed_appointments": confirmed,
            "completed_appointments": completed,
            "today_appointments": today_appointments,
            "this_month_revenue": float(this_month_revenue),
            "consultation_fee": current_doctor.consultation_fee
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stats: {str(e)}"
        )


@router.get("/admin/all", response_model=List[DoctorResponse])
async def get_all_doctors_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all doctors (Admin only)
    """
    try:
        doctors = db.query(Doctor).options(
            joinedload(Doctor.user)
        ).offset(skip).limit(limit).all()
        
        return doctors
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching doctors: {str(e)}"
        )
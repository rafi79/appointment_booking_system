from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, and_, or_
from typing import List, Optional
from datetime import datetime, date, timedelta
from calendar import monthrange

from app.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import MonthlyReport, AppointmentStats
from app.schemas.user import UserResponse
from app.schemas.doctor import DoctorResponse

router = APIRouter()


@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard statistics
    """
    try:
        # User statistics
        total_users = db.query(User).count()
        total_patients = db.query(User).filter(User.user_type == UserType.PATIENT).count()
        total_doctors = db.query(User).filter(User.user_type == UserType.DOCTOR).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        # Appointment statistics
        total_appointments = db.query(Appointment).count()
        pending_appointments = db.query(Appointment).filter(
            Appointment.status == AppointmentStatus.PENDING
        ).count()
        confirmed_appointments = db.query(Appointment).filter(
            Appointment.status == AppointmentStatus.CONFIRMED
        ).count()
        completed_appointments = db.query(Appointment).filter(
            Appointment.status == AppointmentStatus.COMPLETED
        ).count()
        
        # Today's statistics
        today = datetime.now().date()
        today_appointments = db.query(Appointment).filter(
            Appointment.appointment_date == today
        ).count()
        
        # This month's statistics
        current_month_start = today.replace(day=1)
        this_month_appointments = db.query(Appointment).filter(
            Appointment.appointment_date >= current_month_start
        ).count()
        
        # Revenue statistics
        this_month_revenue = db.query(
            func.sum(Doctor.consultation_fee)
        ).join(Appointment).filter(
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.appointment_date >= current_month_start
        ).scalar() or 0
        
        return {
            "users": {
                "total": total_users,
                "patients": total_patients,
                "doctors": total_doctors,
                "active": active_users
            },
            "appointments": {
                "total": total_appointments,
                "pending": pending_appointments,
                "confirmed": confirmed_appointments,
                "completed": completed_appointments,
                "today": today_appointments,
                "this_month": this_month_appointments
            },
            "revenue": {
                "this_month": float(this_month_revenue)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dashboard data: {str(e)}"
        )


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
    user_type: Optional[UserType] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users with filters
    """
    try:
        query = db.query(User)
        
        if user_type:
            query = query.filter(User.user_type == user_type)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if search:
            search_filter = or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.mobile_number.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get user by ID
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/doctors", response_model=List[DoctorResponse])
async def get_all_doctors_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
    specialization: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all doctors with filters (Admin only)
    """
    try:
        query = db.query(Doctor).options(joinedload(Doctor.user))
        
        if specialization:
            query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
        
        if is_active is not None:
            query = query.join(User).filter(User.is_active == is_active)
        
        doctors = query.offset(skip).limit(limit).all()
        return doctors
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching doctors: {str(e)}"
        )


@router.get("/appointments")
async def get_all_appointments_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
    status: Optional[AppointmentStatus] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    doctor_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all appointments with filters (Admin only)
    """
    try:
        query = db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        )
        
        if status:
            query = query.filter(Appointment.status == status)
        
        if date_from:
            query = query.filter(Appointment.appointment_date >= date_from)
        
        if date_to:
            query = query.filter(Appointment.appointment_date <= date_to)
        
        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        
        if patient_id:
            query = query.filter(Appointment.patient_id == patient_id)
        
        appointments = query.order_by(Appointment.appointment_date.desc()).offset(skip).limit(limit).all()
        
        # Format appointments for response
        formatted_appointments = []
        for apt in appointments:
            formatted_appointments.append({
                "id": apt.id,
                "patient_id": apt.patient_id,
                "doctor_id": apt.doctor_id,
                "appointment_date": apt.appointment_date,
                "appointment_time": apt.appointment_time,
                "status": apt.status,
                "notes": apt.notes,
                "symptoms": apt.symptoms,
                "doctor_notes": apt.doctor_notes,
                "prescription": apt.prescription,
                "created_at": apt.created_at,
                "updated_at": apt.updated_at,
                "patient_name": apt.patient.full_name,
                "patient_mobile": apt.patient.mobile_number,
                "doctor_name": apt.doctor.user.full_name,
                "doctor_specialization": apt.doctor.specialization,
                "consultation_fee": apt.doctor.consultation_fee
            })
        
        return formatted_appointments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointments: {str(e)}"
        )


@router.get("/reports/monthly", response_model=List[MonthlyReport])
async def get_monthly_reports(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Generate monthly reports for all doctors
    """
    try:
        # Use current month/year if not provided
        if not year or not month:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        # Validate month and year
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be between 1 and 12"
            )
        
        if year < 2020 or year > 2030:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Year must be between 2020 and 2030"
            )
        
        # Get the start and end dates for the month
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        
        # Get all doctors
        doctors = db.query(Doctor).options(joinedload(Doctor.user)).all()
        
        reports = []
        for doctor in doctors:
            # Get appointments for this doctor in the month
            appointments = db.query(Appointment).filter(
                Appointment.doctor_id == doctor.id,
                Appointment.appointment_date >= start_date,
                Appointment.appointment_date <= end_date
            ).all()
            
            total_appointments = len(appointments)
            completed_appointments = len([a for a in appointments if a.status == AppointmentStatus.COMPLETED])
            cancelled_appointments = len([a for a in appointments if a.status == AppointmentStatus.CANCELLED])
            total_patients = len(set([a.patient_id for a in appointments]))
            total_earnings = completed_appointments * doctor.consultation_fee
            
            reports.append(MonthlyReport(
                doctor_id=doctor.id,
                doctor_name=doctor.user.full_name,
                specialization=doctor.specialization,
                month=month,
                year=year,
                total_patients=total_patients,
                total_appointments=total_appointments,
                total_earnings=total_earnings,
                completed_appointments=completed_appointments,
                cancelled_appointments=cancelled_appointments
            ))
        
        return reports
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating monthly reports: {str(e)}"
        )


@router.get("/reports/weekly")
async def get_weekly_report(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get weekly appointment report
    """
    try:
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        # Get appointments for this week
        appointments = db.query(Appointment).filter(
            Appointment.appointment_date >= week_start,
            Appointment.appointment_date <= week_end
        ).all()
        
        # Group by day
        daily_stats = {}
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_appointments = [apt for apt in appointments if apt.appointment_date == day]
            
            daily_stats[day.strftime('%A')] = {
                'date': day.isoformat(),
                'total': len(day_appointments),
                'pending': len([a for a in day_appointments if a.status == AppointmentStatus.PENDING]),
                'confirmed': len([a for a in day_appointments if a.status == AppointmentStatus.CONFIRMED]),
                'completed': len([a for a in day_appointments if a.status == AppointmentStatus.COMPLETED]),
                'cancelled': len([a for a in day_appointments if a.status == AppointmentStatus.CANCELLED])
            }
        
        return {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'daily_stats': daily_stats,
            'total_week_appointments': len(appointments)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating weekly report: {str(e)}"
        )


@router.get("/reports/revenue")
async def get_revenue_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get revenue report for a date range
    """
    try:
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Total revenue from completed appointments
        completed_appointments = db.query(Appointment).join(Doctor).filter(
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.appointment_date >= date_from,
            Appointment.appointment_date <= date_to
        ).all()
        
        total_revenue = sum([apt.doctor.consultation_fee for apt in completed_appointments])
        
        # Revenue by doctor
        doctor_revenue = {}
        for apt in completed_appointments:
            doctor_id = apt.doctor_id
            if doctor_id not in doctor_revenue:
                doctor_revenue[doctor_id] = {
                    'doctor_name': apt.doctor.user.full_name,
                    'specialization': apt.doctor.specialization,
                    'revenue': 0,
                    'completed_appointments': 0
                }
            doctor_revenue[doctor_id]['revenue'] += apt.doctor.consultation_fee
            doctor_revenue[doctor_id]['completed_appointments'] += 1
        
        # Revenue by specialization
        specialization_revenue = {}
        for apt in completed_appointments:
            spec = apt.doctor.specialization
            if spec not in specialization_revenue:
                specialization_revenue[spec] = {
                    'revenue': 0,
                    'appointments': 0
                }
            specialization_revenue[spec]['revenue'] += apt.doctor.consultation_fee
            specialization_revenue[spec]['appointments'] += 1
        
        return {
            "period": {
                "from": date_from,
                "to": date_to
            },
            "total_revenue": total_revenue,
            "doctor_revenue": [
                {
                    "doctor_id": dr_id,
                    **dr_data
                }
                for dr_id, dr_data in doctor_revenue.items()
            ],
            "specialization_revenue": [
                {
                    "specialization": spec,
                    **spec_data
                }
                for spec, spec_data in specialization_revenue.items()
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating revenue report: {str(e)}"
        )


@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Toggle user active status
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Don't allow deactivating other admins
        if user.user_type == UserType.ADMIN and user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate other admin users"
            )
        
        user.is_active = not user.is_active
        db.commit()
        
        return {
            "message": f"User {'activated' if user.is_active else 'deactivated'} successfully",
            "user_id": user.id,
            "is_active": user.is_active
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling user status: {str(e)}"
        )


@router.get("/system/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get system-wide statistics
    """
    try:
        # User registration trends (last 6 months)
        today = datetime.now().date()
        six_months_ago = today - timedelta(days=180)
        
        monthly_registrations = []
        monthly_appointments = []
        
        for i in range(6):
            month_start = six_months_ago + timedelta(days=i*30)
            month_end = month_start + timedelta(days=29)
            
            registrations = db.query(User).filter(
                func.date(User.created_at) >= month_start,
                func.date(User.created_at) <= month_end
            ).count()
            
            appointments = db.query(Appointment).filter(
                Appointment.appointment_date >= month_start,
                Appointment.appointment_date <= month_end
            ).count()
            
            monthly_registrations.append({
                "month": month_start.strftime("%Y-%m"),
                "registrations": registrations
            })
            
            monthly_appointments.append({
                "month": month_start.strftime("%Y-%m"),
                "appointments": appointments
            })
        
        # Most popular specializations
        specializations = db.query(Doctor.specialization).all()
        specialization_counts = {}
        
        for spec in specializations:
            spec_name = spec[0]
            if spec_name not in specialization_counts:
                specialization_counts[spec_name] = 0
            
            # Count appointments for this specialization
            count = db.query(Appointment).join(Doctor).filter(
                Doctor.specialization == spec_name
            ).count()
            specialization_counts[spec_name] = count
        
        # Sort by count and take top 5
        popular_specializations = sorted(
            specialization_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            "registration_trends": monthly_registrations,
            "appointment_trends": monthly_appointments,
            "popular_specializations": [
                {
                    "specialization": spec,
                    "appointment_count": count
                }
                for spec, count in popular_specializations
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching system stats: {str(e)}"
        )
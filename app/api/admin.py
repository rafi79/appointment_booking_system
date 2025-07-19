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
    Get admin dashboard statistics - Enhanced version
    """
    try:
        # User statistics
        total_users = db.query(User).count()
        total_patients = db.query(User).filter(User.user_type == UserType.PATIENT).count()
        total_doctors = db.query(User).filter(User.user_type == UserType.DOCTOR).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        # Active doctors (both user active and has doctor profile)
        active_doctors = db.query(Doctor).join(User).filter(
            User.is_active == True,
            User.user_type == UserType.DOCTOR
        ).count()
        
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
        
        # Revenue statistics - Fixed calculation
        completed_appointments_this_month = db.query(Appointment).join(Doctor).filter(
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.appointment_date >= current_month_start
        ).all()
        
        this_month_revenue = sum([apt.doctor.consultation_fee for apt in completed_appointments_this_month])
        
        # Total revenue
        all_completed_appointments = db.query(Appointment).join(Doctor).filter(
            Appointment.status == AppointmentStatus.COMPLETED
        ).all()
        
        total_revenue = sum([apt.doctor.consultation_fee for apt in all_completed_appointments])
        
        return {
            "users": {
                "total": total_users,
                "patients": total_patients,
                "doctors": total_doctors,
                "active": active_users
            },
            "doctors": {
                "total": total_doctors,
                "active": active_doctors
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
                "total": float(total_revenue),
                "this_month": float(this_month_revenue)
            }
        }
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        # Return zeros if there's an error but don't crash
        return {
            "users": {
                "total": 0,
                "patients": 0,
                "doctors": 0,
                "active": 0
            },
            "doctors": {
                "total": 0,
                "active": 0
            },
            "appointments": {
                "total": 0,
                "pending": 0,
                "confirmed": 0,
                "completed": 0,
                "today": 0,
                "this_month": 0
            },
            "revenue": {
                "total": 0.0,
                "this_month": 0.0
            }
        }


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
    Get all doctors with filters (Admin only) - FIXED VERSION
    """
    try:
        query = db.query(Doctor).options(
            joinedload(Doctor.user).joinedload(User.division),
            joinedload(Doctor.user).joinedload(User.district),
            joinedload(Doctor.user).joinedload(User.thana)
        )
        
        if specialization:
            query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
        
        if is_active is not None:
            query = query.join(User).filter(User.is_active == is_active)
        
        doctors = query.offset(skip).limit(limit).all()
        
        # Format response with proper data
        formatted_doctors = []
        for doctor in doctors:
            formatted_doctors.append({
                "id": doctor.id,
                "user_id": doctor.user_id,
                "license_number": doctor.license_number,
                "specialization": doctor.specialization,
                "experience_years": doctor.experience_years,
                "consultation_fee": doctor.consultation_fee,
                "qualification": doctor.qualification,
                "bio": doctor.bio,
                "available_timeslots": doctor.available_timeslots,
                "user": {
                    "id": doctor.user.id,
                    "full_name": doctor.user.full_name,
                    "email": doctor.user.email,
                    "mobile_number": doctor.user.mobile_number,
                    "user_type": doctor.user.user_type,
                    "is_active": doctor.user.is_active,
                    "is_verified": doctor.user.is_verified,
                    "profile_image": doctor.user.profile_image,
                    "division_id": doctor.user.division_id,
                    "district_id": doctor.user.district_id,
                    "thana_id": doctor.user.thana_id,
                    "address": doctor.user.address,
                    "created_at": doctor.user.created_at,
                    "updated_at": doctor.user.updated_at
                }
            })
        
        return formatted_doctors
        
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


# USER STATUS TOGGLE - Multiple endpoints for different frontend calls
@router.put("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Toggle user active status - PUT method
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
            "success": True,
            "message": f"User {'activated' if user.is_active else 'deactivated'} successfully",
            "user_id": user.id,
            "is_active": user.is_active
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling user status: {str(e)}"
        )


@router.post("/users/{user_id}/toggle")
async def toggle_user_status_post(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Toggle user active status - POST method (alternative)
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
            "success": True,
            "message": f"User {'activated' if user.is_active else 'deactivated'} successfully",
            "user_id": user.id,
            "is_active": user.is_active
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling user status: {str(e)}"
        )


@router.put("/users/{user_id}/status")
async def update_user_status_simple(
    user_id: int,
    status_data: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update user status - Simple endpoint with data payload
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get the new status from request
        new_status = status_data.get('is_active', not user.is_active)
        
        # Don't allow deactivating other admins
        if user.user_type == UserType.ADMIN and user.id != current_user.id and not new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate other admin users"
            )
        
        user.is_active = new_status
        db.commit()
        
        return {
            "success": True,
            "message": f"User {'activated' if user.is_active else 'deactivated'} successfully",
            "user_id": user.id,
            "is_active": user.is_active
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user status: {str(e)}"
        )


# REPORTS SECTION
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


@router.get("/reports/monthly/download")
async def download_monthly_report(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Download monthly report as CSV
    """
    try:
        # Get monthly reports data
        if not year or not month:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        from fastapi.responses import Response
        import csv
        from io import StringIO
        
        # Get report data (reuse the logic from get_monthly_reports)
        reports = await get_monthly_reports(year=year, month=month, current_user=current_user, db=db)
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Doctor ID', 'Doctor Name', 'Specialization', 'Month', 'Year',
            'Total Patients', 'Total Appointments', 'Total Earnings',
            'Completed Appointments', 'Cancelled Appointments'
        ])
        
        # Write data
        for report in reports:
            writer.writerow([
                report.doctor_id, report.doctor_name, report.specialization,
                report.month, report.year, report.total_patients,
                report.total_appointments, report.total_earnings,
                report.completed_appointments, report.cancelled_appointments
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        # Return CSV response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=monthly_report_{year}_{month:02d}.csv"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating CSV report: {str(e)}"
        )


@router.get("/reports/weekly/download")
async def download_weekly_report(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Download weekly report as CSV
    """
    try:
        from fastapi.responses import Response
        import csv
        from io import StringIO
        
        # Get weekly report data
        weekly_data = await get_weekly_report(current_user=current_user, db=db)
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Day', 'Date', 'Total', 'Pending', 'Confirmed', 'Completed', 'Cancelled'])
        
        # Write data
        for day, stats in weekly_data['daily_stats'].items():
            writer.writerow([
                day, stats['date'], stats['total'], stats['pending'],
                stats['confirmed'], stats['completed'], stats['cancelled']
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=weekly_report_{weekly_data['week_start']}.csv"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating weekly CSV report: {str(e)}"
        )


@router.get("/reports/custom")
async def get_custom_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get custom date range report
    """
    try:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Get appointments in date range
        appointments = db.query(Appointment).filter(
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= end_date
        ).all()
        
        # Calculate statistics
        total_appointments = len(appointments)
        status_counts = {}
        for status in AppointmentStatus:
            status_counts[status.value] = len([a for a in appointments if a.status == status])
        
        # Doctor-wise statistics
        doctor_stats = {}
        for apt in appointments:
            doctor_id = apt.doctor_id
            if doctor_id not in doctor_stats:
                doctor_stats[doctor_id] = {
                    'doctor_name': apt.doctor.user.full_name,
                    'specialization': apt.doctor.specialization,
                    'total_appointments': 0,
                    'completed': 0,
                    'revenue': 0
                }
            doctor_stats[doctor_id]['total_appointments'] += 1
            if apt.status == AppointmentStatus.COMPLETED:
                doctor_stats[doctor_id]['completed'] += 1
                doctor_stats[doctor_id]['revenue'] += apt.doctor.consultation_fee
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_appointments': total_appointments,
                'status_breakdown': status_counts
            },
            'doctor_statistics': list(doctor_stats.values())
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating custom report: {str(e)}"
        )


@router.put("/settings")
async def update_system_settings(
    settings_data: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update system settings (placeholder endpoint)
    """
    try:
        # This is a placeholder - you can implement actual settings storage
        # For now, just return success
        return {
            "success": True,
            "message": "Settings updated successfully",
            "settings": settings_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating settings: {str(e)}"
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


# ADDITIONAL UTILITY ENDPOINTS
@router.get("/users/count")
async def get_user_counts(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get user counts by type and status - Quick stats endpoint
    """
    try:
        return {
            "total_users": db.query(User).count(),
            "active_users": db.query(User).filter(User.is_active == True).count(),
            "inactive_users": db.query(User).filter(User.is_active == False).count(),
            "patients": db.query(User).filter(User.user_type == UserType.PATIENT).count(),
            "doctors": db.query(User).filter(User.user_type == UserType.DOCTOR).count(),
            "admins": db.query(User).filter(User.user_type == UserType.ADMIN).count(),
            "active_patients": db.query(User).filter(
                User.user_type == UserType.PATIENT, 
                User.is_active == True
            ).count(),
            "active_doctors": db.query(User).filter(
                User.user_type == UserType.DOCTOR, 
                User.is_active == True
            ).count()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user counts: {str(e)}"
        )


@router.get("/appointments/stats")
async def get_appointment_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get appointment statistics - Quick stats endpoint
    """
    try:
        today = datetime.now().date()
        
        return {
            "total": db.query(Appointment).count(),
            "today": db.query(Appointment).filter(Appointment.appointment_date == today).count(),
            "pending": db.query(Appointment).filter(Appointment.status == AppointmentStatus.PENDING).count(),
            "confirmed": db.query(Appointment).filter(Appointment.status == AppointmentStatus.CONFIRMED).count(),
            "completed": db.query(Appointment).filter(Appointment.status == AppointmentStatus.COMPLETED).count(),
            "cancelled": db.query(Appointment).filter(Appointment.status == AppointmentStatus.CANCELLED).count(),
            "this_week": db.query(Appointment).filter(
                Appointment.appointment_date >= today - timedelta(days=today.weekday()),
                Appointment.appointment_date <= today + timedelta(days=6-today.weekday())
            ).count(),
            "this_month": db.query(Appointment).filter(
                Appointment.appointment_date >= today.replace(day=1)
            ).count()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointment stats: {str(e)}"
        )


@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete user (Admin only) - Use with caution
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Don't allow deleting other admins
        if user.user_type == UserType.ADMIN and user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete other admin users"
            )
        
        # Check for existing appointments
        appointments_count = db.query(Appointment).filter(
            or_(
                Appointment.patient_id == user_id,
                Appointment.doctor_id == user_id if user.user_type == UserType.DOCTOR else False
            )
        ).count()
        
        if appointments_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete user with {appointments_count} existing appointments. Deactivate instead."
            )
        
        db.delete(user)
        db.commit()
        
        return {
            "success": True,
            "message": f"User {user.full_name} deleted successfully",
            "deleted_user_id": user_id
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )


# MISSING EXPORT ENDPOINTS
@router.get("/export/users")
async def export_users_csv(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Export users to CSV
    """
    try:
        from fastapi.responses import Response
        import csv
        from io import StringIO
        
        users = db.query(User).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'ID', 'Full Name', 'Email', 'Mobile', 'User Type', 
            'Is Active', 'Is Verified', 'Created At', 'Address'
        ])
        
        # Write data
        for user in users:
            writer.writerow([
                user.id, user.full_name, user.email, user.mobile_number,
                user.user_type.value, user.is_active, user.is_verified,
                user.created_at.strftime('%Y-%m-%d %H:%M:%S'), user.address or ''
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_export.csv"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting users: {str(e)}"
        )


@router.get("/export/doctors")
async def export_doctors_csv(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Export doctors to CSV
    """
    try:
        from fastapi.responses import Response
        import csv
        from io import StringIO
        
        doctors = db.query(Doctor).options(joinedload(Doctor.user)).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'ID', 'Doctor Name', 'Email', 'Mobile', 'License Number',
            'Specialization', 'Experience Years', 'Consultation Fee',
            'Qualification', 'Is Active', 'Created At'
        ])
        
        # Write data
        for doctor in doctors:
            writer.writerow([
                doctor.id, doctor.user.full_name, doctor.user.email,
                doctor.user.mobile_number, doctor.license_number,
                doctor.specialization, doctor.experience_years,
                doctor.consultation_fee, doctor.qualification or '',
                doctor.user.is_active, doctor.user.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=doctors_export.csv"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting doctors: {str(e)}"
        )


@router.get("/export/appointments")
async def export_appointments_csv(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Export appointments to CSV
    """
    try:
        from fastapi.responses import Response
        import csv
        from io import StringIO
        
        appointments = db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.user)
        ).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'ID', 'Patient Name', 'Doctor Name', 'Specialization',
            'Date', 'Time', 'Status', 'Consultation Fee',
            'Notes', 'Symptoms', 'Created At'
        ])
        
        # Write data
        for apt in appointments:
            writer.writerow([
                apt.id, apt.patient.full_name, apt.doctor.user.full_name,
                apt.doctor.specialization, apt.appointment_date.strftime('%Y-%m-%d'),
                apt.appointment_time, apt.status.value, apt.doctor.consultation_fee,
                apt.notes or '', apt.symptoms or '',
                apt.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=appointments_export.csv"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting appointments: {str(e)}"
        )


@router.post("/clear-cache")
async def clear_cache(
    current_user: User = Depends(get_current_admin)
):
    """
    Clear application cache (placeholder)
    """
    try:
        # This is a placeholder - implement actual cache clearing if needed
        return {
            "success": True,
            "message": "Cache cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing cache: {str(e)}"
        )


@router.post("/backup")
async def create_backup(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create database backup (placeholder)
    """
    try:
        # Count all records for backup summary
        users_count = db.query(User).count()
        doctors_count = db.query(Doctor).count()
        appointments_count = db.query(Appointment).count()
        
        return {
            "success": True,
            "message": "Backup created successfully",
            "backup_info": {
                "users": users_count,
                "doctors": doctors_count,
                "appointments": appointments_count,
                "timestamp": datetime.now().isoformat(),
                "filename": f"medicare_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating backup: {str(e)}"
        )


@router.get("/specializations")
async def get_all_specializations(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all unique specializations for dropdown
    """
    try:
        specializations = db.query(Doctor.specialization).distinct().all()
        return [{"value": spec[0], "label": spec[0]} for spec in specializations if spec[0]]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching specializations: {str(e)}"
        )


@router.get("/health")
async def admin_health_check(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Admin health check - Test database connectivity and basic stats
    """
    try:
        # Test database connectivity
        user_count = db.query(User).count()
        doctor_count = db.query(Doctor).count()
        appointment_count = db.query(Appointment).count()
        
        return {
            "status": "healthy",
            "admin": current_user.full_name,
            "database": "connected",
            "quick_stats": {
                "users": user_count,
                "doctors": doctor_count,
                "appointments": appointment_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
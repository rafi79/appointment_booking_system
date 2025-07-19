#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from datetime import datetime

def test_admin_dashboard_logic():
    db = SessionLocal()
    try:
        print("🧪 Testing Admin Dashboard Logic...")
        print("=" * 50)
        
        # User statistics
        total_users = db.query(User).count()
        total_patients = db.query(User).filter(User.user_type == UserType.PATIENT).count()
        total_doctors = db.query(User).filter(User.user_type == UserType.DOCTOR).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        print(f"📊 User Statistics:")
        print(f"   Total Users: {total_users}")
        print(f"   Patients: {total_patients}")
        print(f"   Doctors: {total_doctors}")
        print(f"   Active Users: {active_users}")
        
        # Active doctors with profiles
        active_doctors = db.query(Doctor).join(User).filter(
            User.is_active == True,
            User.user_type == UserType.DOCTOR
        ).count()
        print(f"   Active Doctors with Profiles: {active_doctors}")
        
        # Appointment statistics
        total_appointments = db.query(Appointment).count()
        pending = db.query(Appointment).filter(Appointment.status == AppointmentStatus.PENDING).count()
        confirmed = db.query(Appointment).filter(Appointment.status == AppointmentStatus.CONFIRMED).count()
        completed = db.query(Appointment).filter(Appointment.status == AppointmentStatus.COMPLETED).count()
        
        print(f"\n📅 Appointment Statistics:")
        print(f"   Total: {total_appointments}")
        print(f"   Pending: {pending}")
        print(f"   Confirmed: {confirmed}")
        print(f"   Completed: {completed}")
        
        # Revenue calculation
        completed_appointments = db.query(Appointment).join(Doctor).filter(
            Appointment.status == AppointmentStatus.COMPLETED
        ).all()
        
        total_revenue = sum([apt.doctor.consultation_fee for apt in completed_appointments])
        print(f"\n💰 Revenue:")
        print(f"   Completed appointments for revenue: {len(completed_appointments)}")
        print(f"   Total Revenue: ৳{total_revenue}")
        
        # Today's appointments
        today = datetime.now().date()
        today_appointments = db.query(Appointment).filter(
            Appointment.appointment_date == today
        ).count()
        print(f"   Today's appointments: {today_appointments}")
        
        # Check if we have the expected seed data
        expected_users = 21  # 1 admin + 10 doctors + 8 patients + 2 additional
        if total_users >= expected_users:
            print(f"\n✅ Good! Found {total_users} users (expected ~{expected_users})")
        else:
            print(f"\n❌ Expected ~{expected_users} users, found {total_users}")
            print("   Run: python scripts/seed_data.py")
        
        dashboard_data = {
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
                "pending": pending, 
                "confirmed": confirmed, 
                "completed": completed,
                "today": today_appointments
            },
            "revenue": {
                "total": float(total_revenue)
            }
        }
        
        print(f"\n📋 Dashboard Data:")
        import json
        print(json.dumps(dashboard_data, indent=2))
        
        return dashboard_data
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    test_admin_dashboard_logic()
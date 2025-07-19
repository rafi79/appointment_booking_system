#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.location import Division, District, Thana

def check_database():
    db = SessionLocal()
    try:
        print("🔍 Checking database contents...")
        print("=" * 50)
        
        # Check users
        total_users = db.query(User).count()
        patients = db.query(User).filter(User.user_type == UserType.PATIENT).count()
        doctors_users = db.query(User).filter(User.user_type == UserType.DOCTOR).count()
        admins = db.query(User).filter(User.user_type == UserType.ADMIN).count()
        
        print(f"👥 Users:")
        print(f"   Total: {total_users}")
        print(f"   Patients: {patients}")
        print(f"   Doctors: {doctors_users}")
        print(f"   Admins: {admins}")
        
        # Check doctor profiles
        doctor_profiles = db.query(Doctor).count()
        print(f"\n👨‍⚕️ Doctor Profiles: {doctor_profiles}")
        
        # Check appointments
        appointments = db.query(Appointment).count()
        print(f"📅 Appointments: {appointments}")
        
        # Check locations
        divisions = db.query(Division).count()
        districts = db.query(District).count()
        thanas = db.query(Thana).count()
        
        print(f"\n📍 Locations:")
        print(f"   Divisions: {divisions}")
        print(f"   Districts: {districts}")
        print(f"   Thanas: {thanas}")
        
        # List some sample data
        if total_users > 0:
            print(f"\n📋 Sample Users:")
            sample_users = db.query(User).limit(3).all()
            for user in sample_users:
                print(f"   - {user.full_name} ({user.user_type.value}) - {user.email}")
        
        if doctor_profiles > 0:
            print(f"\n👨‍⚕️ Sample Doctors:")
            sample_doctors = db.query(Doctor).limit(3).all()
            for doctor in sample_doctors:
                print(f"   - Dr. {doctor.user.full_name} - {doctor.specialization}")
        
        print("=" * 50)
        
        if total_users == 0:
            print("❌ NO DATA FOUND! Run the seed script:")
            print("   python scripts/seed_data.py")
            return False
        else:
            print("✅ Database has data!")
            return True
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    check_database()
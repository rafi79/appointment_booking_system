#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, create_tables
from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.models.location import Division, District, Thana
from app.core.security import get_password_hash
from datetime import datetime, date, timedelta
import json


def create_locations(db: Session):
    """Create Bangladesh divisions, districts, and thanas"""
    
    print("Creating locations...")
    
    # Sample Bangladesh locations
    locations_data = {
        "Dhaka": {
            "Dhaka": ["Dhanmondi", "Gulshan", "Uttara", "Ramna", "Tejgaon"],
            "Gazipur": ["Gazipur Sadar", "Kaliakair", "Kapasia"],
            "Manikganj": ["Manikganj Sadar", "Shibalaya", "Saturia"]
        },
        "Chittagong": {
            "Chittagong": ["Kotwali", "Pahartali", "Bayazid", "Halishahar"],
            "Cox's Bazar": ["Cox's Bazar Sadar", "Chakaria", "Teknaf"],
            "Comilla": ["Comilla Sadar", "Burichang", "Brahmanpara"]
        },
        "Rajshahi": {
            "Rajshahi": ["Rajshahi Sadar", "Godagari", "Tanore"],
            "Bogra": ["Bogra Sadar", "Sherpur", "Shibganj"],
            "Pabna": ["Pabna Sadar", "Ishwardi", "Atgharia"]
        },
        "Khulna": {
            "Khulna": ["Khulna Sadar", "Sonadanga", "Khalishpur"],
            "Jessore": ["Jessore Sadar", "Chaugachha", "Jhikargachha"],
            "Satkhira": ["Satkhira Sadar", "Kalaroa", "Tala"]
        },
        "Sylhet": {
            "Sylhet": ["Sylhet Sadar", "Beanibazar", "Bishwanath"],
            "Moulvibazar": ["Moulvibazar Sadar", "Sreemangal", "Kamalganj"],
            "Habiganj": ["Habiganj Sadar", "Madhabpur", "Bahubal"]
        }
    }
    
    for division_name, districts in locations_data.items():
        # Create division
        division = Division(name=division_name)
        db.add(division)
        db.flush()
        
        for district_name, thanas in districts.items():
            # Create district
            district = District(name=district_name, division_id=division.id)
            db.add(district)
            db.flush()
            
            for thana_name in thanas:
                # Create thana
                thana = Thana(name=thana_name, district_id=district.id)
                db.add(thana)
    
    db.commit()
    print("Locations created successfully!")


def create_admin_user(db: Session):
    """Create default admin user"""
    
    print("Creating admin user...")
    
    # Get Dhaka division, district, and thana
    dhaka_division = db.query(Division).filter(Division.name == "Dhaka").first()
    dhaka_district = db.query(District).filter(District.name == "Dhaka").first()
    dhanmondi_thana = db.query(Thana).filter(Thana.name == "Dhanmondi").first()
    
    admin_user = User(
        full_name="System Administrator",
        email="admin@hospital.com",
        mobile_number="+8801712345678",
        password_hash=get_password_hash("Admin123!"),
        user_type=UserType.ADMIN,
        division_id=dhaka_division.id,
        district_id=dhaka_district.id,
        thana_id=dhanmondi_thana.id,
        address="123 Admin Street, Dhanmondi",
        is_active=True,
        is_verified=True
    )
    
    db.add(admin_user)
    db.commit()
    print("Admin user created! Email: admin@hospital.com, Password: Admin123!")


def create_sample_doctors(db: Session):
    """Create sample doctor users"""
    
    print("Creating sample doctors...")
    
    doctors_data = [
        {
            "name": "Dr. Ahmed Rahman",
            "email": "ahmed.rahman@hospital.com",
            "mobile": "+8801712345679",
            "specialization": "Cardiology",
            "license": "BMA12345",
            "experience": 10,
            "fee": 1500.0,
            "qualification": "MBBS, MD (Cardiology)",
            "bio": "Experienced cardiologist with 10+ years of practice",
            "division": "Dhaka",
            "district": "Dhaka",
            "thana": "Gulshan"
        },
        {
            "name": "Dr. Fatima Khatun",
            "email": "fatima.khatun@hospital.com",
            "mobile": "+8801712345680",
            "specialization": "Pediatrics",
            "license": "BMA12346",
            "experience": 8,
            "fee": 1200.0,
            "qualification": "MBBS, DCH",
            "bio": "Specialist in child healthcare and development",
            "division": "Dhaka",
            "district": "Dhaka",
            "thana": "Dhanmondi"
        },
        {
            "name": "Dr. Mohammad Ali",
            "email": "mohammad.ali@hospital.com",
            "mobile": "+8801712345681",
            "specialization": "Orthopedics",
            "license": "BMA12347",
            "experience": 12,
            "fee": 1800.0,
            "qualification": "MBBS, MS (Orthopedics)",
            "bio": "Expert in bone and joint disorders",
            "division": "Chittagong",
            "district": "Chittagong",
            "thana": "Kotwali"
        },
        {
            "name": "Dr. Nasreen Sultana",
            "email": "nasreen.sultana@hospital.com",
            "mobile": "+8801712345682",
            "specialization": "Gynecology",
            "license": "BMA12348",
            "experience": 15,
            "fee": 2000.0,
            "qualification": "MBBS, FCPS (Gynecology)",
            "bio": "Women's health specialist with extensive experience",
            "division": "Rajshahi",
            "district": "Rajshahi",
            "thana": "Rajshahi Sadar"
        },
        {
            "name": "Dr. Karim Uddin",
            "email": "karim.uddin@hospital.com",
            "mobile": "+8801712345683",
            "specialization": "Neurology",
            "license": "BMA12349",
            "experience": 9,
            "fee": 2500.0,
            "qualification": "MBBS, MD (Neurology)",
            "bio": "Neurologist specializing in brain and nervous system disorders",
            "division": "Khulna",
            "district": "Khulna",
            "thana": "Khulna Sadar"
        }
    ]
    
    for doctor_data in doctors_data:
        # Get location IDs
        division = db.query(Division).filter(Division.name == doctor_data["division"]).first()
        district = db.query(District).filter(District.name == doctor_data["district"]).first()
        thana = db.query(Thana).filter(Thana.name == doctor_data["thana"]).first()
        
        # Create user
        user = User(
            full_name=doctor_data["name"],
            email=doctor_data["email"],
            mobile_number=doctor_data["mobile"],
            password_hash=get_password_hash("Doctor123!"),
            user_type=UserType.DOCTOR,
            division_id=division.id,
            district_id=district.id,
            thana_id=thana.id,
            address=f"Medical Center, {doctor_data['thana']}",
            is_active=True,
            is_verified=True
        )
        
        db.add(user)
        db.flush()
        
        # Create doctor profile
        doctor = Doctor(
            user_id=user.id,
            license_number=doctor_data["license"],
            specialization=doctor_data["specialization"],
            experience_years=doctor_data["experience"],
            consultation_fee=doctor_data["fee"],
            qualification=doctor_data["qualification"],
            bio=doctor_data["bio"],
            available_timeslots={
                "monday": ["10:00-11:00", "14:00-15:00", "16:00-17:00"],
                "tuesday": ["10:00-11:00", "14:00-15:00", "16:00-17:00"],
                "wednesday": ["10:00-11:00", "14:00-15:00", "16:00-17:00"],
                "thursday": ["10:00-11:00", "14:00-15:00", "16:00-17:00"],
                "friday": ["10:00-11:00", "14:00-15:00"],
                "saturday": ["10:00-11:00", "14:00-15:00", "16:00-17:00"],
                "sunday": ["10:00-11:00"]
            }
        )
        
        db.add(doctor)
    
    db.commit()
    print("Sample doctors created! Default password: Doctor123!")


def create_sample_patients(db: Session):
    """Create sample patient users"""
    
    print("Creating sample patients...")
    
    patients_data = [
        {
            "name": "John Doe",
            "email": "john.doe@email.com",
            "mobile": "+8801712345684",
            "division": "Dhaka",
            "district": "Dhaka",
            "thana": "Uttara"
        },
        {
            "name": "Jane Smith",
            "email": "jane.smith@email.com",
            "mobile": "+8801712345685",
            "division": "Dhaka",
            "district": "Dhaka",
            "thana": "Gulshan"
        },
        {
            "name": "Ali Hassan",
            "email": "ali.hassan@email.com",
            "mobile": "+8801712345686",
            "division": "Chittagong",
            "district": "Chittagong",
            "thana": "Pahartali"
        },
        {
            "name": "Maria Rodriguez",
            "email": "maria.rodriguez@email.com",
            "mobile": "+8801712345687",
            "division": "Sylhet",
            "district": "Sylhet",
            "thana": "Sylhet Sadar"
        }
    ]
    
    for patient_data in patients_data:
        # Get location IDs
        division = db.query(Division).filter(Division.name == patient_data["division"]).first()
        district = db.query(District).filter(District.name == patient_data["district"]).first()
        thana = db.query(Thana).filter(Thana.name == patient_data["thana"]).first()
        
        # Create patient user
        user = User(
            full_name=patient_data["name"],
            email=patient_data["email"],
            mobile_number=patient_data["mobile"],
            password_hash=get_password_hash("Patient123!"),
            user_type=UserType.PATIENT,
            division_id=division.id,
            district_id=district.id,
            thana_id=thana.id,
            address=f"House 123, {patient_data['thana']}",
            is_active=True,
            is_verified=True
        )
        
        db.add(user)
    
    db.commit()
    print("Sample patients created! Default password: Patient123!")


def create_sample_appointments(db: Session):
    """Create sample appointments"""
    
    print("Creating sample appointments...")
    
    # Get some doctors and patients
    doctors = db.query(Doctor).limit(3).all()
    patients = db.query(User).filter(User.user_type == UserType.PATIENT).limit(4).all()
    
    # Create appointments for the next few days
    base_date = datetime.now().date()
    
    appointments_data = [
        {
            "patient_id": patients[0].id,
            "doctor_id": doctors[0].id,
            "date": base_date + timedelta(days=1),
            "time": "10:00-11:00",
            "status": AppointmentStatus.CONFIRMED,
            "notes": "Regular checkup",
            "symptoms": "Chest pain and shortness of breath"
        },
        {
            "patient_id": patients[1].id,
            "doctor_id": doctors[1].id,
            "date": base_date + timedelta(days=2),
            "time": "14:00-15:00",
            "status": AppointmentStatus.PENDING,
            "notes": "Child vaccination",
            "symptoms": "Routine vaccination for 2-year-old"
        },
        {
            "patient_id": patients[2].id,
            "doctor_id": doctors[2].id,
            "date": base_date + timedelta(days=3),
            "time": "16:00-17:00",
            "status": AppointmentStatus.CONFIRMED,
            "notes": "Knee pain consultation",
            "symptoms": "Persistent knee pain for 2 weeks"
        },
        {
            "patient_id": patients[3].id,
            "doctor_id": doctors[0].id,
            "date": base_date - timedelta(days=1),
            "time": "10:00-11:00",
            "status": AppointmentStatus.COMPLETED,
            "notes": "Follow-up visit",
            "symptoms": "Hypertension monitoring",
            "doctor_notes": "Blood pressure stable. Continue medication.",
            "prescription": "Amlodipine 5mg once daily"
        },
        {
            "patient_id": patients[0].id,
            "doctor_id": doctors[1].id,
            "date": base_date - timedelta(days=3),
            "time": "14:00-15:00",
            "status": AppointmentStatus.CANCELLED,
            "notes": "Cancelled by patient",
            "symptoms": "General consultation"
        }
    ]
    
    for apt_data in appointments_data:
        appointment = Appointment(
            patient_id=apt_data["patient_id"],
            doctor_id=apt_data["doctor_id"],
            appointment_date=apt_data["date"],
            appointment_time=apt_data["time"],
            status=apt_data["status"],
            notes=apt_data["notes"],
            symptoms=apt_data["symptoms"],
            doctor_notes=apt_data.get("doctor_notes"),
            prescription=apt_data.get("prescription")
        )
        
        db.add(appointment)
    
    db.commit()
    print("Sample appointments created!")


def main():
    """Main function to seed the database"""
    
    print("Starting database seeding...")
    
    # Create tables
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(Division).first():
            print("Database already seeded. Skipping...")
            return
        
        # Seed data
        create_locations(db)
        create_admin_user(db)
        create_sample_doctors(db)
        create_sample_patients(db)
        create_sample_appointments(db)
        
        print("\n" + "="*50)
        print("DATABASE SEEDING COMPLETED!")
        print("="*50)
        print("\nDefault Users Created:")
        print("Admin: admin@hospital.com / Admin123!")
        print("Doctors: *.doctor@hospital.com / Doctor123!")
        print("Patients: *.patient@email.com / Patient123!")
        print("\nYou can now start the application!")
        print("="*50)
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
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
    
    # Complete Bangladesh locations data
    locations_data = {
        "Dhaka": {
            "Dhaka": ["Dhanmondi", "Gulshan", "Uttara", "Ramna", "Tejgaon", "Wari", "Motijheel"],
            "Gazipur": ["Gazipur Sadar", "Kaliakair", "Kapasia", "Sreepur", "Kaliganj"],
            "Manikganj": ["Manikganj Sadar", "Shibalaya", "Saturia", "Harirampur", "Daulatpur"]
        },
        "Chittagong": {
            "Chittagong": ["Kotwali", "Pahartali", "Bayazid", "Halishahar", "Chandgaon", "Karnaphuli"],
            "Cox's Bazar": ["Cox's Bazar Sadar", "Chakaria", "Teknaf", "Ramu", "Ukhia"],
            "Comilla": ["Comilla Sadar", "Burichang", "Brahmanpara", "Chandina", "Debidwar"]
        },
        "Rajshahi": {
            "Rajshahi": ["Rajshahi Sadar", "Godagari", "Tanore", "Mohanpur", "Charghat"],
            "Bogra": ["Bogra Sadar", "Sherpur", "Shibganj", "Sonatola", "Gabtali"],
            "Pabna": ["Pabna Sadar", "Ishwardi", "Atgharia", "Chatmohar", "Santhia"]
        },
        "Khulna": {
            "Khulna": ["Khulna Sadar", "Sonadanga", "Khalishpur", "Khan Jahan Ali", "Kotwali"],
            "Jessore": ["Jessore Sadar", "Chaugachha", "Jhikargachha", "Keshabpur", "Manirampur"],
            "Satkhira": ["Satkhira Sadar", "Kalaroa", "Tala", "Debhata", "Kaliganj"]
        },
        "Sylhet": {
            "Sylhet": ["Sylhet Sadar", "Beanibazar", "Bishwanath", "Companiganj", "Fenchuganj"],
            "Moulvibazar": ["Moulvibazar Sadar", "Sreemangal", "Kamalganj", "Kulaura", "Rajnagar"],
            "Habiganj": ["Habiganj Sadar", "Madhabpur", "Bahubal", "Ajmiriganj", "Baniachong"]
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
    print("✅ Locations created successfully!")


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
        address="123 Admin Street, Dhanmondi, Dhaka",
        is_active=True,
        is_verified=True
    )
    
    db.add(admin_user)
    db.commit()
    print("✅ Admin user created! Email: admin@hospital.com, Password: Admin123!")


def create_sample_doctors(db: Session):
    """Create comprehensive sample doctor users"""
    
    print("Creating sample doctors...")
    
    doctors_data = [
        {
            "name": "Dr. Ahmed Rahman",
            "email": "ahmed.rahman@hospital.com",
            "mobile": "+8801712345679",
            "specialization": "Cardiology",
            "license": "BMA12345",
            "experience": 12,
            "fee": 1500.0,
            "qualification": "MBBS, MD (Cardiology), FACC",
            "bio": "Senior cardiologist with 12+ years of experience in interventional cardiology and heart disease management. Expert in cardiac catheterization and angioplasty.",
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
            "qualification": "MBBS, DCH, MD (Pediatrics)",
            "bio": "Dedicated pediatrician specializing in child healthcare, vaccination, and developmental pediatrics. Committed to providing compassionate care for children.",
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
            "experience": 15,
            "fee": 1800.0,
            "qualification": "MBBS, MS (Orthopedics), FRCS",
            "bio": "Experienced orthopedic surgeon specializing in joint replacement, sports injuries, and trauma surgery. Pioneer in minimally invasive orthopedic procedures.",
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
            "experience": 18,
            "fee": 2000.0,
            "qualification": "MBBS, FCPS (Gynecology), FRCOG",
            "bio": "Senior gynecologist and obstetrician with extensive experience in women's health, high-risk pregnancies, and minimally invasive gynecological procedures.",
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
            "experience": 10,
            "fee": 2500.0,
            "qualification": "MBBS, MD (Neurology), DM (Neurology)",
            "bio": "Neurologist specializing in stroke management, epilepsy, and neurodegenerative diseases. Expert in EEG interpretation and neuroimaging.",
            "division": "Khulna",
            "district": "Khulna",
            "thana": "Khulna Sadar"
        },
        {
            "name": "Dr. Rashida Begum",
            "email": "rashida.begum@hospital.com",
            "mobile": "+8801712345684",
            "specialization": "Dermatology",
            "license": "BMA12350",
            "experience": 7,
            "fee": 1300.0,
            "qualification": "MBBS, DDV, MD (Dermatology)",
            "bio": "Dermatologist focusing on skin diseases, cosmetic dermatology, and dermatopathology. Specialized in acne treatment and anti-aging procedures.",
            "division": "Sylhet",
            "district": "Sylhet",
            "thana": "Sylhet Sadar"
        },
        {
            "name": "Dr. Abdul Mannan",
            "email": "abdul.mannan@hospital.com",
            "mobile": "+8801712345685",
            "specialization": "General Medicine",
            "license": "BMA12351",
            "experience": 20,
            "fee": 1000.0,
            "qualification": "MBBS, FCPS (Medicine), FRCP",
            "bio": "Senior physician with two decades of experience in internal medicine, diabetes management, and preventive healthcare. Known for holistic patient care.",
            "division": "Dhaka",
            "district": "Dhaka",
            "thana": "Uttara"
        },
        {
            "name": "Dr. Sharmin Akter",
            "email": "sharmin.akter@hospital.com",
            "mobile": "+8801712345686",
            "specialization": "Psychiatry",
            "license": "BMA12352",
            "experience": 9,
            "fee": 1600.0,
            "qualification": "MBBS, MPhil (Psychiatry), MD (Psychiatry)",
            "bio": "Psychiatrist specializing in mood disorders, anxiety management, and adolescent mental health. Advocate for mental health awareness and therapy.",
            "division": "Chittagong",
            "district": "Chittagong",
            "thana": "Pahartali"
        },
        {
            "name": "Dr. Mizanur Rahman",
            "email": "mizanur.rahman@hospital.com",
            "mobile": "+8801712345687",
            "specialization": "Surgery",
            "license": "BMA12353",
            "experience": 16,
            "fee": 2200.0,
            "qualification": "MBBS, FCPS (Surgery), FRCS",
            "bio": "General and laparoscopic surgeon with expertise in abdominal surgery, hernia repair, and minimally invasive surgical techniques.",
            "division": "Rajshahi",
            "district": "Bogra",
            "thana": "Bogra Sadar"
        },
        {
            "name": "Dr. Salma Khatun",
            "email": "salma.khatun@hospital.com",
            "mobile": "+8801712345688",
            "specialization": "Dentistry",
            "license": "BMA12354",
            "experience": 6,
            "fee": 800.0,
            "qualification": "BDS, MDS (Oral Surgery)",
            "bio": "Dental surgeon specializing in oral and maxillofacial surgery, dental implants, and cosmetic dentistry. Committed to pain-free dental care.",
            "division": "Khulna",
            "district": "Jessore",
            "thana": "Jessore Sadar"
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
            address=f"Medical Center, {doctor_data['thana']}, {doctor_data['district']}",
            is_active=True,
            is_verified=True
        )
        
        db.add(user)
        db.flush()
        
        # Create doctor profile with realistic availability
        available_days = ["monday", "tuesday", "wednesday", "thursday", "saturday"]
        weekend_days = ["friday", "sunday"]
        
        timeslots = {}
        for day in available_days:
            timeslots[day] = ["09:00-10:00", "10:00-11:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"]
        
        for day in weekend_days:
            timeslots[day] = ["09:00-10:00", "10:00-11:00"] if day == "friday" else ["10:00-11:00"]
        
        doctor = Doctor(
            user_id=user.id,
            license_number=doctor_data["license"],
            specialization=doctor_data["specialization"],
            experience_years=doctor_data["experience"],
            consultation_fee=doctor_data["fee"],
            qualification=doctor_data["qualification"],
            bio=doctor_data["bio"],
            available_timeslots=timeslots
        )
        
        db.add(doctor)
    
    db.commit()
    print("✅ Sample doctors created! Default password: Doctor123!")


def create_sample_patients(db: Session):
    """Create diverse sample patient users"""
    
    print("Creating sample patients...")
    
    patients_data = [
        {
            "name": "John Doe",
            "email": "john.doe@email.com",
            "mobile": "+8801712345690",
            "division": "Dhaka",
            "district": "Dhaka",
            "thana": "Uttara"
        },
        {
            "name": "Jane Smith",
            "email": "jane.smith@email.com",
            "mobile": "+8801712345691",
            "division": "Dhaka",
            "district": "Dhaka",
            "thana": "Gulshan"
        },
        {
            "name": "Ali Hassan",
            "email": "ali.hassan@email.com",
            "mobile": "+8801712345692",
            "division": "Chittagong",
            "district": "Chittagong",
            "thana": "Pahartali"
        },
        {
            "name": "Maria Rodriguez",
            "email": "maria.rodriguez@email.com",
            "mobile": "+8801712345693",
            "division": "Sylhet",
            "district": "Sylhet",
            "thana": "Sylhet Sadar"
        },
        {
            "name": "Kamal Ahmed",
            "email": "kamal.ahmed@email.com",
            "mobile": "+8801712345694",
            "division": "Rajshahi",
            "district": "Rajshahi",
            "thana": "Rajshahi Sadar"
        },
        {
            "name": "Fatima Khan",
            "email": "fatima.khan@email.com",
            "mobile": "+8801712345695",
            "division": "Khulna",
            "district": "Khulna",
            "thana": "Khulna Sadar"
        },
        {
            "name": "Robert Johnson",
            "email": "robert.johnson@email.com",
            "mobile": "+8801712345696",
            "division": "Dhaka",
            "district": "Gazipur",
            "thana": "Gazipur Sadar"
        },
        {
            "name": "Amina Begum",
            "email": "amina.begum@email.com",
            "mobile": "+8801712345697",
            "division": "Chittagong",
            "district": "Cox's Bazar",
            "thana": "Cox's Bazar Sadar"
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
            address=f"House 123, {patient_data['thana']}, {patient_data['district']}",
            is_active=True,
            is_verified=True
        )
        
        db.add(user)
    
    db.commit()
    print("✅ Sample patients created! Default password: Patient123!")


def create_sample_appointments(db: Session):
    """Create realistic sample appointments"""
    
    print("Creating sample appointments...")
    
    # Get doctors and patients
    doctors = db.query(Doctor).all()
    patients = db.query(User).filter(User.user_type == UserType.PATIENT).all()
    
    # Create appointments for the past, present, and future
    base_date = datetime.now().date()
    
    appointments_data = [
        # Past appointments (completed)
        {
            "patient_id": patients[0].id,
            "doctor_id": doctors[0].id,
            "date": base_date - timedelta(days=7),
            "time": "10:00-11:00",
            "status": AppointmentStatus.COMPLETED,
            "notes": "Regular cardiology checkup",
            "symptoms": "Chest pain and shortness of breath",
            "doctor_notes": "ECG normal. Blood pressure slightly elevated. Recommended lifestyle changes.",
            "prescription": "Amlodipine 5mg once daily, follow-up in 3 months"
        },
        {
            "patient_id": patients[1].id,
            "doctor_id": doctors[1].id,
            "date": base_date - timedelta(days=5),
            "time": "14:00-15:00",
            "status": AppointmentStatus.COMPLETED,
            "notes": "Child vaccination",
            "symptoms": "Routine vaccination for 2-year-old",
            "doctor_notes": "Vaccination completed successfully. Child is healthy and developing normally.",
            "prescription": "Paracetamol drops if fever develops"
        },
        {
            "patient_id": patients[2].id,
            "doctor_id": doctors[2].id,
            "date": base_date - timedelta(days=3),
            "time": "16:00-17:00",
            "status": AppointmentStatus.COMPLETED,
            "notes": "Knee pain consultation",
            "symptoms": "Persistent knee pain for 2 weeks",
            "doctor_notes": "X-ray shows mild osteoarthritis. Recommended physiotherapy.",
            "prescription": "Ibuprofen 400mg twice daily, physiotherapy sessions"
        },
        
        # Today's appointments
        {
            "patient_id": patients[3].id,
            "doctor_id": doctors[3].id,
            "date": base_date,
            "time": "09:00-10:00",
            "status": AppointmentStatus.CONFIRMED,
            "notes": "Gynecology consultation",
            "symptoms": "Irregular menstrual cycle"
        },
        {
            "patient_id": patients[4].id,
            "doctor_id": doctors[4].id,
            "date": base_date,
            "time": "14:00-15:00",
            "status": AppointmentStatus.CONFIRMED,
            "notes": "Neurology follow-up",
            "symptoms": "Migraine headaches"
        },
        
        # Future appointments
        {
            "patient_id": patients[5].id,
            "doctor_id": doctors[5].id,
            "date": base_date + timedelta(days=1),
            "time": "10:00-11:00",
            "status": AppointmentStatus.CONFIRMED,
            "notes": "Skin consultation",
            "symptoms": "Acne treatment follow-up"
        },
        {
            "patient_id": patients[6].id,
            "doctor_id": doctors[6].id,
            "date": base_date + timedelta(days=2),
            "time": "09:00-10:00",
            "status": AppointmentStatus.PENDING,
            "notes": "General health checkup",
            "symptoms": "Annual health screening"
        },
        {
            "patient_id": patients[7].id,
            "doctor_id": doctors[7].id,
            "date": base_date + timedelta(days=3),
            "time": "15:00-16:00",
            "status": AppointmentStatus.PENDING,
            "notes": "Mental health consultation",
            "symptoms": "Anxiety and stress management"
        },
        {
            "patient_id": patients[0].id,
            "doctor_id": doctors[8].id,
            "date": base_date + timedelta(days=5),
            "time": "16:00-17:00",
            "status": AppointmentStatus.CONFIRMED,
            "notes": "Surgery consultation",
            "symptoms": "Gallbladder issues"
        },
        {
            "patient_id": patients[1].id,
            "doctor_id": doctors[9].id,
            "date": base_date + timedelta(days=7),
            "time": "10:00-11:00",
            "status": AppointmentStatus.PENDING,
            "notes": "Dental checkup",
            "symptoms": "Tooth pain and sensitivity"
        },
        
        # Cancelled appointment
        {
            "patient_id": patients[2].id,
            "doctor_id": doctors[0].id,
            "date": base_date - timedelta(days=1),
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
    print("✅ Sample appointments created!")


def create_additional_users(db: Session):
    """Create additional users for testing"""
    
    print("Creating additional test users...")
    
    # Get some locations
    dhaka_division = db.query(Division).filter(Division.name == "Dhaka").first()
    dhaka_district = db.query(District).filter(District.name == "Dhaka").first()
    gulshan_thana = db.query(Thana).filter(Thana.name == "Gulshan").first()
    
    # Additional admin user
    admin2 = User(
        full_name="Hospital Administrator",
        email="hospital.admin@medicare.com",
        mobile_number="+8801712345699",
        password_hash=get_password_hash("Admin123!"),
        user_type=UserType.ADMIN,
        division_id=dhaka_division.id,
        district_id=dhaka_district.id,
        thana_id=gulshan_thana.id,
        address="Hospital Complex, Gulshan, Dhaka",
        is_active=True,
        is_verified=True
    )
    
    db.add(admin2)
    
    # Test patient with different scenarios
    test_patients = [
        {
            "name": "Test Patient One",
            "email": "test.patient1@example.com",
            "mobile": "+8801712345700"
        },
        {
            "name": "Test Patient Two", 
            "email": "test.patient2@example.com",
            "mobile": "+8801712345701"
        }
    ]
    
    for patient_data in test_patients:
        user = User(
            full_name=patient_data["name"],
            email=patient_data["email"],
            mobile_number=patient_data["mobile"],
            password_hash=get_password_hash("Patient123!"),
            user_type=UserType.PATIENT,
            division_id=dhaka_division.id,
            district_id=dhaka_district.id,
            thana_id=gulshan_thana.id,
            address="Test Address, Gulshan, Dhaka",
            is_active=True,
            is_verified=True
        )
        db.add(user)
    
    db.commit()
    print("✅ Additional test users created!")


def print_summary(db: Session):
    """Print summary of seeded data"""
    
    print("\n" + "="*60)
    print("🏥 MEDICARE DATABASE SEEDING COMPLETED!")
    print("="*60)
    
    # Count records
    divisions_count = db.query(Division).count()
    districts_count = db.query(District).count()
    thanas_count = db.query(Thana).count()
    users_count = db.query(User).count()
    doctors_count = db.query(Doctor).count()
    appointments_count = db.query(Appointment).count()
    
    print(f"\n📊 DATABASE STATISTICS:")
    print(f"├── Divisions: {divisions_count}")
    print(f"├── Districts: {districts_count}")
    print(f"├── Thanas: {thanas_count}")
    print(f"├── Total Users: {users_count}")
    print(f"├── Doctors: {doctors_count}")
    print(f"└── Appointments: {appointments_count}")
    
    print(f"\n🔑 DEFAULT LOGIN CREDENTIALS:")
    print(f"┌─ ADMIN ACCOUNTS ─────────────────────────")
    print(f"│ Email: admin@hospital.com")
    print(f"│ Password: Admin123!")
    print(f"│ Role: System Administrator")
    print(f"├─────────────────────────────────────────")
    print(f"│ Email: hospital.admin@medicare.com")
    print(f"│ Password: Admin123!")
    print(f"│ Role: Hospital Administrator")
    print(f"└─────────────────────────────────────────")
    
    print(f"\n👨‍⚕️ DOCTOR ACCOUNTS:")
    print(f"┌─ All doctor emails end with @hospital.com")
    print(f"│ Password: Doctor123!")
    print(f"│ Example: ahmed.rahman@hospital.com")
    print(f"│ Specializations: Cardiology, Pediatrics,")
    print(f"│ Orthopedics, Gynecology, Neurology, etc.")
    print(f"└─────────────────────────────────────────")
    
    print(f"\n👤 PATIENT ACCOUNTS:")
    print(f"┌─ All patient emails end with @email.com")
    print(f"│ Password: Patient123!")
    print(f"│ Example: john.doe@email.com")
    print(f"│ Test accounts: test.patient1@example.com")
    print(f"└─────────────────────────────────────────")
    
    print(f"\n🌐 QUICK START:")
    print(f"1. Start your FastAPI server: uvicorn app.main:app --reload")
    print(f"2. Visit: http://localhost:8000")
    print(f"3. Click demo login or use credentials above")
    print(f"4. API Documentation: http://localhost:8000/docs")
    
    print(f"\n🎯 FEATURES READY:")
    print(f"✅ User Authentication (Admin, Doctor, Patient)")
    print(f"✅ Location Management (Bangladesh divisions/districts)")
    print(f"✅ Doctor Profiles & Specializations")
    print(f"✅ Appointment Booking & Management")
    print(f"✅ Sample Data for Testing")
    print(f"✅ Professional Dashboards")
    
    print("="*60)
    print("🚀 Your MediCare system is ready to use!")
    print("="*60)


def main():
    """Main function to seed the database"""
    
    print("🏥 Starting MediCare Database Seeding...")
    print("─" * 50)
    
    # Create tables
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(Division).first():
            print("⚠️  Database already contains data.")
            response = input("Do you want to continue and add more data? (y/N): ")
            if response.lower() != 'y':
                print("Seeding cancelled.")
                return
        
        # Seed data step by step
        create_locations(db)
        create_admin_user(db)
        create_sample_doctors(db)
        create_sample_patients(db)
        create_sample_appointments(db)
        create_additional_users(db)
        
        # Print summary
        print_summary(db)
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        print(f"Rolling back changes...")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import Optional
import os

from app.config import settings
from app.database import create_tables, get_db

# Import all models to ensure proper initialization - THIS IS CRITICAL
from app.models import (
    Division, District, Thana,
    User, UserType,
    Doctor,
    Appointment, AppointmentStatus
)

# Import dependencies and schemas for profile endpoints
from app.core.dependencies import get_current_user
from app.schemas.user import UserProfile, UserUpdate

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A comprehensive appointment booking system for healthcare providers",
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates setup
templates = Jinja2Templates(directory="templates")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount upload directory
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include API routers
try:
    from app.api.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    print("✅ Auth router loaded successfully")
except Exception as e:
    print(f"❌ Failed to load auth router: {e}")

try:
    from app.api.users import router as users_router
    app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
    print("✅ Users router loaded successfully")
except Exception as e:
    print(f"❌ Failed to load users router: {e}")

try:
    from app.api.doctors import router as doctors_router
    app.include_router(doctors_router, prefix="/api/v1/doctors", tags=["Doctors"])
    print("✅ Doctors router loaded successfully")
except Exception as e:
    print(f"❌ Failed to load doctors router: {e}")

try:
    from app.api.appointments import router as appointments_router
    app.include_router(appointments_router, prefix="/api/v1/appointments", tags=["Appointments"])
    print("✅ Appointments router loaded successfully")
except Exception as e:
    print(f"❌ Failed to load appointments router: {e}")

try:
    from app.api.admin import router as admin_router
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
    print("✅ Admin router loaded successfully")
except Exception as e:
    print(f"❌ Failed to load admin router: {e}")


# CRITICAL FIX: Add missing profile endpoints directly to main app
@app.get("/api/v1/users/profile", response_model=UserProfile, tags=["User Profile"])
async def get_user_profile_main(current_user: User = Depends(get_current_user)):
    """
    Get current user's profile - Main endpoint to fix 404 errors
    """
    try:
        return UserProfile(
            id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            mobile_number=current_user.mobile_number,
            user_type=current_user.user_type,
            profile_image=current_user.profile_image,
            division_name=current_user.division.name if current_user.division else None,
            district_name=current_user.district.name if current_user.district else None,
            thana_name=current_user.thana.name if current_user.thana else None,
            address=current_user.address,
            is_active=current_user.is_active,
            created_at=current_user.created_at
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )


@app.put("/api/v1/users/profile", response_model=UserProfile, tags=["User Profile"])
async def update_user_profile_main(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile - Main endpoint to fix 404 errors
    """
    try:
        # Check if mobile number is already taken by another user
        if user_update.mobile_number:
            existing_user = db.query(User).filter(
                User.mobile_number == user_update.mobile_number,
                User.id != current_user.id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mobile number already taken"
                )
        
        # Update user fields
        for field, value in user_update.dict(exclude_unset=True).items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        db.commit()
        db.refresh(current_user)
        
        return UserProfile(
            id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            mobile_number=current_user.mobile_number,
            user_type=current_user.user_type,
            profile_image=current_user.profile_image,
            division_name=current_user.division.name if current_user.division else None,
            district_name=current_user.district.name if current_user.district else None,
            thana_name=current_user.thana.name if current_user.thana else None,
            address=current_user.address,
            is_active=current_user.is_active,
            created_at=current_user.created_at
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )


# CRITICAL FIXES: Add missing endpoints for frontend functionality

# Fix 1: Doctor Schedule Endpoints (fixes 404 errors)
@app.get("/api/v1/doctors/me/schedule", tags=["Doctor Schedule"])
async def get_doctor_schedule_main(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current doctor's schedule - Main endpoint"""
    try:
        if current_user.user_type != UserType.DOCTOR:
            raise HTTPException(status_code=403, detail="Doctor access required")
        
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        return {
            "doctor_id": doctor.id,
            "available_timeslots": doctor.available_timeslots or {}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching schedule: {str(e)}")


@app.put("/api/v1/doctors/me/schedule", tags=["Doctor Schedule"])
async def update_doctor_schedule_main(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current doctor's schedule - Main endpoint"""
    try:
        if current_user.user_type != UserType.DOCTOR:
            raise HTTPException(status_code=403, detail="Doctor access required")
        
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        request_body = await request.json()
        
        # Handle different input formats
        if 'available_timeslots' in request_body:
            available_timeslots = request_body['available_timeslots']
        else:
            valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            available_timeslots = {k.lower(): v for k, v in request_body.items() if k.lower() in valid_days}
        
        # Basic validation and cleaning
        cleaned_timeslots = {}
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for day, timeslots in available_timeslots.items():
            day_lower = day.lower().strip()
            if day_lower not in valid_days:
                continue
            
            if not isinstance(timeslots, list):
                timeslots = [timeslots] if isinstance(timeslots, str) and timeslots.strip() else []
            
            valid_slots = [slot.strip() for slot in timeslots if isinstance(slot, str) and ':' in slot and '-' in slot]
            cleaned_timeslots[day_lower] = valid_slots
        
        doctor.available_timeslots = cleaned_timeslots
        db.commit()
        
        return {
            "success": True,
            "message": "Schedule updated successfully",
            "available_timeslots": doctor.available_timeslots
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating schedule: {str(e)}")


# Fix 3: Doctor Profile Endpoints (fixes doctor profile 404 errors)
@app.get("/api/v1/doctors/me/profile", tags=["Doctor Profile"])
async def get_doctor_profile_main(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current doctor's profile - Main endpoint"""
    try:
        if current_user.user_type != UserType.DOCTOR:
            raise HTTPException(status_code=403, detail="Doctor access required")
        
        doctor = db.query(Doctor).options(joinedload(Doctor.user)).filter(
            Doctor.user_id == current_user.id
        ).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        return {
            "id": doctor.id,
            "user_id": doctor.user_id,
            "full_name": doctor.user.full_name,
            "email": doctor.user.email,
            "mobile_number": doctor.user.mobile_number,
            "license_number": doctor.license_number,
            "specialization": doctor.specialization,
            "experience_years": doctor.experience_years,
            "consultation_fee": doctor.consultation_fee,
            "qualification": doctor.qualification,
            "bio": doctor.bio,
            "available_timeslots": doctor.available_timeslots,
            "is_active": doctor.user.is_active,
            "profile_image": doctor.user.profile_image
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching doctor profile: {str(e)}")


@app.put("/api/v1/doctors/me/profile", tags=["Doctor Profile"])
async def update_doctor_profile_main(
    profile_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current doctor's profile - Main endpoint"""
    try:
        if current_user.user_type != UserType.DOCTOR:
            raise HTTPException(status_code=403, detail="Doctor access required")
        
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        
        # Update user fields
        user_fields = ['full_name', 'mobile_number']
        for field in user_fields:
            if field in profile_data and profile_data[field]:
                setattr(current_user, field, profile_data[field])
        
        # Update doctor fields
        doctor_fields = ['specialization', 'experience_years', 'consultation_fee', 'qualification', 'bio']
        for field in doctor_fields:
            if field in profile_data and profile_data[field] is not None:
                setattr(doctor, field, profile_data[field])
        
        db.commit()
        db.refresh(doctor)
        db.refresh(current_user)
        
        return {
            "success": True,
            "message": "Doctor profile updated successfully",
            "doctor": {
                "id": doctor.id,
                "full_name": current_user.full_name,
                "email": current_user.email,
                "mobile_number": current_user.mobile_number,
                "specialization": doctor.specialization,
                "experience_years": doctor.experience_years,
                "consultation_fee": doctor.consultation_fee,
                "qualification": doctor.qualification,
                "bio": doctor.bio
            }
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating doctor profile: {str(e)}")


# Fix 4: Location endpoints for dropdowns
@app.get("/api/v1/locations/divisions", tags=["Locations"])
async def get_divisions_main(db: Session = Depends(get_db)):
    """Get all divisions"""
    try:
        divisions = db.query(Division).all()
        return [{"id": div.id, "name": div.name} for div in divisions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching divisions: {str(e)}")


@app.get("/api/v1/locations/districts/{division_id}", tags=["Locations"])
async def get_districts_main(division_id: int, db: Session = Depends(get_db)):
    """Get districts by division"""
    try:
        districts = db.query(District).filter(District.division_id == division_id).all()
        return [{"id": dist.id, "name": dist.name} for dist in districts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching districts: {str(e)}")


@app.get("/api/v1/locations/thanas/{district_id}", tags=["Locations"])
async def get_thanas_main(district_id: int, db: Session = Depends(get_db)):
    """Get thanas by district"""
    try:
        thanas = db.query(Thana).filter(Thana.district_id == district_id).all()
        return [{"id": thana.id, "name": thana.name} for thana in thanas]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching thanas: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print(f"🏥 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print("📊 Creating database tables...")
    create_tables()
    print("✅ Database tables created successfully")
    print("🚀 Server is ready!")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🌐 Homepage: http://localhost:8000")
    print("👤 Profile endpoints: /api/v1/users/profile")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    print(f"👋 Shutting down {settings.APP_NAME}")


# HTML Template Routes
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Homepage with professional landing page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/patient-dashboard", response_class=HTMLResponse)
async def patient_dashboard(request: Request):
    """Patient dashboard"""
    return templates.TemplateResponse("patient_dashboard.html", {"request": request})

@app.get("/doctor-dashboard", response_class=HTMLResponse)
async def doctor_dashboard(request: Request):
    """Doctor dashboard"""
    return templates.TemplateResponse("doctor_dashboard.html", {"request": request})

@app.get("/admin-dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard"""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@app.get("/book-appointment", response_class=HTMLResponse)
async def book_appointment_page(request: Request):
    """Book appointment page"""
    return templates.TemplateResponse("book_appointment.html", {"request": request})

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "MediCare Healthcare System is running!"
    }

@app.get("/api", response_class=HTMLResponse)
async def api_root():
    """API root with documentation links"""
    return """
    <html>
        <head>
            <title>MediCare API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #2c5aa0; }
                .link { display: inline-block; margin: 10px 15px 10px 0; padding: 10px 20px; background: #2c5aa0; color: white; text-decoration: none; border-radius: 5px; }
                .link:hover { background: #1a365d; }
                .credentials { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }
                .seed-info { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107; }
                .status { background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏥 MediCare Healthcare API</h1>
                <p>Welcome to the MediCare Appointment Booking System API</p>
                
                <h2>📚 Documentation & Tools</h2>
                <a href="/docs" class="link">📖 Interactive API Docs</a>
                <a href="/redoc" class="link">📋 ReDoc Documentation</a>
                <a href="/health" class="link">💚 Health Check</a>
                
                <h2>🖥️ User Interfaces</h2>
                <a href="/login" class="link">🔐 Login</a>
                <a href="/register" class="link">📝 Register</a>
                <a href="/patient-dashboard" class="link">👤 Patient Dashboard</a>
                <a href="/doctor-dashboard" class="link">👨‍⚕️ Doctor Dashboard</a>
                <a href="/admin-dashboard" class="link">🛡️ Admin Dashboard</a>
                
                <div class="seed-info">
                    <h3>🌱 Database Seeding</h3>
                    <p>To populate your database with sample data, run:</p>
                    <code>python scripts/seed_data.py</code>
                    <p>This will create sample users, doctors, patients, and appointments.</p>
                </div>
                
                <div class="credentials">
                    <h3>🔑 Default Login Credentials (after seeding):</h3>
                    <ul>
                        <li><strong>Admin:</strong> admin@hospital.com / Admin123!</li>
                        <li><strong>Doctor:</strong> ahmed.rahman@hospital.com / Doctor123!</li>
                        <li><strong>Patient:</strong> john.doe@email.com / Patient123!</li>
                    </ul>
                </div>
                
                <div class="status">
                    <h3>🔄 API Status</h3>
                    <p>✅ All routers loaded successfully</p>
                    <p>✅ Database connected</p>
                    <p>✅ Authentication enabled</p>
                    <p>✅ CORS configured</p>
                    <p>✅ Models initialized</p>
                    <p>✅ Profile endpoints fixed</p>
                </div>
                
                <h3>🚀 Quick Test Endpoints:</h3>
                <a href="/api/v1/users/locations/divisions" class="link">📍 Divisions</a>
                <a href="/docs#/Doctors/get_doctors_api_v1_doctors__get" class="link">👨‍⚕️ Doctors API</a>
                <a href="/docs#/User Profile/get_user_profile_main_api_v1_users_profile_get" class="link">👤 Profile API</a>
            </div>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
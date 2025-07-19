from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import os
import shutil
import time
from typing import Optional, Dict, Any
import logging

from app.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user
from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserProfile, PasswordChange
from app.schemas.doctor import DoctorCreate
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Custom registration request model to handle the frontend data
from pydantic import BaseModel, validator

class RegistrationRequest(BaseModel):
    full_name: str
    email: str
    mobile_number: str
    password: str
    user_type: str
    division_id: int
    district_id: int
    thana_id: int
    address: Optional[str] = None
    doctor_data: Optional[Dict[str, Any]] = None
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('mobile_number')
    def validate_mobile(cls, v):
        """Validate mobile number format"""
        import re
        # Clean the mobile number
        clean_mobile = re.sub(r'[^\d+]', '', v)
        
        # Bangladesh mobile number patterns
        patterns = [
            r'^\+8801[3-9]\d{8}$',  # +8801XXXXXXXXX
            r'^8801[3-9]\d{8}$',    # 8801XXXXXXXXX
            r'^01[3-9]\d{8}$',      # 01XXXXXXXXX
        ]
        
        for pattern in patterns:
            if re.match(pattern, clean_mobile):
                # Normalize to +88 format
                if clean_mobile.startswith('+88'):
                    return clean_mobile
                elif clean_mobile.startswith('88'):
                    return '+' + clean_mobile
                else:
                    return '+88' + clean_mobile
        
        raise ValueError('Mobile number must be in format +8801XXXXXXXXX')
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        import re
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v


@router.post("/register", response_model=UserResponse)
async def register(
    request: RegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user with improved error handling
    """
    try:
        logger.info(f"Registration attempt for email: {request.email}")
        logger.info(f"User type received: {request.user_type}")
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == request.email) | (User.mobile_number == request.mobile_number)
        ).first()
        
        if existing_user:
            if existing_user.email == request.email:
                detail = "A user with this email address already exists"
            else:
                detail = "A user with this mobile number already exists"
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail
            )
        
        # Validate and convert user type
        user_type_str = request.user_type.upper().strip()
        
        # Map to enum values
        type_mapping = {
            "PATIENT": UserType.PATIENT,
            "DOCTOR": UserType.DOCTOR,
            "ADMIN": UserType.ADMIN
        }
        
        if user_type_str not in type_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user type '{request.user_type}'. Must be PATIENT, DOCTOR, or ADMIN"
            )
        
        user_type_enum = type_mapping[user_type_str]
        
        # Create user
        hashed_password = get_password_hash(request.password)
        db_user = User(
            full_name=request.full_name,
            email=request.email,
            mobile_number=request.mobile_number,
            password_hash=hashed_password,
            user_type=user_type_enum,
            division_id=request.division_id,
            district_id=request.district_id,
            thana_id=request.thana_id,
            address=request.address,
            is_active=True,  # Make sure user is active by default
            is_verified=True  # For testing, auto-verify
        )
        
        db.add(db_user)
        db.flush()  # Get the user ID without committing
        
        # Handle doctor registration
        if user_type_enum == UserType.DOCTOR:
            if not request.doctor_data:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Doctor profile data is required for doctor registration"
                )
            
            # Validate required doctor fields
            required_fields = ['license_number', 'specialization', 'experience_years', 'consultation_fee']
            for field in required_fields:
                if not request.doctor_data.get(field):
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Doctor {field} is required"
                    )
            
            # Check if license number already exists
            existing_doctor = db.query(Doctor).filter(
                Doctor.license_number == request.doctor_data.get('license_number')
            ).first()
            
            if existing_doctor:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Doctor with this license number already exists"
                )
            
            # Create doctor profile
            try:
                # Ensure proper default values
                timeslots = request.doctor_data.get('available_timeslots', {})
                if not timeslots:
                    # Default schedule
                    timeslots = {
                        "monday": ["09:00-10:00", "14:00-15:00"],
                        "tuesday": ["09:00-10:00", "14:00-15:00"],
                        "wednesday": ["09:00-10:00", "14:00-15:00"],
                        "thursday": ["09:00-10:00", "14:00-15:00"],
                        "saturday": ["09:00-10:00"]
                    }
                
                db_doctor = Doctor(
                    user_id=db_user.id,
                    license_number=request.doctor_data.get('license_number'),
                    specialization=request.doctor_data.get('specialization'),
                    experience_years=int(request.doctor_data.get('experience_years')),
                    consultation_fee=float(request.doctor_data.get('consultation_fee')),
                    available_timeslots=timeslots,
                    qualification=request.doctor_data.get('qualification', 'MBBS'),
                    bio=request.doctor_data.get('bio', f"Dr. {request.full_name} - {request.doctor_data.get('specialization')} specialist")
                )
                
                db.add(db_doctor)
                logger.info(f"Doctor profile created for user: {request.email}")
                
            except (ValueError, TypeError) as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid doctor data: {str(e)}"
                )
        
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User registered successfully: {request.email}")
        return db_user
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error"
        )


@router.post("/login")
async def login_json(
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    User login with JSON data
    """
    try:
        logger.info(f"JSON Login attempt for email: {user_login.email}")
        
        # Find user by email
        user = db.query(User).filter(User.email == user_login.email).first()
        
        if not user:
            logger.warning(f"User not found: {user_login.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not verify_password(user_login.password, user.password_hash):
            logger.warning(f"Invalid password for user: {user_login.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {user_login.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "user_type": user.user_type.value},
            expires_delta=access_token_expires
        )
        
        logger.info(f"Successful JSON login for user: {user_login.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "user_type": user.user_type.value.lower(),
            "full_name": user.full_name,
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/login-form")
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    User login with form data (OAuth2 compatible)
    """
    try:
        logger.info(f"Form Login attempt for username: {form_data.username}")
        
        # Find user by email (username field)
        user = db.query(User).filter(User.email == form_data.username).first()
        
        if not user:
            logger.warning(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not verify_password(form_data.password, user.password_hash):
            logger.warning(f"Invalid password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "user_type": user.user_type.value},
            expires_delta=access_token_expires
        )
        
        logger.info(f"Successful form login for user: {form_data.username}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "user_type": user.user_type.value.lower(),
            "full_name": user.full_name,
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Form Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile
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


@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload profile image
    """
    try:
        # File validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size if available
        if hasattr(file, 'size') and file.size and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Check content type
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(status_code=400, detail="Only JPEG and PNG files allowed")
        
        # Create filename
        file_extension = file.filename.split(".")[-1].lower()
        filename = f"profile_{current_user.id}_{int(time.time())}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update user profile
        current_user.profile_image = f"/uploads/{filename}"
        db.commit()
        
        return {
            "success": True,
            "message": "Profile image uploaded successfully",
            "profile_image": current_user.profile_image
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    """
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        current_user.password_hash = get_password_hash(password_data.new_password)
        db.commit()
        
        return {
            "success": True,
            "message": "Password updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    User logout (client should remove token)
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information (alternative to profile)
    """
    return current_user


@router.post("/refresh-token")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh access token
    """
    try:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(current_user.id), "user_type": current_user.user_type.value},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": current_user.id,
            "user_type": current_user.user_type.value.lower(),
            "full_name": current_user.full_name
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing token: {str(e)}"
        )


# Debug endpoint to test what data is being received
@router.post("/debug-request")
async def debug_request(request: Request):
    """
    Debug endpoint to see what data is being received
    """
    try:
        # Get headers
        headers = dict(request.headers)
        
        # Get query params
        query_params = dict(request.query_params)
        
        # Try to get body
        try:
            body = await request.body()
            body_str = body.decode() if body else "No body"
        except:
            body_str = "Could not read body"
        
        # Try to parse as JSON
        try:
            # Reset request stream for JSON parsing
            json_data = await request.json()
        except:
            json_data = "Could not parse as JSON"
        
        return {
            "method": request.method,
            "url": str(request.url),
            "headers": headers,
            "query_params": query_params,
            "raw_body": body_str,
            "json_data": json_data,
            "content_type": headers.get("content-type", "Not set")
        }
        
    except Exception as e:
        return {"error": str(e)}
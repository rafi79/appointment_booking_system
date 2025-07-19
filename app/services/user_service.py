from sqlalchemy.orm import Session
from typing import Optional, List
from fastapi import HTTPException, status

from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.doctor import DoctorCreate
from app.core.security import get_password_hash, verify_password


class UserService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_mobile(self, mobile: str) -> Optional[User]:
        """Get user by mobile number"""
        return self.db.query(User).filter(User.mobile_number == mobile).first()
    
    def create_user(self, user_data: UserCreate, doctor_data: Optional[DoctorCreate] = None) -> User:
        """Create a new user with optional doctor profile"""
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(
            (User.email == user_data.email) | (User.mobile_number == user_data.mobile_number)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or mobile number already exists"
            )
        
        # Validate doctor data if user type is doctor
        if user_data.user_type == UserType.DOCTOR and not doctor_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doctor profile data is required for doctor registration"
            )
        
        try:
            # Create user
            hashed_password = get_password_hash(user_data.password)
            db_user = User(
                full_name=user_data.full_name,
                email=user_data.email,
                mobile_number=user_data.mobile_number,
                password_hash=hashed_password,
                user_type=user_data.user_type,
                division_id=user_data.division_id,
                district_id=user_data.district_id,
                thana_id=user_data.thana_id,
                address=user_data.address
            )
            
            self.db.add(db_user)
            self.db.flush()  # Flush to get the user ID
            
            # Create doctor profile if needed
            if user_data.user_type == UserType.DOCTOR and doctor_data:
                # Check if license number already exists
                existing_doctor = self.db.query(Doctor).filter(
                    Doctor.license_number == doctor_data.license_number
                ).first()
                
                if existing_doctor:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Doctor with this license number already exists"
                    )
                
                db_doctor = Doctor(
                    user_id=db_user.id,
                    license_number=doctor_data.license_number,
                    specialization=doctor_data.specialization,
                    experience_years=doctor_data.experience_years,
                    consultation_fee=doctor_data.consultation_fee,
                    available_timeslots=doctor_data.available_timeslots,
                    qualification=doctor_data.qualification,
                    bio=doctor_data.bio
                )
                
                self.db.add(db_doctor)
            
            self.db.commit()
            self.db.refresh(db_user)
            
            return db_user
            
        except Exception as e:
            self.db.rollback()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
    
    def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        """Update user profile"""
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if mobile number is already taken by another user
        if user_update.mobile_number:
            existing_user = self.db.query(User).filter(
                User.mobile_number == user_update.mobile_number,
                User.id != user_id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mobile number already taken"
                )
        
        try:
            # Update user fields
            for field, value in user_update.dict(exclude_unset=True).items():
                setattr(user, field, value)
            
            self.db.commit()
            self.db.refresh(user)
            
            return user
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password"""
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        try:
            # Update password
            user.password_hash = get_password_hash(new_password)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )
    
    def toggle_user_status(self, user_id: int, admin_user_id: int) -> User:
        """Toggle user active status (Admin only)"""
        
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Don't allow deactivating other admins
        if user.user_type == UserType.ADMIN and user.id != admin_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate other admin users"
            )
        
        try:
            user.is_active = not user.is_active
            self.db.commit()
            self.db.refresh(user)
            
            return user
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user status"
            )
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        return user
    
    def get_users_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        user_type: Optional[UserType] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """Get users with filters"""
        
        query = self.db.query(User)
        
        if user_type:
            query = query.filter(User.user_type == user_type)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if search:
            query = query.filter(
                (User.full_name.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%")) |
                (User.mobile_number.ilike(f"%{search}%"))
            )
        
        return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
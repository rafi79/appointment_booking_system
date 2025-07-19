from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from app.models.user import UserType


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    mobile_number: str
    user_type: UserType
    division_id: int
    district_id: int
    thana_id: int
    address: Optional[str] = None


class UserCreate(UserBase):
    password: str
    
    @validator('full_name')
    def validate_name_simple(cls, v):
        if not v or not v.strip():
            raise ValueError('Full name is required')
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        return v.strip()
    
    @validator('mobile_number')
    def validate_mobile_simple(cls, v):
        if not v or not v.strip():
            raise ValueError('Mobile number is required')
        # Simple validation - just check if it contains numbers
        import re
        if not re.search(r'\d', v):
            raise ValueError('Mobile number must contain digits')
        return v.strip()
    
    @validator('password')
    def validate_password_simple(cls, v):
        if not v:
            raise ValueError('Password is required')
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    mobile_number: Optional[str] = None
    division_id: Optional[int] = None
    district_id: Optional[int] = None
    thana_id: Optional[int] = None
    address: Optional[str] = None
    
    @validator('full_name')
    def validate_name_simple(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Full name cannot be empty')
            if len(v.strip()) < 2:
                raise ValueError('Full name must be at least 2 characters')
            return v.strip()
        return v
    
    @validator('mobile_number')
    def validate_mobile_simple(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Mobile number cannot be empty')
            import re
            if not re.search(r'\d', v):
                raise ValueError('Mobile number must contain digits')
            return v.strip()
        return v


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    profile_image: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    id: int
    full_name: str
    email: str
    mobile_number: str
    user_type: UserType
    profile_image: Optional[str] = None
    division_name: Optional[str] = None
    district_name: Optional[str] = None
    thana_name: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password_simple(cls, v):
        if not v:
            raise ValueError('New password is required')
        if len(v) < 6:
            raise ValueError('New password must be at least 6 characters')
        return v
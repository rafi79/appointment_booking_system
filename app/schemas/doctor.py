from pydantic import BaseModel, validator
from typing import Optional, Dict, List
from app.schemas.user import UserResponse


class DoctorBase(BaseModel):
    license_number: str
    specialization: str
    experience_years: int
    consultation_fee: float
    available_timeslots: Dict[str, List[str]]
    qualification: Optional[str] = None
    bio: Optional[str] = None


class DoctorCreate(DoctorBase):
    @validator('license_number')
    def validate_license(cls, v):
        from app.utils.validators import validate_license_number
        is_valid, error = validate_license_number(v)
        if not is_valid:
            raise ValueError(error)
        return v
    
    @validator('consultation_fee')
    def validate_fee(cls, v):
        from app.utils.validators import validate_consultation_fee
        is_valid, error = validate_consultation_fee(v)
        if not is_valid:
            raise ValueError(error)
        return v
    
    @validator('available_timeslots')
    def validate_timeslots(cls, v):
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in v.keys():
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day: {day}")
            
            for timeslot in v[day]:
                from app.utils.validators import validate_appointment_time
                is_valid, error = validate_appointment_time(timeslot)
                if not is_valid:
                    raise ValueError(f"Invalid timeslot '{timeslot}': {error}")
        return v


class DoctorUpdate(BaseModel):
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    consultation_fee: Optional[float] = None
    available_timeslots: Optional[Dict[str, List[str]]] = None
    qualification: Optional[str] = None
    bio: Optional[str] = None
    
    @validator('consultation_fee')
    def validate_fee(cls, v):
        if v is not None:
            from app.utils.validators import validate_consultation_fee
            is_valid, error = validate_consultation_fee(v)
            if not is_valid:
                raise ValueError(error)
        return v


class DoctorResponse(DoctorBase):
    id: int
    user_id: int
    user: UserResponse
    
    class Config:
        from_attributes = True


class DoctorSearch(BaseModel):
    specialization: Optional[str] = None
    division_id: Optional[int] = None
    district_id: Optional[int] = None
    min_fee: Optional[float] = None
    max_fee: Optional[float] = None
    available_day: Optional[str] = None


class DoctorPublic(BaseModel):
    id: int
    full_name: str
    specialization: str
    experience_years: int
    consultation_fee: float
    qualification: Optional[str] = None
    bio: Optional[str] = None
    available_timeslots: Dict[str, List[str]]
    division_name: str
    district_name: str
    thana_name: str
    profile_image: Optional[str] = None
    
    class Config:
        from_attributes = True
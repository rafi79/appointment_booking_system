from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime, date
from app.models.appointment import AppointmentStatus


class AppointmentBase(BaseModel):
    doctor_id: int
    appointment_date: date
    appointment_time: str
    notes: Optional[str] = None
    symptoms: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    """Simplified appointment creation without complex validators"""
    
    @validator('doctor_id')
    def validate_doctor_id(cls, v):
        if v <= 0:
            raise ValueError('Doctor ID must be positive')
        return v
    
    @validator('appointment_time')
    def validate_time_simple(cls, v):
        if not v or not v.strip():
            raise ValueError('Appointment time is required')
        return v.strip()
    
    @validator('appointment_date')
    def validate_date_simple(cls, v):
        if not v:
            raise ValueError('Appointment date is required')
        
        # Simple check: can't be in the past
        from datetime import date as dt_date
        if v < dt_date.today():
            raise ValueError('Cannot book appointments for past dates')
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "doctor_id": 1,
                "appointment_date": "2025-07-21",
                "appointment_time": "09:00-10:00",
                "symptoms": "Fever and headache",
                "notes": "Patient has been experiencing symptoms for 3 days"
            }
        }


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[str] = None
    notes: Optional[str] = None
    symptoms: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    
    @validator('appointment_date')
    def validate_date_simple(cls, v):
        if v is not None:
            from datetime import date as dt_date
            if v < dt_date.today():
                raise ValueError('Cannot schedule appointments for past dates')
        return v


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    doctor_notes: Optional[str] = None
    prescription: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: str
    status: AppointmentStatus
    notes: Optional[str] = None
    symptoms: Optional[str] = None
    doctor_notes: Optional[str] = None
    prescription: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Related data
    patient_name: str
    patient_mobile: str
    doctor_name: str
    doctor_specialization: str
    consultation_fee: float
    
    class Config:
        from_attributes = True


class AppointmentSearch(BaseModel):
    doctor_id: Optional[int] = None
    patient_id: Optional[int] = None
    status: Optional[AppointmentStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    specialization: Optional[str] = None


class AppointmentStats(BaseModel):
    total_appointments: int
    pending_appointments: int
    confirmed_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    today_appointments: int
    this_month_appointments: int


class MonthlyReport(BaseModel):
    doctor_id: int
    doctor_name: str
    specialization: str
    month: int
    year: int
    total_patients: int
    total_appointments: int
    total_earnings: float
    completed_appointments: int
    cancelled_appointments: int
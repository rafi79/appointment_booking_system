"""Database models for the appointment booking system"""

# Import all models to ensure proper initialization order
from .location import Division, District, Thana
from .user import User, UserType
from .doctor import Doctor
from .appointment import Appointment, AppointmentStatus

# Export all models
__all__ = [
    "Division", "District", "Thana",
    "User", "UserType", 
    "Doctor",
    "Appointment", "AppointmentStatus"
]
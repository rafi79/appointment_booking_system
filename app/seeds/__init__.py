# Import all models here to ensure proper initialization order
from app.models.location import Division, District, Thana
from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus

# Export all models
__all__ = [
    "Division", "District", "Thana",
    "User", "UserType", 
    "Doctor",
    "Appointment", "AppointmentStatus"
]
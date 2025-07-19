from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Doctor(Base):
    __tablename__ = "doctors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    license_number = Column(String(50), unique=True, nullable=False)
    specialization = Column(String(100), nullable=False)
    experience_years = Column(Integer, nullable=False)
    consultation_fee = Column(Float, nullable=False)
    
    # Available timeslots stored as JSON
    # Format: {"monday": ["10:00-11:00", "14:00-15:00"], "tuesday": [...]}
    available_timeslots = Column(JSON, nullable=False)
    
    # Additional fields
    qualification = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="doctor_profile")
    appointments = relationship("Appointment", back_populates="doctor")
    
    def __str__(self):
        return f"Dr. {self.user.full_name} ({self.specialization})"
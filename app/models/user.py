from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserType(str, enum.Enum):
    ADMIN = "ADMIN"      # Changed to uppercase to match frontend
    DOCTOR = "DOCTOR"    # Changed to uppercase to match frontend
    PATIENT = "PATIENT"  # Changed to uppercase to match frontend


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    mobile_number = Column(String(14), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    user_type = Column(Enum(UserType), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    profile_image = Column(String(255), nullable=True)
    
    # Location fields
    division_id = Column(Integer, ForeignKey("divisions.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    thana_id = Column(Integer, ForeignKey("thanas.id"), nullable=False)
    address = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    division = relationship("Division", back_populates="users")
    district = relationship("District", back_populates="users")
    thana = relationship("Thana", back_populates="users")
    
    # Doctor relationship (if user is a doctor)
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)
    
    # Patient appointments
    patient_appointments = relationship(
        "Appointment",
        back_populates="patient",
        foreign_keys="[Appointment.patient_id]"
    )
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
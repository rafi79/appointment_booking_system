from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    
    # Appointment details - FIXED: Use Date instead of DateTime for appointment_date
    appointment_date = Column(Date, nullable=False)  # Changed from DateTime to Date
    appointment_time = Column(String(20), nullable=False)  # Format: "10:00-11:00"
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING)
    
    # Patient notes and symptoms
    notes = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=True)
    
    # Doctor's notes (filled after appointment)
    doctor_notes = Column(Text, nullable=True)
    prescription = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    patient = relationship("User", back_populates="patient_appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    
    def __str__(self):
        return f"Appointment #{self.id} - {self.patient.full_name} with Dr. {self.doctor.user.full_name}"
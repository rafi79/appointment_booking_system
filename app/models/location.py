from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Division(Base):
    __tablename__ = "divisions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    
    # Relationships
    districts = relationship("District", back_populates="division")
    users = relationship("User", back_populates="division")
    
    def __str__(self):
        return self.name


class District(Base):
    __tablename__ = "districts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    division_id = Column(Integer, ForeignKey("divisions.id"), nullable=False)
    
    # Relationships
    division = relationship("Division", back_populates="districts")
    thanas = relationship("Thana", back_populates="district")
    users = relationship("User", back_populates="district")
    
    def __str__(self):
        return f"{self.name}, {self.division.name}"


class Thana(Base):
    __tablename__ = "thanas"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    
    # Relationships
    district = relationship("District", back_populates="thanas")
    users = relationship("User", back_populates="thana")
    
    def __str__(self):
        return f"{self.name}, {self.district.name}, {self.district.division.name}"
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "appointment_db"
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Email
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # File Upload
    UPLOAD_DIR: str = "uploads/"
    MAX_FILE_SIZE: int = 5242880  # 5MB
    
    # Application
    APP_NAME: str = "Appointment Booking System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
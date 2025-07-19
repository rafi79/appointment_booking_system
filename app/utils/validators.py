import re
from typing import Tuple
from datetime import datetime, time, date
from fastapi import UploadFile


def validate_mobile_number(mobile: str) -> Tuple[bool, str]:
    """
    Validate mobile number format (+88 followed by 11 digits)
    """
    if not mobile:
        return False, "Mobile number is required"
    
    # Clean the mobile number
    clean_mobile = re.sub(r'[^\d+]', '', mobile)
    
    # Bangladesh mobile number patterns
    patterns = [
        r'^\+8801[3-9]\d{8}$',  # +8801XXXXXXXXX
        r'^8801[3-9]\d{8}$',    # 8801XXXXXXXXX
        r'^01[3-9]\d{8}$',      # 01XXXXXXXXX
    ]
    
    for pattern in patterns:
        if re.match(pattern, clean_mobile):
            return True, ""
    
    return False, "Mobile number must be in format +8801XXXXXXXXX or 01XXXXXXXXX"


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format
    """
    if not email:
        return False, "Email is required"
    
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, ""


def validate_appointment_time(appointment_time: str) -> Tuple[bool, str]:
    """
    Validate appointment time format (HH:MM-HH:MM)
    """
    if not appointment_time:
        return False, "Appointment time is required"
    
    pattern = r"^([01]?[0-9]|2[0-3]):[0-5][0-9]-([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    if not re.match(pattern, appointment_time):
        return False, "Time must be in format HH:MM-HH:MM"
    
    try:
        start_time, end_time = appointment_time.split("-")
        start_hour, start_min = map(int, start_time.split(":"))
        end_hour, end_min = map(int, end_time.split(":"))
        
        start_time_obj = time(start_hour, start_min)
        end_time_obj = time(end_hour, end_min)
        
        if start_time_obj >= end_time_obj:
            return False, "Start time must be before end time"
            
        # Check if within business hours (6 AM to 10 PM)
        business_start = time(6, 0)
        business_end = time(22, 0)
        
        if start_time_obj < business_start or end_time_obj > business_end:
            return False, "Appointment must be within business hours (6:00 AM - 10:00 PM)"
            
    except ValueError:
        return False, "Invalid time format"
    
    return True, ""


def validate_appointment_date(appointment_date: date) -> Tuple[bool, str]:
    """
    Validate appointment date (must be in the future)
    """
    if not appointment_date:
        return False, "Appointment date is required"
    
    today = date.today()
    if appointment_date < today:
        return False, "Appointment date must be in the future"
    
    # Cannot book more than 3 months in advance
    from datetime import timedelta
    max_date = today + timedelta(days=90)
    if appointment_date > max_date:
        return False, "Cannot book appointments more than 3 months in advance"
    
    return True, ""


def validate_file_upload(file: UploadFile, max_size: int = 5242880) -> Tuple[bool, str]:
    """
    Validate file upload (size and type)
    """
    if not file:
        return False, "No file provided"
    
    # Check file size
    if hasattr(file, 'size') and file.size and file.size > max_size:
        return False, f"File size must be less than {max_size // (1024*1024)}MB"
    
    # Check file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if hasattr(file, 'content_type') and file.content_type not in allowed_types:
        return False, "Only JPEG and PNG files are allowed"
    
    return True, ""


def validate_license_number(license_number: str) -> Tuple[bool, str]:
    """
    Validate doctor license number format
    """
    if not license_number:
        return False, "License number is required"
    
    # Clean the license number
    clean_license = license_number.strip().upper()
    
    # Simple validation - can be customized based on requirements
    if len(clean_license) < 3 or len(clean_license) > 20:
        return False, "License number must be between 3 and 20 characters"
    
    # Allow letters and numbers
    if not re.match(r"^[A-Z0-9]+$", clean_license):
        return False, "License number must contain only uppercase letters and numbers"
    
    return True, ""


def validate_consultation_fee(fee: float) -> Tuple[bool, str]:
    """
    Validate consultation fee
    """
    if fee is None:
        return False, "Consultation fee is required"
    
    if not isinstance(fee, (int, float)):
        return False, "Consultation fee must be a number"
    
    if fee < 0:
        return False, "Consultation fee cannot be negative"
    
    if fee > 50000:  # Maximum fee limit
        return False, "Consultation fee cannot exceed 50,000 BDT"
    
    return True, ""


def validate_experience_years(years: int) -> Tuple[bool, str]:
    """
    Validate doctor experience years
    """
    if years is None:
        return False, "Experience years is required"
    
    if not isinstance(years, int):
        return False, "Experience years must be an integer"
    
    if years < 0:
        return False, "Experience years cannot be negative"
    
    if years > 60:
        return False, "Experience years cannot exceed 60"
    
    return True, ""
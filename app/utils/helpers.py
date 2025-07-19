"""Helper utility functions"""

from typing import Any, Dict, List, Optional
import json
import hashlib
import secrets
from datetime import datetime, date, timedelta
from pathlib import Path
import os

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def format_date(dt: date) -> str:
    """Format date for display"""
    return dt.strftime("%Y-%m-%d")

def format_time(time_str: str) -> str:
    """Format time slot for display"""
    return time_str.replace("-", " - ")

def serialize_json(obj: Any) -> str:
    """Serialize object to JSON string"""
    def json_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return json.dumps(obj, default=json_serializer)

def generate_filename(original_filename: str, user_id: int) -> str:
    """Generate unique filename for uploads"""
    timestamp = int(datetime.now().timestamp())
    file_extension = Path(original_filename).suffix
    random_string = secrets.token_hex(8)
    return f"user_{user_id}_{timestamp}_{random_string}{file_extension}"

def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def get_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def ensure_directory_exists(directory_path: str) -> None:
    """Ensure directory exists, create if it doesn't"""
    Path(directory_path).mkdir(parents=True, exist_ok=True)

def clean_phone_number(phone: str) -> str:
    """Clean and format phone number"""
    # Remove all non-digit characters except +
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Ensure it starts with +88 for Bangladesh
    if not cleaned.startswith('+88'):
        if cleaned.startswith('88'):
            cleaned = '+' + cleaned
        elif cleaned.startswith('01'):
            cleaned = '+88' + cleaned
        else:
            # Assume it's a local number without country code
            cleaned = '+88' + cleaned
    
    return cleaned

def get_business_days(start_date: date, end_date: date) -> List[date]:
    """Get list of business days between two dates (excluding weekends)"""
    business_days = []
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday = 0, Sunday = 6
            business_days.append(current_date)
        current_date += timedelta(days=1)
    
    return business_days

def parse_time_slot(time_slot: str) -> tuple[str, str]:
    """Parse time slot string into start and end times"""
    try:
        start_time, end_time = time_slot.split('-')
        return start_time.strip(), end_time.strip()
    except ValueError:
        raise ValueError(f"Invalid time slot format: {time_slot}")

def is_time_slot_overlap(slot1: str, slot2: str) -> bool:
    """Check if two time slots overlap"""
    start1, end1 = parse_time_slot(slot1)
    start2, end2 = parse_time_slot(slot2)
    
    # Convert to comparable format (assuming HH:MM format)
    def time_to_minutes(time_str: str) -> int:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    
    start1_min = time_to_minutes(start1)
    end1_min = time_to_minutes(end1)
    start2_min = time_to_minutes(start2)
    end2_min = time_to_minutes(end2)
    
    # Check for overlap
    return not (end1_min <= start2_min or end2_min <= start1_min)

def get_week_dates(date_input: date) -> Dict[str, date]:
    """Get all dates for the week containing the given date"""
    # Get Monday of the week
    monday = date_input - timedelta(days=date_input.weekday())
    
    week_dates = {}
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    for i, day in enumerate(days):
        week_dates[day] = monday + timedelta(days=i)
    
    return week_dates

def format_currency(amount: float, currency: str = "BDT") -> str:
    """Format currency amount"""
    return f"{amount:,.2f} {currency}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename

def paginate_query(query, page: int = 1, per_page: int = 20):
    """Add pagination to SQLAlchemy query"""
    offset = (page - 1) * per_page
    return query.offset(offset).limit(per_page)

def create_response_metadata(total_items: int, page: int, per_page: int) -> Dict[str, Any]:
    """Create pagination metadata for API responses"""
    total_pages = (total_items + per_page - 1) // per_page
    
    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

def validate_bangladesh_location(division: str, district: str, thana: str) -> bool:
    """Validate if the location combination is valid for Bangladesh"""
    # This is a simplified validation - in production, you'd check against a comprehensive database
    valid_combinations = {
        "Dhaka": {
            "Dhaka": ["Dhanmondi", "Gulshan", "Uttara", "Ramna", "Tejgaon"],
            "Gazipur": ["Gazipur Sadar", "Kaliakair", "Kapasia"],
            "Manikganj": ["Manikganj Sadar", "Shibalaya", "Saturia"]
        },
        "Chittagong": {
            "Chittagong": ["Kotwali", "Pahartali", "Bayazid", "Halishahar"],
            "Cox's Bazar": ["Cox's Bazar Sadar", "Chakaria", "Teknaf"],
            "Comilla": ["Comilla Sadar", "Burichang", "Brahmanpara"]
        },
        # Add more as needed
    }
    
    return (division in valid_combinations and 
            district in valid_combinations[division] and 
            thana in valid_combinations[division][district])

def get_appointment_status_color(status: str) -> str:
    """Get color code for appointment status"""
    status_colors = {
        "pending": "#ffc107",    # yellow
        "confirmed": "#28a745",  # green
        "completed": "#007bff",  # blue
        "cancelled": "#dc3545"   # red
    }
    return status_colors.get(status.lower(), "#6c757d")  # default gray

def generate_appointment_reference(appointment_id: int) -> str:
    """Generate appointment reference number"""
    return f"APT{appointment_id:06d}"

def mask_email(email: str) -> str:
    """Mask email for privacy (show only first char and domain)"""
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        return email
    
    masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"

def mask_phone(phone: str) -> str:
    """Mask phone number for privacy"""
    if len(phone) <= 6:
        return phone
    
    return phone[:3] + '*' * (len(phone) - 6) + phone[-3:]

def get_time_greeting() -> str:
    """Get appropriate greeting based on current time"""
    current_hour = datetime.now().hour
    
    if 5 <= current_hour < 12:
        return "Good Morning"
    elif 12 <= current_hour < 17:
        return "Good Afternoon"
    elif 17 <= current_hour < 21:
        return "Good Evening"
    else:
        return "Good Night"
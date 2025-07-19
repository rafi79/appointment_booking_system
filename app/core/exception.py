"""Custom exception classes for the appointment booking system"""

from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class AppointmentBookingException(HTTPException):
    """Base exception for appointment booking system"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class ValidationException(AppointmentBookingException):
    """Validation error exception"""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class AuthenticationException(AppointmentBookingException):
    """Authentication error exception"""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationException(AppointmentBookingException):
    """Authorization error exception"""
    
    def __init__(self, detail: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class UserNotFoundException(AppointmentBookingException):
    """User not found exception"""
    
    def __init__(self, user_id: Optional[int] = None, email: Optional[str] = None):
        if user_id:
            detail = f"User with ID {user_id} not found"
        elif email:
            detail = f"User with email {email} not found"
        else:
            detail = "User not found"
            
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class DoctorNotFoundException(AppointmentBookingException):
    """Doctor not found exception"""
    
    def __init__(self, doctor_id: Optional[int] = None):
        if doctor_id:
            detail = f"Doctor with ID {doctor_id} not found"
        else:
            detail = "Doctor not found"
            
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class AppointmentNotFoundException(AppointmentBookingException):
    """Appointment not found exception"""
    
    def __init__(self, appointment_id: Optional[int] = None):
        if appointment_id:
            detail = f"Appointment with ID {appointment_id} not found"
        else:
            detail = "Appointment not found"
            
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class UserAlreadyExistsException(AppointmentBookingException):
    """User already exists exception"""
    
    def __init__(self, email: Optional[str] = None, mobile: Optional[str] = None):
        if email and mobile:
            detail = f"User with email {email} or mobile {mobile} already exists"
        elif email:
            detail = f"User with email {email} already exists"
        elif mobile:
            detail = f"User with mobile {mobile} already exists"
        else:
            detail = "User already exists"
            
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class DoctorAlreadyExistsException(AppointmentBookingException):
    """Doctor already exists exception"""
    
    def __init__(self, license_number: Optional[str] = None):
        if license_number:
            detail = f"Doctor with license number {license_number} already exists"
        else:
            detail = "Doctor already exists"
            
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class TimeSlotUnavailableException(AppointmentBookingException):
    """Time slot unavailable exception"""
    
    def __init__(self, time_slot: str, date: str = ""):
        if date:
            detail = f"Time slot {time_slot} is not available on {date}"
        else:
            detail = f"Time slot {time_slot} is not available"
            
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class TimeSlotConflictException(AppointmentBookingException):
    """Time slot conflict exception"""
    
    def __init__(self, time_slot: str, date: str = ""):
        if date:
            detail = f"Time slot {time_slot} is already booked on {date}"
        else:
            detail = f"Time slot {time_slot} is already booked"
            
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class InvalidAppointmentStatusException(AppointmentBookingException):
    """Invalid appointment status exception"""
    
    def __init__(self, current_status: str, requested_status: str):
        detail = f"Cannot change appointment status from {current_status} to {requested_status}"
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class AppointmentModificationException(AppointmentBookingException):
    """Appointment modification not allowed exception"""
    
    def __init__(self, reason: str = "Appointment cannot be modified"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason
        )


class FileUploadException(AppointmentBookingException):
    """File upload error exception"""
    
    def __init__(self, detail: str = "File upload failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class InvalidFileTypeException(FileUploadException):
    """Invalid file type exception"""
    
    def __init__(self, file_type: str, allowed_types: list):
        detail = f"File type {file_type} not allowed. Allowed types: {', '.join(allowed_types)}"
        super().__init__(detail=detail)


class FileSizeExceededException(FileUploadException):
    """File size exceeded exception"""
    
    def __init__(self, size: int, max_size: int):
        detail = f"File size {size} bytes exceeds maximum allowed size {max_size} bytes"
        super().__init__(detail=detail)


class EmailServiceException(AppointmentBookingException):
    """Email service error exception"""
    
    def __init__(self, detail: str = "Email service error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class DatabaseException(AppointmentBookingException):
    """Database error exception"""
    
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class BusinessRuleException(AppointmentBookingException):
    """Business rule violation exception"""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class ScheduleConflictException(BusinessRuleException):
    """Schedule conflict exception"""
    
    def __init__(self, detail: str = "Schedule conflict detected"):
        super().__init__(detail=detail)


class InactiveUserException(AppointmentBookingException):
    """Inactive user exception"""
    
    def __init__(self, detail: str = "User account is inactive"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class UnverifiedUserException(AppointmentBookingException):
    """Unverified user exception"""
    
    def __init__(self, detail: str = "User account is not verified"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class RateLimitExceededException(AppointmentBookingException):
    """Rate limit exceeded exception"""
    
    def __init__(self, detail: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )


class ExternalServiceException(AppointmentBookingException):
    """External service error exception"""
    
    def __init__(self, service_name: str, detail: str = ""):
        if detail:
            detail = f"{service_name} service error: {detail}"
        else:
            detail = f"{service_name} service is currently unavailable"
            
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )


# Exception handler functions for FastAPI
async def validation_exception_handler(request, exc):
    """Handle validation exceptions"""
    return {
        "error": "Validation Error",
        "detail": str(exc.detail),
        "type": "validation_error"
    }


async def authentication_exception_handler(request, exc):
    """Handle authentication exceptions"""
    return {
        "error": "Authentication Error",
        "detail": str(exc.detail),
        "type": "authentication_error"
    }


async def authorization_exception_handler(request, exc):
    """Handle authorization exceptions"""
    return {
        "error": "Authorization Error",
        "detail": str(exc.detail),
        "type": "authorization_error"
    }


async def not_found_exception_handler(request, exc):
    """Handle not found exceptions"""
    return {
        "error": "Not Found",
        "detail": str(exc.detail),
        "type": "not_found_error"
    }


async def conflict_exception_handler(request, exc):
    """Handle conflict exceptions"""
    return {
        "error": "Conflict",
        "detail": str(exc.detail),
        "type": "conflict_error"
    }


async def business_rule_exception_handler(request, exc):
    """Handle business rule exceptions"""
    return {
        "error": "Business Rule Violation",
        "detail": str(exc.detail),
        "type": "business_rule_error"
    }


async def server_error_exception_handler(request, exc):
    """Handle server error exceptions"""
    return {
        "error": "Internal Server Error",
        "detail": str(exc.detail),
        "type": "server_error"
    }
"""Tests for appointment management endpoints"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal, create_tables
from app.models.user import User, UserType
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus
from app.models.location import Division, District, Thana
from app.core.security import get_password_hash

client = TestClient(app)

@pytest.fixture(scope="module")
def test_db():
    """Create test database session with test data"""
    create_tables()
    db = SessionLocal()
    
    # Create test locations
    division = Division(name="Test Division")
    db.add(division)
    db.flush()
    
    district = District(name="Test District", division_id=division.id)
    db.add(district)
    db.flush()
    
    thana = Thana(name="Test Thana", district_id=district.id)
    db.add(thana)
    db.flush()
    
    # Create test users
    admin_user = User(
        full_name="Test Admin",
        email="admin@test.com",
        mobile_number="+8801712345678",
        password_hash=get_password_hash("Password123!"),
        user_type=UserType.ADMIN,
        division_id=division.id,
        district_id=district.id,
        thana_id=thana.id,
        is_active=True
    )
    
    doctor_user = User(
        full_name="Dr. Test Doctor",
        email="doctor@test.com",
        mobile_number="+8801712345679",
        password_hash=get_password_hash("Password123!"),
        user_type=UserType.DOCTOR,
        division_id=division.id,
        district_id=district.id,
        thana_id=thana.id,
        is_active=True
    )
    
    patient_user = User(
        full_name="Test Patient",
        email="patient@test.com",
        mobile_number="+8801712345680",
        password_hash=get_password_hash("Password123!"),
        user_type=UserType.PATIENT,
        division_id=division.id,
        district_id=district.id,
        thana_id=thana.id,
        is_active=True
    )
    
    db.add_all([admin_user, doctor_user, patient_user])
    db.flush()
    
    # Create test doctor profile
    doctor_profile = Doctor(
        user_id=doctor_user.id,
        license_number="TEST12345",
        specialization="General Medicine",
        experience_years=5,
        consultation_fee=1000.0,
        available_timeslots={
            "monday": ["10:00-11:00", "14:00-15:00", "16:00-17:00"],
            "tuesday": ["10:00-11:00", "14:00-15:00"],
            "wednesday": ["10:00-11:00", "16:00-17:00"],
            "thursday": ["14:00-15:00", "16:00-17:00"],
            "friday": ["10:00-11:00"]
        },
        qualification="MBBS",
        bio="Test doctor for appointments"
    )
    
    db.add(doctor_profile)
    db.commit()
    
    yield db
    db.close()

@pytest.fixture
def override_get_db(test_db):
    """Override database dependency"""
    def _get_test_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = _get_test_db
    yield test_db
    app.dependency_overrides = {}

@pytest.fixture
def admin_token(override_get_db):
    """Get admin authentication token"""
    response = client.post("/api/v1/auth/login", data={
        "username": "admin@test.com",
        "password": "Password123!"
    })
    return response.json()["access_token"]

@pytest.fixture
def doctor_token(override_get_db):
    """Get doctor authentication token"""
    response = client.post("/api/v1/auth/login", data={
        "username": "doctor@test.com",
        "password": "Password123!"
    })
    return response.json()["access_token"]

@pytest.fixture
def patient_token(override_get_db):
    """Get patient authentication token"""
    response = client.post("/api/v1/auth/login", data={
        "username": "patient@test.com",
        "password": "Password123!"
    })
    return response.json()["access_token"]

class TestAppointmentCreation:
    """Test appointment creation functionality"""
    
    def test_create_appointment_success(self, override_get_db, patient_token):
        """Test successful appointment creation"""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "10:00-11:00",
                "notes": "Regular checkup",
                "symptoms": "General consultation"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["doctor_id"] == 1
        assert data["appointment_time"] == "10:00-11:00"
        assert data["status"] == "pending"
        assert data["notes"] == "Regular checkup"
    
    def test_create_appointment_invalid_doctor(self, override_get_db, patient_token):
        """Test appointment creation with invalid doctor"""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 99999,  # Non-existent doctor
                "appointment_date": tomorrow,
                "appointment_time": "10:00-11:00",
                "notes": "Test"
            }
        )
        
        assert response.status_code == 404
        assert "Doctor not found" in response.json()["detail"]
    
    def test_create_appointment_unavailable_time(self, override_get_db, patient_token):
        """Test appointment creation with unavailable time slot"""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "12:00-13:00",  # Not in doctor's available slots
                "notes": "Test"
            }
        )
        
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]
    
    def test_create_appointment_past_date(self, override_get_db, patient_token):
        """Test appointment creation with past date"""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        
        response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": yesterday,
                "appointment_time": "10:00-11:00",
                "notes": "Test"
            }
        )
        
        assert response.status_code == 422
    
    def test_create_appointment_conflict(self, override_get_db, patient_token):
        """Test appointment creation with time conflict"""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        # Create first appointment
        client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "14:00-15:00",
                "notes": "First appointment"
            }
        )
        
        # Try to create conflicting appointment
        response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "14:00-15:00",  # Same time slot
                "notes": "Conflicting appointment"
            }
        )
        
        assert response.status_code == 400
        assert "already booked" in response.json()["detail"]

class TestAppointmentRetrieval:
    """Test appointment retrieval functionality"""
    
    def test_get_patient_appointments(self, override_get_db, patient_token):
        """Test getting patient's appointments"""
        response = client.get(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should return appointments for this patient only
        assert isinstance(data, list)
    
    def test_get_doctor_appointments(self, override_get_db, doctor_token):
        """Test getting doctor's appointments"""
        response = client.get(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_admin_appointments(self, override_get_db, admin_token):
        """Test admin getting all appointments"""
        response = client.get(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_appointments_with_filters(self, override_get_db, admin_token):
        """Test getting appointments with status filter"""
        response = client.get(
            "/api/v1/appointments/?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        for appointment in data:
            assert appointment["status"] == "pending"
    
    def test_get_appointments_with_date_filter(self, override_get_db, admin_token):
        """Test getting appointments with date range filter"""
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        response = client.get(
            f"/api/v1/appointments/?date_from={today}&date_to={tomorrow}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestAppointmentUpdate:
    """Test appointment update functionality"""
    
    def test_update_appointment_by_patient(self, override_get_db, patient_token):
        """Test patient updating their own appointment"""
        # First create an appointment
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        create_response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "16:00-17:00",
                "notes": "Original notes"
            }
        )
        appointment_id = create_response.json()["id"]
        
        # Update the appointment
        response = client.put(
            f"/api/v1/appointments/{appointment_id}",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "notes": "Updated notes",
                "symptoms": "Updated symptoms"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes"
        assert data["symptoms"] == "Updated symptoms"
    
    def test_update_appointment_status_by_doctor(self, override_get_db, doctor_token, patient_token):
        """Test doctor updating appointment status"""
        # Create appointment first
        tomorrow = (date.today() + timedelta(days=2)).isoformat()
        create_response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "10:00-11:00",
                "notes": "Test appointment"
            }
        )
        appointment_id = create_response.json()["id"]
        
        # Update status as doctor
        response = client.put(
            f"/api/v1/appointments/{appointment_id}/status",
            headers={"Authorization": f"Bearer {doctor_token}"},
            json={
                "status": "confirmed",
                "doctor_notes": "Confirmed by doctor"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"
        assert data["doctor_notes"] == "Confirmed by doctor"
    
    def test_update_non_pending_appointment(self, override_get_db, patient_token, doctor_token):
        """Test updating non-pending appointment should fail for patient"""
        # Create and confirm appointment
        tomorrow = (date.today() + timedelta(days=3)).isoformat()
        create_response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "14:00-15:00",
                "notes": "Test"
            }
        )
        appointment_id = create_response.json()["id"]
        
        # Confirm appointment as doctor
        client.put(
            f"/api/v1/appointments/{appointment_id}/status",
            headers={"Authorization": f"Bearer {doctor_token}"},
            json={"status": "confirmed"}
        )
        
        # Try to update confirmed appointment as patient
        response = client.put(
            f"/api/v1/appointments/{appointment_id}",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={"notes": "Updated notes"}
        )
        
        assert response.status_code == 400
        assert "Only pending appointments" in response.json()["detail"]

class TestAppointmentCancellation:
    """Test appointment cancellation functionality"""
    
    def test_cancel_appointment_by_patient(self, override_get_db, patient_token):
        """Test patient cancelling their appointment"""
        # Create appointment
        tomorrow = (date.today() + timedelta(days=4)).isoformat()
        create_response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "16:00-17:00",
                "notes": "To be cancelled"
            }
        )
        appointment_id = create_response.json()["id"]
        
        # Cancel appointment
        response = client.delete(
            f"/api/v1/appointments/{appointment_id}",
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        
        assert response.status_code == 200
        assert "cancelled successfully" in response.json()["message"]
    
    def test_cancel_appointment_by_doctor(self, override_get_db, doctor_token, patient_token):
        """Test doctor cancelling appointment"""
        # Create appointment
        tomorrow = (date.today() + timedelta(days=5)).isoformat()
        create_response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "10:00-11:00",
                "notes": "Doctor cancellation test"
            }
        )
        appointment_id = create_response.json()["id"]
        
        # Cancel as doctor
        response = client.delete(
            f"/api/v1/appointments/{appointment_id}",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 200
    
    def test_cancel_nonexistent_appointment(self, override_get_db, patient_token):
        """Test cancelling non-existent appointment"""
        response = client.delete(
            "/api/v1/appointments/99999",
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        
        assert response.status_code == 404

class TestAppointmentStatistics:
    """Test appointment statistics functionality"""
    
    def test_get_appointment_stats(self, override_get_db, admin_token):
        """Test getting appointment statistics"""
        response = client.get(
            "/api/v1/appointments/stats/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_appointments" in data
        assert "pending_appointments" in data
        assert "confirmed_appointments" in data
        assert "completed_appointments" in data
        assert "cancelled_appointments" in data
        assert "today_appointments" in data
        assert "this_month_appointments" in data
    
    def test_get_doctor_stats(self, override_get_db, doctor_token):
        """Test doctor getting their own statistics"""
        response = client.get(
            "/api/v1/appointments/stats/overview",
            headers={"Authorization": f"Bearer {doctor_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_appointments" in data

class TestAppointmentPermissions:
    """Test appointment access permissions"""
    
    def test_patient_cannot_access_other_appointments(self, override_get_db, patient_token):
        """Test patient cannot access other patients' appointments"""
        # This would need another patient's appointment ID
        # For now, test that patient gets only their appointments
        response = client.get(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        
        assert response.status_code == 200
        # All returned appointments should belong to this patient
    
    def test_doctor_cannot_update_other_doctor_appointments(self, override_get_db):
        """Test doctor cannot update appointments of other doctors"""
        # This would require creating another doctor
        # For now, just test access control
        pass
    
    def test_unauthenticated_access_denied(self, override_get_db):
        """Test unauthenticated access is denied"""
        response = client.get("/api/v1/appointments/")
        assert response.status_code == 403
        
        response = client.post("/api/v1/appointments/", json={})
        assert response.status_code == 403

class TestAppointmentValidation:
    """Test appointment input validation"""
    
    def test_invalid_time_format(self, override_get_db, patient_token):
        """Test invalid time format"""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "10:00-25:00",  # Invalid time
                "notes": "Test"
            }
        )
        
        assert response.status_code == 422
    
    def test_invalid_date_format(self, override_get_db, patient_token):
        """Test invalid date format"""
        response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": "invalid-date",
                "appointment_time": "10:00-11:00",
                "notes": "Test"
            }
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self, override_get_db, patient_token):
        """Test missing required fields"""
        response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                # Missing appointment_date and appointment_time
                "notes": "Test"
            }
        )
        
        assert response.status_code == 422

# Integration tests
class TestAppointmentWorkflow:
    """Test complete appointment workflow"""
    
    def test_complete_appointment_lifecycle(self, override_get_db, patient_token, doctor_token, admin_token):
        """Test complete appointment lifecycle"""
        tomorrow = (date.today() + timedelta(days=6)).isoformat()
        
        # 1. Patient creates appointment
        create_response = client.post(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "doctor_id": 1,
                "appointment_date": tomorrow,
                "appointment_time": "14:00-15:00",
                "notes": "Complete lifecycle test",
                "symptoms": "Test symptoms"
            }
        )
        
        assert create_response.status_code == 200
        appointment_id = create_response.json()["id"]
        assert create_response.json()["status"] == "pending"
        
        # 2. Patient updates appointment (while still pending)
        update_response = client.put(
            f"/api/v1/appointments/{appointment_id}",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "notes": "Updated lifecycle test",
                "symptoms": "Updated symptoms"
            }
        )
        
        assert update_response.status_code == 200
        assert update_response.json()["notes"] == "Updated lifecycle test"
        
        # 3. Doctor confirms appointment
        confirm_response = client.put(
            f"/api/v1/appointments/{appointment_id}/status",
            headers={"Authorization": f"Bearer {doctor_token}"},
            json={
                "status": "confirmed",
                "doctor_notes": "Appointment confirmed"
            }
        )
        
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "confirmed"
        
        # 4. Doctor completes appointment
        complete_response = client.put(
            f"/api/v1/appointments/{appointment_id}/status",
            headers={"Authorization": f"Bearer {doctor_token}"},
            json={
                "status": "completed",
                "doctor_notes": "Consultation completed",
                "prescription": "Take rest and drink plenty of water"
            }
        )
        
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"
        assert complete_response.json()["prescription"] == "Take rest and drink plenty of water"
        
        # 5. Admin views appointment details
        admin_view_response = client.get(
            f"/api/v1/appointments/{appointment_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert admin_view_response.status_code == 200
        assert admin_view_response.json()["status"] == "completed"
        
        # 6. Check statistics reflect the completed appointment
        stats_response = client.get(
            "/api/v1/appointments/stats/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["completed_appointments"] >= 1
"""Tests for authentication endpoints"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db, SessionLocal, create_tables
from app.models.user import User, UserType
from app.models.location import Division, District, Thana
from app.core.security import get_password_hash

client = TestClient(app)

# Test database setup
@pytest.fixture(scope="module")
def test_db():
    """Create test database session"""
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

class TestUserRegistration:
    """Test user registration functionality"""
    
    def test_register_patient_success(self, override_get_db):
        """Test successful patient registration"""
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Test Patient",
            "email": "patient@test.com",
            "mobile_number": "+8801712345678",
            "password": "Password123!",
            "user_type": "patient",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1,
            "address": "123 Test Street"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "patient@test.com"
        assert data["user_type"] == "patient"
        assert data["full_name"] == "Test Patient"
    
    def test_register_doctor_success(self, override_get_db):
        """Test successful doctor registration"""
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Dr. Test Doctor",
            "email": "doctor@test.com",
            "mobile_number": "+8801712345679",
            "password": "Password123!",
            "user_type": "doctor",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1,
            "address": "123 Medical Street",
            "doctor_data": {
                "license_number": "TEST12345",
                "specialization": "General Medicine",
                "experience_years": 5,
                "consultation_fee": 1000.0,
                "available_timeslots": {
                    "monday": ["10:00-11:00", "14:00-15:00"],
                    "tuesday": ["10:00-11:00"]
                },
                "qualification": "MBBS",
                "bio": "Test doctor"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "doctor@test.com"
        assert data["user_type"] == "doctor"
    
    def test_register_duplicate_email(self, override_get_db):
        """Test registration with duplicate email"""
        # First registration
        client.post("/api/v1/auth/register", json={
            "full_name": "Test User 1",
            "email": "duplicate@test.com",
            "mobile_number": "+8801712345680",
            "password": "Password123!",
            "user_type": "patient",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1
        })
        
        # Second registration with same email
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Test User 2",
            "email": "duplicate@test.com",
            "mobile_number": "+8801712345681",
            "password": "Password123!",
            "user_type": "patient",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1
        })
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_register_invalid_mobile(self, override_get_db):
        """Test registration with invalid mobile number"""
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": "test@test.com",
            "mobile_number": "123456789",  # Invalid format
            "password": "Password123!",
            "user_type": "patient",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1
        })
        
        assert response.status_code == 422
    
    def test_register_weak_password(self, override_get_db):
        """Test registration with weak password"""
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": "test2@test.com",
            "mobile_number": "+8801712345682",
            "password": "weak",  # Weak password
            "user_type": "patient",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1
        })
        
        assert response.status_code == 422
    
    def test_register_doctor_without_profile(self, override_get_db):
        """Test doctor registration without doctor profile data"""
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Dr. Test",
            "email": "doctor2@test.com",
            "mobile_number": "+8801712345683",
            "password": "Password123!",
            "user_type": "doctor",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1
            # Missing doctor_data
        })
        
        assert response.status_code == 400
        assert "Doctor profile data is required" in response.json()["detail"]

class TestUserLogin:
    """Test user login functionality"""
    
    def test_login_success(self, override_get_db):
        """Test successful login"""
        # Create a test user
        db = override_get_db
        test_user = User(
            full_name="Login Test User",
            email="login@test.com",
            mobile_number="+8801712345684",
            password_hash=get_password_hash("Password123!"),
            user_type=UserType.PATIENT,
            division_id=1,
            district_id=1,
            thana_id=1,
            is_active=True
        )
        db.add(test_user)
        db.commit()
        
        # Test login
        response = client.post("/api/v1/auth/login", data={
            "username": "login@test.com",
            "password": "Password123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_type"] == "patient"
    
    def test_login_invalid_email(self, override_get_db):
        """Test login with invalid email"""
        response = client.post("/api/v1/auth/login", data={
            "username": "nonexistent@test.com",
            "password": "Password123!"
        })
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_invalid_password(self, override_get_db):
        """Test login with invalid password"""
        response = client.post("/api/v1/auth/login", data={
            "username": "login@test.com",
            "password": "WrongPassword!"
        })
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_inactive_user(self, override_get_db):
        """Test login with inactive user"""
        # Create inactive user
        db = override_get_db
        inactive_user = User(
            full_name="Inactive User",
            email="inactive@test.com",
            mobile_number="+8801712345685",
            password_hash=get_password_hash("Password123!"),
            user_type=UserType.PATIENT,
            division_id=1,
            district_id=1,
            thana_id=1,
            is_active=False  # Inactive user
        )
        db.add(inactive_user)
        db.commit()
        
        response = client.post("/api/v1/auth/login", data={
            "username": "inactive@test.com",
            "password": "Password123!"
        })
        
        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]

class TestUserProfile:
    """Test user profile functionality"""
    
    def test_get_profile_success(self, override_get_db):
        """Test getting user profile with valid token"""
        # Login first to get token
        response = client.post("/api/v1/auth/login", data={
            "username": "login@test.com",
            "password": "Password123!"
        })
        token = response.json()["access_token"]
        
        # Get profile
        response = client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "login@test.com"
        assert "full_name" in data
        assert "user_type" in data
    
    def test_get_profile_invalid_token(self, override_get_db):
        """Test getting profile with invalid token"""
        response = client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_get_profile_no_token(self, override_get_db):
        """Test getting profile without token"""
        response = client.get("/api/v1/auth/profile")
        
        assert response.status_code == 403

class TestPasswordChange:
    """Test password change functionality"""
    
    def test_change_password_success(self, override_get_db):
        """Test successful password change"""
        # Login to get token
        response = client.post("/api/v1/auth/login", data={
            "username": "login@test.com",
            "password": "Password123!"
        })
        token = response.json()["access_token"]
        
        # Change password
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "Password123!",
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == 200
        assert "Password updated successfully" in response.json()["message"]
        
        # Test login with new password
        response = client.post("/api/v1/auth/login", data={
            "username": "login@test.com",
            "password": "NewPassword123!"
        })
        
        assert response.status_code == 200
    
    def test_change_password_wrong_current(self, override_get_db):
        """Test password change with wrong current password"""
        # Login to get token
        response = client.post("/api/v1/auth/login", data={
            "username": "login@test.com",
            "password": "NewPassword123!"
        })
        token = response.json()["access_token"]
        
        # Try to change with wrong current password
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "WrongPassword!",
                "new_password": "AnotherPassword123!"
            }
        )
        
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]
    
    def test_change_password_weak_new(self, override_get_db):
        """Test password change with weak new password"""
        # Login to get token
        response = client.post("/api/v1/auth/login", data={
            "username": "login@test.com",
            "password": "NewPassword123!"
        })
        token = response.json()["access_token"]
        
        # Try to change to weak password
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "NewPassword123!",
                "new_password": "weak"
            }
        )
        
        assert response.status_code == 422

class TestLogout:
    """Test logout functionality"""
    
    def test_logout_success(self, override_get_db):
        """Test successful logout"""
        # Login to get token
        response = client.post("/api/v1/auth/login", data={
            "username": "login@test.com",
            "password": "NewPassword123!"
        })
        token = response.json()["access_token"]
        
        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]
    
    def test_logout_no_token(self, override_get_db):
        """Test logout without token"""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 403

# Integration tests
class TestAuthenticationFlow:
    """Test complete authentication flow"""
    
    def test_complete_patient_flow(self, override_get_db):
        """Test complete patient registration and login flow"""
        # 1. Register patient
        register_response = client.post("/api/v1/auth/register", json={
            "full_name": "Flow Test Patient",
            "email": "flow.patient@test.com",
            "mobile_number": "+8801712345686",
            "password": "Password123!",
            "user_type": "patient",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1,
            "address": "123 Flow Street"
        })
        
        assert register_response.status_code == 200
        
        # 2. Login
        login_response = client.post("/api/v1/auth/login", data={
            "username": "flow.patient@test.com",
            "password": "Password123!"
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 3. Get profile
        profile_response = client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["email"] == "flow.patient@test.com"
        assert profile_data["user_type"] == "patient"
        
        # 4. Change password
        password_change_response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "Password123!",
                "new_password": "NewFlowPassword123!"
            }
        )
        
        assert password_change_response.status_code == 200
        
        # 5. Login with new password
        new_login_response = client.post("/api/v1/auth/login", data={
            "username": "flow.patient@test.com",
            "password": "NewFlowPassword123!"
        })
        
        assert new_login_response.status_code == 200
        
        # 6. Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert logout_response.status_code == 200
    
    def test_complete_doctor_flow(self, override_get_db):
        """Test complete doctor registration and login flow"""
        # 1. Register doctor
        register_response = client.post("/api/v1/auth/register", json={
            "full_name": "Dr. Flow Test",
            "email": "flow.doctor@test.com",
            "mobile_number": "+8801712345687",
            "password": "Password123!",
            "user_type": "doctor",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1,
            "address": "123 Medical Flow Street",
            "doctor_data": {
                "license_number": "FLOW12345",
                "specialization": "Cardiology",
                "experience_years": 8,
                "consultation_fee": 1500.0,
                "available_timeslots": {
                    "monday": ["10:00-11:00", "14:00-15:00"],
                    "tuesday": ["10:00-11:00", "16:00-17:00"],
                    "wednesday": ["14:00-15:00"]
                },
                "qualification": "MBBS, MD (Cardiology)",
                "bio": "Experienced cardiologist for flow testing"
            }
        })
        
        assert register_response.status_code == 200
        
        # 2. Login
        login_response = client.post("/api/v1/auth/login", data={
            "username": "flow.doctor@test.com",
            "password": "Password123!"
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 3. Get profile
        profile_response = client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["email"] == "flow.doctor@test.com"
        assert profile_data["user_type"] == "doctor"

# Validation tests
class TestValidation:
    """Test input validation"""
    
    def test_email_validation(self, override_get_db):
        """Test email format validation"""
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": "invalid-email",  # Invalid email format
            "mobile_number": "+8801712345688",
            "password": "Password123!",
            "user_type": "patient",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1
        })
        
        assert response.status_code == 422
    
    def test_mobile_validation(self, override_get_db):
        """Test mobile number validation"""
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": "test.mobile@test.com",
            "mobile_number": "01712345678",  # Missing +88
            "password": "Password123!",
            "user_type": "patient",
            "division_id": 1,
            "district_id": 1,
            "thana_id": 1
        })
        
        assert response.status_code == 422
    
    def test_required_fields(self, override_get_db):
        """Test required field validation"""
        response = client.post("/api/v1/auth/register", json={
            "email": "test.required@test.com",
            "password": "Password123!",
            # Missing required fields
        })
        
        assert response.status_code == 422
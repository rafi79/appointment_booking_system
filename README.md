# Healthcare Appointment Booking System

A comprehensive appointment booking system built with FastAPI and PostgreSQL that allows patients to book appointments with doctors, manage profiles, and provides administrative tools for healthcare providers.

## 🏗️ Project Architecture

### Tech Stack
- **Backend**: FastAPI (Python 3.8+)
- **Database**: PostgreSQL 13+
- **Authentication**: JWT (JSON Web Tokens)
- **Frontend**: HTML/CSS/JavaScript with Bootstrap 5
- **Task Queue**: Celery with Redis
- **File Storage**: Local filesystem
- **Validation**: Pydantic models
- **ORM**: SQLAlchemy with Alembic migrations

### Architecture Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (HTML/JS)     │◄──►│   (FastAPI)     │◄──►│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Task Queue    │
                       │   (Celery)      │
                       └─────────────────┘
```

## 🚀 Features

### User Management
- **Three User Types**: Admin, Doctor, Patient
- **JWT Authentication**: Secure login/logout system
- **Profile Management**: Complete user profile with image upload
- **Role-based Access Control**: Different permissions for each user type

### Appointment System
- **Real-time Booking**: Check doctor availability
- **Status Management**: Pending → Confirmed → Completed workflow
- **Conflict Prevention**: No double-booking validation
- **Time Slot Management**: Doctor-specific available hours

### Administrative Tools
- **User Management**: View, activate/deactivate users
- **Doctor Management**: Approve doctors, manage specializations
- **Appointment Oversight**: Monitor all appointments across the system
- **Reports & Analytics**: Monthly reports, revenue tracking

### Background Tasks
- **Appointment Reminders**: 24-hour advance notifications
- **Monthly Reports**: Automated doctor performance reports
- **Data Cleanup**: Automated maintenance tasks

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 13 or higher
- Redis (for Celery tasks)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/healthcare-appointment-system.git
cd healthcare-appointment-system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
```bash
cp .env.example .env
# Edit .env with your database credentials and settings
```

### 5. Database Setup
```bash
# Create PostgreSQL database
createdb healthcare_appointments

# Run migrations
alembic upgrade head

# Seed initial data
python scripts/seed_data.py
```

### 6. Create Admin User
```bash
python scripts/create_admin.py
```

### 7. Start the Application
```bash
# Start the main application
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# In a separate terminal, start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# In another terminal, start Celery scheduler
celery -A app.tasks.celery_app beat --loglevel=info
```

### 8. Access the Application
- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:8000/admin
- **Default Admin**: admin@hospital.com / Admin123!

## 🐳 Docker Setup (Alternative)

```bash
# Build and start all services
docker-compose up --build

# Run migrations
docker-compose exec web alembic upgrade head

# Seed data
docker-compose exec web python scripts/seed_data.py
```

## 📖 API Documentation

### Authentication Endpoints

#### POST /api/v1/auth/register
Register a new user
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "mobile_number": "+8801712345678",
  "password": "SecurePass123!",
  "user_type": "patient",
  "division_id": 1,
  "district_id": 1,
  "thana_id": 1,
  "address": "123 Main St"
}
```

#### POST /api/v1/auth/login
User login
```json
{
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

### User Management Endpoints

#### GET /api/v1/users/profile
Get current user profile (requires authentication)

#### PUT /api/v1/users/profile
Update user profile
```json
{
  "full_name": "John Smith",
  "mobile_number": "+8801712345679",
  "address": "456 New Street"
}
```

### Doctor Endpoints

#### GET /api/v1/doctors/
List all doctors with pagination and filters
Query parameters: `specialization`, `skip`, `limit`

#### GET /api/v1/doctors/me/profile
Get current doctor's profile (doctors only)

#### PUT /api/v1/doctors/me/profile
Update doctor profile
```json
{
  "specialization": "Cardiology",
  "experience_years": 10,
  "consultation_fee": 1500.00,
  "qualification": "MBBS, MD"
}
```

### Appointment Endpoints

#### POST /api/v1/appointments/
Book a new appointment
```json
{
  "doctor_id": 1,
  "appointment_date": "2025-01-25",
  "appointment_time": "10:00-11:00",
  "symptoms": "Chest pain",
  "notes": "Urgent consultation needed"
}
```

#### GET /api/v1/appointments/
List user's appointments with filters
Query parameters: `status`, `date_from`, `date_to`, `skip`, `limit`

#### PUT /api/v1/appointments/{id}/status
Update appointment status (doctors/admins only)
```json
{
  "status": "confirmed",
  "doctor_notes": "Patient consultation confirmed"
}
```

### Admin Endpoints

#### GET /api/v1/admin/dashboard
Get admin dashboard statistics

#### GET /api/v1/admin/users
List all users with filters and pagination

#### PUT /api/v1/admin/users/{id}/toggle-status
Activate/deactivate user account

#### GET /api/v1/admin/reports/monthly
Generate monthly performance reports

## 🗄️ Database Schema

### Core Tables

#### users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    mobile_number VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    user_type user_type_enum NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    profile_image VARCHAR(255),
    division_id INTEGER REFERENCES divisions(id),
    district_id INTEGER REFERENCES districts(id),
    thana_id INTEGER REFERENCES thanas(id),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### doctors
```sql
CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    license_number VARCHAR(50) UNIQUE NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    experience_years INTEGER NOT NULL,
    consultation_fee DECIMAL(10,2) NOT NULL,
    qualification TEXT,
    bio TEXT,
    available_timeslots JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### appointments
```sql
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    doctor_id INTEGER REFERENCES doctors(id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR(20) NOT NULL,
    status appointment_status_enum DEFAULT 'pending',
    symptoms TEXT,
    notes TEXT,
    doctor_notes TEXT,
    prescription TEXT,
    diagnosis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, appointment_date, appointment_time, status) 
    WHERE status IN ('pending', 'confirmed')
);
```

### Enums
```sql
CREATE TYPE user_type_enum AS ENUM ('patient', 'doctor', 'admin');
CREATE TYPE appointment_status_enum AS ENUM ('pending', 'confirmed', 'completed', 'cancelled');
```

### Relationships
- **One-to-One**: User ↔ Doctor
- **One-to-Many**: User → Appointments (as patient)
- **One-to-Many**: Doctor → Appointments
- **Many-to-One**: Users → Locations (Division/District/Thana)

### Indexes
```sql
CREATE INDEX idx_appointments_doctor_date ON appointments(doctor_id, appointment_date);
CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_mobile ON users(mobile_number);
CREATE INDEX idx_doctors_specialization ON doctors(specialization);
```

## 🔧 Configuration

### Environment Variables (.env)
```env
# Database
DATABASE_URL=postgresql://username:password@localhost/healthcare_appointments
TEST_DATABASE_URL=postgresql://username:password@localhost/healthcare_appointments_test

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# File Upload
MAX_FILE_SIZE=5242880  # 5MB
UPLOAD_DIR=uploads/
ALLOWED_IMAGE_TYPES=image/jpeg,image/png

# Application
DEBUG=True
ENVIRONMENT=development
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_appointments.py -v
```

### Test Coverage
The project includes comprehensive tests for:
- Authentication flows
- User registration and validation
- Appointment booking logic
- Admin functionalities
- API endpoints
- Database operations

## 📊 Validation Rules

### User Registration
- **Email**: Must be unique and valid format
- **Mobile**: Must start with +88 and be exactly 14 digits
- **Password**: Minimum 8 characters, 1 uppercase, 1 digit, 1 special character
- **Profile Image**: Max 5MB, JPEG/PNG only

### Appointment Booking
- **Date**: Cannot be in the past
- **Time**: Must match doctor's available slots
- **Conflict Check**: No double booking for same doctor/time
- **Business Hours**: Appointments only during working hours

### Doctor Registration
- **License Number**: Must be unique
- **Experience**: Minimum 0, maximum 60 years
- **Consultation Fee**: Must be positive number
- **Available Timeslots**: Valid time format (HH:MM-HH:MM)

## 🔄 Background Tasks

### Scheduled Tasks
- **Daily 09:00**: Send appointment reminders for next day
- **Monthly 1st**: Generate monthly reports for all doctors
- **Weekly**: Clean up expired sessions and temporary files

### Task Examples
```python
# Send reminder
@celery.task
def send_appointment_reminder(appointment_id):
    # Implementation for sending SMS/Email reminders
    pass

# Generate monthly report
@celery.task
def generate_monthly_report(year, month):
    # Implementation for PDF report generation
    pass
```

## 🚨 Challenges Faced & Solutions

### 1. **Appointment Conflict Prevention**
**Challenge**: Preventing double-booking of appointments
**Solution**: Database unique constraint + application-level validation
```sql
UNIQUE(doctor_id, appointment_date, appointment_time, status) 
WHERE status IN ('pending', 'confirmed')
```

### 2. **Complex User Role Management**
**Challenge**: Three different user types with different permissions
**Solution**: Role-based access control with dependency injection
```python
async def get_current_doctor(current_user: User = Depends(get_current_user)):
    if current_user.user_type != UserType.DOCTOR:
        raise HTTPException(status_code=403, detail="Access denied")
    return current_user
```

### 3. **File Upload Validation**
**Challenge**: Secure file upload with size and type validation
**Solution**: Multi-layer validation (file size, MIME type, content validation)

### 4. **Bangladesh Location Hierarchy**
**Challenge**: Complex Division → District → Thana relationship
**Solution**: Normalized database design with foreign key constraints

### 5. **Time Zone Management**
**Challenge**: Consistent time handling across the application
**Solution**: Store all times in UTC, convert to local time in frontend

## 🔐 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt for secure password storage
- **Input Validation**: Comprehensive validation for all inputs
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **File Upload Security**: Strict file type and size validation
- **Rate Limiting**: API rate limiting to prevent abuse
- **CORS Configuration**: Proper cross-origin resource sharing setup

## 📈 Performance Optimizations

- **Database Indexing**: Strategic indexes for common queries
- **Connection Pooling**: PostgreSQL connection pooling
- **Async Operations**: FastAPI async/await for better concurrency
- **Pagination**: Efficient pagination for large datasets
- **Caching**: Redis caching for frequently accessed data
- **File Compression**: Image compression for profile pictures

## 🚀 Deployment

### Production Considerations
- Use environment-specific configuration
- Set up proper logging with log rotation
- Configure backup strategies for database
- Set up monitoring and alerting
- Use reverse proxy (nginx) for static files
- Configure SSL certificates
- Set up CI/CD pipeline

### Scaling Options
- **Horizontal Scaling**: Multiple FastAPI instances behind load balancer
- **Database Scaling**: Read replicas for query optimization
- **Caching Layer**: Redis cluster for distributed caching
- **CDN**: Content delivery network for static assets

## 📞 Support & Contributing

### Getting Help
- Check the [API Documentation](http://localhost:8000/docs)
- Review the [Database Schema](docs/database_schema.md)
- See [Setup Guide](docs/setup_guide.md) for detailed instructions

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🏥 About

This Healthcare Appointment Booking System was developed to demonstrate:
- Clean architecture principles
- Comprehensive API design
- Database design best practices
- Security implementation
- Background task processing
- Complete user management system

For questions or support, please contact [your-email@example.com](mailto:your-email@example.com).

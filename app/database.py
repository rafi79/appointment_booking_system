from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False
    } if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


# Database dependency
def get_db():
    """
    Database dependency for FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to create tables
def create_tables():
    """
    Create all database tables
    """
    Base.metadata.create_all(bind=engine)
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# Get DATABASE_URL from environment
# Default to SQLite for PythonAnywhere compatibility
DATABASE_URL = os.environ.get("DATABASE_URL") or os.getenv("DATABASE_URL", "sqlite:///./okuma.db")

# Debug: Print the database URL (will show in logs)
print(f"DATABASE_URL configured: {DATABASE_URL[:50]}..." if DATABASE_URL else "DATABASE_URL not set!")

# SQLite requires special connect_args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator:
    """
    Database session dependency for FastAPI routes
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database tables
    """
    # Import all models to ensure they are registered with Base
    from models.user import User
    from models.story import Story
    from models.reading_activity import PreReading, Answer
    from models.evaluation import TeacherEvaluation
    from models.quiz import QuizQuestion
    
    Base.metadata.create_all(bind=engine)

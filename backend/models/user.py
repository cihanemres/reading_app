from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from database import Base

class UserRole(str, enum.Enum):
    STUDENT = "ogrenci"
    TEACHER = "ogretmen"
    PARENT = "veli"
    ADMIN = "yonetici"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    ad_soyad = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(SQLEnum(UserRole), nullable=False)
    sinif_duzeyi = Column(Integer, nullable=True)  # Only for students (1-12)
    parent_id = Column(Integer, nullable=True)  # For linking student to parent (Legacy, no FK)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Linked teacher
    is_approved = Column(Boolean, default=False)
    
    # Teacher profile fields
    brans = Column(String(100), nullable=True)  # Specialization/Subject
    mezuniyet = Column(String(255), nullable=True)  # Degree/University
    biyografi = Column(String(500), nullable=True)  # Short bio
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Gamification relationships
    achievements = relationship("Achievement", back_populates="user")
    streak = relationship("UserStreak", back_populates="user", uselist=False)
    
    # Assignment relationships (as student)
    assignments = relationship("Assignment", foreign_keys="Assignment.student_id", back_populates="student")

    def __repr__(self):
        return f"<User {self.email} ({self.rol})>"


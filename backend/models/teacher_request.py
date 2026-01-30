"""
Teacher Request Model
For students requesting to join a teacher
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class RequestStatus(str, enum.Enum):
    PENDING = "bekliyor"
    ACCEPTED = "kabul"
    REJECTED = "red"


class TeacherRequest(Base):
    __tablename__ = "teacher_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String(500), nullable=True)  # Optional message from student
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    response_message = Column(String(500), nullable=True)  # Teacher's response
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])
    
    def __repr__(self):
        return f"<TeacherRequest(student={self.student_id}, teacher={self.teacher_id}, status={self.status})>"

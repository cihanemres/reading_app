"""
Commendation Model
For teacher commendations to students
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Commendation(Base):
    __tablename__ = "commendations"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Type: takdir, tesekkur, birincilik, ozel_basari
    commendation_type = Column(String(50), nullable=False, default="takdir")
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # For achievements/rankings
    category = Column(String(100), nullable=True)  # e.g., "okuma_hizi", "quiz_basarisi"
    rank = Column(Integer, nullable=True)  # 1st, 2nd, 3rd
    period = Column(String(50), nullable=True)  # e.g., "2024-12", "2024-W50"
    
    # XP bonus
    xp_reward = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])
    
    def __repr__(self):
        return f"<Commendation(student={self.student_id}, type={self.commendation_type})>"

"""
Achievement Model
Tracks badges and achievements earned by students
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_type = Column(String(50), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="achievements")
    
    # Ensure user can only earn each badge once
    __table_args__ = (
        UniqueConstraint('user_id', 'badge_type', name='unique_user_badge'),
    )
    
    def __repr__(self):
        return f"<Achievement(user_id={self.user_id}, badge={self.badge_type})>"

"""
Agenda Model
For student tasks, reminders, and special days
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class AgendaItem(Base):
    __tablename__ = "agenda_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Item type: task, reminder, birthday, special_day, reading_goal
    item_type = Column(String(50), nullable=False, default="task")
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Date fields
    date = Column(Date, nullable=False)
    time = Column(String(10), nullable=True)  # HH:MM format
    
    # For recurring events
    is_recurring = Column(Boolean, default=False)
    recurrence_type = Column(String(20), nullable=True)  # daily, weekly, monthly, yearly
    
    # Status
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Related entities
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Notification settings
    notify_before = Column(Integer, nullable=True)  # Minutes before
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    story = relationship("Story", foreign_keys=[story_id])
    
    def __repr__(self):
        return f"<AgendaItem(id={self.id}, title={self.title}, date={self.date})>"

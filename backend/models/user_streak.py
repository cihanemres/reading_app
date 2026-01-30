"""
User Streak Model
Tracks daily login streaks and XP for gamification
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime, date
from database import Base

class UserStreak(Base):
    __tablename__ = "user_streaks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date, nullable=True)
    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="streak")
    
    def __repr__(self):
        return f"<UserStreak(user_id={self.user_id}, streak={self.current_streak}, xp={self.total_xp})>"

# XP values for different actions
XP_VALUES = {
    "story_read": 10,           # Reading a story
    "practice_complete": 5,      # Completing a practice
    "quiz_passed": 15,           # Passing a quiz
    "perfect_score": 25,         # Perfect quiz score
    "daily_login": 5,            # Daily login bonus
    "streak_bonus_3": 10,        # 3-day streak bonus
    "streak_bonus_7": 25,        # 7-day streak bonus
    "streak_bonus_30": 100,      # 30-day streak bonus
    "badge_earned": 20,          # Earning a badge
    "speed_improvement": 15,     # Speed improvement over 10%
}

# Level thresholds
LEVEL_THRESHOLDS = [
    0,      # Level 1
    100,    # Level 2
    250,    # Level 3
    500,    # Level 4
    1000,   # Level 5
    2000,   # Level 6
    3500,   # Level 7
    5000,   # Level 8
    7500,   # Level 9
    10000,  # Level 10
]

def get_level_for_xp(xp: int) -> int:
    """Calculate level based on XP"""
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp < threshold:
            return i
    return len(LEVEL_THRESHOLDS)

def get_xp_for_next_level(current_xp: int, current_level: int) -> dict:
    """Get XP needed for next level"""
    if current_level >= len(LEVEL_THRESHOLDS):
        return {"current": current_xp, "needed": 0, "progress": 100}
    
    current_threshold = LEVEL_THRESHOLDS[current_level - 1] if current_level > 1 else 0
    next_threshold = LEVEL_THRESHOLDS[current_level] if current_level < len(LEVEL_THRESHOLDS) else current_xp
    
    xp_in_level = current_xp - current_threshold
    xp_needed = next_threshold - current_threshold
    progress = (xp_in_level / xp_needed * 100) if xp_needed > 0 else 100
    
    return {
        "current": xp_in_level,
        "needed": xp_needed,
        "progress": min(100, progress)
    }

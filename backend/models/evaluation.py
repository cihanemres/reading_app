from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class TeacherEvaluation(Base):
    """Teacher assessment of student reading performance"""
    __tablename__ = "teacher_evaluation"

    id = Column(Integer, primary_key=True, index=True)
    ogrenci_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False, index=True)
    ogretmen_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Assessment fields
    hatali_kelime = Column(Text, nullable=True)  # Comma-separated list of incorrect words
    akicilik_puan = Column(Integer, nullable=True)  # Fluency score (1-10)
    acik_soru_puani = Column(Integer, nullable=True)  # Open-ended question score (1-10)
    ogretmen_yorumu = Column(Text, nullable=True)  # Teacher's comments
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<TeacherEvaluation student={self.ogrenci_id} story={self.story_id}>"

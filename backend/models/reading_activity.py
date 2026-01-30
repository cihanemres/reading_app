from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class PreReading(Base):
    """Initial reading session before practice"""
    __tablename__ = "pre_reading"

    id = Column(Integer, primary_key=True, index=True)
    ogrenci_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False, index=True)
    okuma_suresi = Column(Float, nullable=False)  # Reading time in seconds
    kelime_sayisi = Column(Integer, nullable=False)
    okuma_hizi = Column(Float, nullable=True)  # Words per minute (calculated)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PreReading student={self.ogrenci_id} story={self.story_id}>"


class Practice(Base):
    """Practice/repeat reading sessions"""
    __tablename__ = "practice"

    id = Column(Integer, primary_key=True, index=True)
    ogrenci_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False, index=True)
    tekrar_no = Column(Integer, nullable=False)  # Practice attempt number
    okuma_suresi = Column(Float, nullable=False)  # Reading time in seconds
    kelime_sayisi = Column(Integer, nullable=False)
    okuma_hizi = Column(Float, nullable=True)  # Words per minute (calculated)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Practice student={self.ogrenci_id} story={self.story_id} attempt={self.tekrar_no}>"


class Answer(Base):
    """Student quiz answers"""
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    ogrenci_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False, index=True)
    q1 = Column(String(10), nullable=True)  # Multiple choice answer (A, B, C, D)
    q2 = Column(String(10), nullable=True)
    q3 = Column(String(10), nullable=True)
    q4 = Column(String(10), nullable=True)
    dogru_sayisi = Column(Integer, nullable=True)  # Number of correct answers
    acik_uclu = Column(Text, nullable=True)  # Open-ended answer
    answers_json = Column(Text, nullable=True)  # JSON string for flexible answers
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Answer student={self.ogrenci_id} story={self.story_id}>"

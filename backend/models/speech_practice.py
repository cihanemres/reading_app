from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class SpeechPracticeRecord(Base):
    """Sesli okuma pratik kayıtları"""
    __tablename__ = "sesli_okuma_kayitlari"

    id = Column(Integer, primary_key=True, index=True)
    ogrenci_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hikaye_id = Column(Integer, ForeignKey("stories.id"), nullable=False, index=True)
    deneme_no = Column(Integer, nullable=False, default=1)
    
    # Okuma sonuçları
    dogru_kelime = Column(Integer, nullable=False, default=0)
    hatali_kelime = Column(Integer, nullable=False, default=0)
    atlanan_kelime = Column(Integer, nullable=False, default=0)
    toplam_kelime = Column(Integer, nullable=False, default=0)
    dogruluk_orani = Column(Float, nullable=False, default=0.0)
    
    # Hatalı kelimeler listesi (JSON string)
    hatali_kelimeler = Column(Text, nullable=True)
    
    # Algılanan metin
    algilanan_metin = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<SpeechPractice Student:{self.ogrenci_id} Story:{self.hikaye_id} Attempt:{self.deneme_no} Accuracy:{self.dogruluk_orani}%>"

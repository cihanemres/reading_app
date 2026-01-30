from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
from models.user import User, UserRole
from models.reading_activity import PreReading, Practice, Answer
from models.story import Story
from models.speech_practice import SpeechPracticeRecord
import json
from auth.dependencies import get_current_user
from utils.word_counter import calculate_reading_speed
from utils.progress_calculator import calculate_improvement

router = APIRouter(prefix="/api/reading", tags=["Reading Activities"])

# Pydantic schemas
class PreReadingCreate(BaseModel):
    story_id: int
    okuma_suresi: float  # in seconds
    kelime_sayisi: int

class PracticeCreate(BaseModel):
    story_id: int
    okuma_suresi: float
    kelime_sayisi: int

class AnswerCreate(BaseModel):
    story_id: int
    q1: Optional[str] = None
    q2: Optional[str] = None
    q3: Optional[str] = None
    q4: Optional[str] = None
    acik_uclu: Optional[str] = None
    answers_json: Optional[List[dict]] = None

class ReadingResponse(BaseModel):
    id: int
    ogrenci_id: int
    story_id: int
    okuma_suresi: float
    kelime_sayisi: int
    okuma_hizi: Optional[float]
    
    class Config:
        from_attributes = True

class PracticeResponse(ReadingResponse):
    tekrar_no: int

class AnswerResponse(BaseModel):
    id: int
    ogrenci_id: int
    story_id: int
    q1: Optional[str]
    q2: Optional[str]
    q3: Optional[str]
    q4: Optional[str]
    acik_uclu: Optional[str]
    answers_json: Optional[str]
    
    class Config:
        from_attributes = True

# Speech practice schemas
class SpeechPracticeCreate(BaseModel):
    story_id: int
    dogru_kelime: int
    hatali_kelime: int
    atlanan_kelime: int
    toplam_kelime: int
    dogruluk_orani: float
    hatali_kelimeler: Optional[List[str]] = None
    algilanan_metin: Optional[str] = None

class SpeechPracticeResponse(BaseModel):
    id: int
    ogrenci_id: int
    hikaye_id: int
    deneme_no: int
    dogru_kelime: int
    hatali_kelime: int
    atlanan_kelime: int
    toplam_kelime: int
    dogruluk_orani: float
    hatali_kelimeler: Optional[List[str]] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

@router.post("/pre-reading", response_model=ReadingResponse, status_code=status.HTTP_201_CREATED)
async def save_pre_reading(
    data: PreReadingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save pre-reading (initial reading) data
    """
    # Verify story exists
    story = db.query(Story).filter(Story.id == data.story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Check if student already has pre-reading for this story
    existing = db.query(PreReading).filter(
        PreReading.ogrenci_id == current_user.id,
        PreReading.story_id == data.story_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pre-reading already exists for this story. Use practice endpoint instead."
        )
    
    # Calculate reading speed
    reading_speed = calculate_reading_speed(data.kelime_sayisi, data.okuma_suresi)
    
    # Create pre-reading record
    pre_reading = PreReading(
        ogrenci_id=current_user.id,
        story_id=data.story_id,
        okuma_suresi=data.okuma_suresi,
        kelime_sayisi=data.kelime_sayisi,
        okuma_hizi=reading_speed
    )
    
    db.add(pre_reading)
    db.commit()
    db.refresh(pre_reading)
    
    # Check milestone
    try:
        from utils.notification_helper import notify_progress_milestone
        total = db.query(PreReading).filter(PreReading.ogrenci_id == current_user.id).count()
        if total in [5, 10, 20, 50, 100]:
            notify_progress_milestone(db, current_user.id, 'stories', total)
    except Exception as e:
        print(f'Milestone notification error: {e}')
    
    return pre_reading

@router.post("/practice", response_model=PracticeResponse, status_code=status.HTTP_201_CREATED)
async def save_practice(
    data: PracticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save practice reading data
    """
    # Verify story exists
    story = db.query(Story).filter(Story.id == data.story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Get the next practice number
    last_practice = db.query(Practice).filter(
        Practice.ogrenci_id == current_user.id,
        Practice.story_id == data.story_id
    ).order_by(Practice.tekrar_no.desc()).first()
    
    next_number = 1 if not last_practice else last_practice.tekrar_no + 1
    
    # Calculate reading speed
    reading_speed = calculate_reading_speed(data.kelime_sayisi, data.okuma_suresi)
    
    # Create practice record
    practice = Practice(
        ogrenci_id=current_user.id,
        story_id=data.story_id,
        tekrar_no=next_number,
        okuma_suresi=data.okuma_suresi,
        kelime_sayisi=data.kelime_sayisi,
        okuma_hizi=reading_speed
    )
    
    db.add(practice)
    db.commit()
    db.refresh(practice)
    
    return practice

@router.post("/answers", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
async def save_answers(
    data: AnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save quiz answers
    """
    # Verify story exists
    story = db.query(Story).filter(Story.id == data.story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    correct_count = 0
    
    # Logic for NEW system (JSON based)
    if story.sorular:
        try:
            story_questions = json.loads(story.sorular)
            # data.answers_json expects a list of dicts: [{"index": 0, "answer": "A"}, ...] or similar
            # Ideally frontend sends direct simple structure. 
            # Let's assume data.answers_json is a list of answer objects matching question order or containing index.
            
            if data.answers_json:
                for ans in data.answers_json:
                    idx = ans.get('question_index')
                    val = ans.get('answer')
                    
                    if idx is not None and 0 <= idx < len(story_questions):
                        q = story_questions[idx]
                        if q.get('cevap_tipi') == 'test' and q.get('dogru_cevap') == val:
                             correct_count += 1
        except Exception as e:
            print(f"Error calculating score: {e}")
            
    # Logic for OLD system (QuizQuestion table)
    else:
        from models.quiz import QuizQuestion
        questions = db.query(QuizQuestion).filter(QuizQuestion.story_id == data.story_id).order_by(QuizQuestion.id).all()
        
        # Map answers to indices
        student_answers = [data.q1, data.q2, data.q3, data.q4]
        
        for i, q in enumerate(questions):
            if i < 4:  # Only check first 4 questions
                student_ans = student_answers[i]
                if student_ans and student_ans == q.correct_answer:
                    correct_count += 1

    # Check if answers already exist
    existing = db.query(Answer).filter(
        Answer.ogrenci_id == current_user.id,
        Answer.story_id == data.story_id
    ).first()
    
    if existing:
        # Update existing answers
        existing.q1 = data.q1
        existing.q2 = data.q2
        existing.q3 = data.q3
        existing.q4 = data.q4
        existing.acik_uclu = data.acik_uclu
        existing.answers_json = json.dumps(data.answers_json) if data.answers_json else None
        existing.dogru_sayisi = correct_count
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new answer record
    answer = Answer(
        ogrenci_id=current_user.id,
        story_id=data.story_id,
        q1=data.q1,
        q2=data.q2,
        q3=data.q3,
        q4=data.q4,
        acik_uclu=data.acik_uclu,
        answers_json=json.dumps(data.answers_json) if data.answers_json else None,
        dogru_sayisi=correct_count
    )
    
    db.add(answer)
    db.commit()
    db.refresh(answer)
    
    return answer

@router.get("/progress/{story_id}")
async def get_reading_progress(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get reading progress for a specific story
    """
    improvement = calculate_improvement(current_user.id, story_id, db)
    
    # Get all practice attempts
    practices = db.query(Practice).filter(
        Practice.ogrenci_id == current_user.id,
        Practice.story_id == story_id
    ).order_by(Practice.tekrar_no).all()
    
    practice_data = [
        {
            "attempt": p.tekrar_no,
            "speed_wpm": p.okuma_hizi,
            "time_seconds": p.okuma_suresi
        }
        for p in practices
    ]
    
    return {
        "story_id": story_id,
        "improvement": improvement,
        "practice_history": practice_data
    }

@router.get("/my-progress")
async def get_overall_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall reading progress for the current student
    """
    from utils.progress_calculator import get_student_progress_summary
    
    summary = get_student_progress_summary(current_user.id, db)
    
    # Get all stories the student has read
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == current_user.id
    ).all()
    
    stories_read = []
    for pr in pre_readings:
        story = db.query(Story).filter(Story.id == pr.story_id).first()
        if story:
            improvement = calculate_improvement(current_user.id, story.id, db)
            stories_read.append({
                "story_id": story.id,
                "story_title": story.baslik,
                "improvement": improvement
            })
    
    return {
        "summary": summary,
        "stories": stories_read
    }

# Speech Practice Endpoints
@router.post("/speech-practice", response_model=SpeechPracticeResponse, status_code=status.HTTP_201_CREATED)
async def save_speech_practice(
    data: SpeechPracticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save speech practice results
    """
    if current_user.rol != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can save speech practice"
        )
    
    # Verify story exists
    story = db.query(Story).filter(Story.id == data.story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Get next attempt number
    last_attempt = db.query(SpeechPracticeRecord).filter(
        SpeechPracticeRecord.ogrenci_id == current_user.id,
        SpeechPracticeRecord.hikaye_id == data.story_id
    ).order_by(SpeechPracticeRecord.deneme_no.desc()).first()
    
    next_attempt = (last_attempt.deneme_no + 1) if last_attempt else 1
    
    # Create record
    record = SpeechPracticeRecord(
        ogrenci_id=current_user.id,
        hikaye_id=data.story_id,
        deneme_no=next_attempt,
        dogru_kelime=data.dogru_kelime,
        hatali_kelime=data.hatali_kelime,
        atlanan_kelime=data.atlanan_kelime,
        toplam_kelime=data.toplam_kelime,
        dogruluk_orani=data.dogruluk_orani,
        hatali_kelimeler=json.dumps(data.hatali_kelimeler) if data.hatali_kelimeler else None,
        algilanan_metin=data.algilanan_metin
    )
    
    db.add(record)
    db.commit()
    db.refresh(record)
    
    return SpeechPracticeResponse(
        id=record.id,
        ogrenci_id=record.ogrenci_id,
        hikaye_id=record.hikaye_id,
        deneme_no=record.deneme_no,
        dogru_kelime=record.dogru_kelime,
        hatali_kelime=record.hatali_kelime,
        atlanan_kelime=record.atlanan_kelime,
        toplam_kelime=record.toplam_kelime,
        dogruluk_orani=record.dogruluk_orani,
        hatali_kelimeler=json.loads(record.hatali_kelimeler) if record.hatali_kelimeler else None,
        created_at=str(record.created_at) if record.created_at else None
    )

@router.get("/speech-history/{story_id}", response_model=List[SpeechPracticeResponse])
async def get_speech_history(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get speech practice history for a story
    """
    records = db.query(SpeechPracticeRecord).filter(
        SpeechPracticeRecord.ogrenci_id == current_user.id,
        SpeechPracticeRecord.hikaye_id == story_id
    ).order_by(SpeechPracticeRecord.deneme_no.desc()).all()
    
    return [
        SpeechPracticeResponse(
            id=r.id,
            ogrenci_id=r.ogrenci_id,
            hikaye_id=r.hikaye_id,
            deneme_no=r.deneme_no,
            dogru_kelime=r.dogru_kelime,
            hatali_kelime=r.hatali_kelime,
            atlanan_kelime=r.atlanan_kelime,
            toplam_kelime=r.toplam_kelime,
            dogruluk_orani=r.dogruluk_orani,
            hatali_kelimeler=json.loads(r.hatali_kelimeler) if r.hatali_kelimeler else None,
            created_at=str(r.created_at) if r.created_at else None
        )
        for r in records
    ]


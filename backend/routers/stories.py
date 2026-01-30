from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
from models.user import User, UserRole
from models.story import Story
from auth.dependencies import get_current_user, require_role, require_any_role
from utils.file_handler import save_upload_file, delete_file
from utils.word_counter import count_words
import json

router = APIRouter(prefix="/api/stories", tags=["Stories"])

# Pydantic schemas
# Pydantic schemas
class StoryCreate(BaseModel):
    sinif_duzeyi: int
    ders: Optional[str] = None
    baslik: str
    konu_ozeti: Optional[str] = None
    metin: str
    sorular: Optional[List[dict]] = None

class StoryUpdate(BaseModel):
    baslik: Optional[str] = None
    metin: Optional[str] = None
    sinif_duzeyi: Optional[int] = None
    ders: Optional[str] = None
    konu_ozeti: Optional[str] = None
    sorular: Optional[List[dict]] = None

class StoryResponse(BaseModel):
    id: int
    sinif_duzeyi: int
    ders: Optional[str]
    baslik: str
    konu_ozeti: Optional[str]
    metin: str
    kapak_gorseli: Optional[str]
    ses_dosyasi: Optional[str]
    kelime_sayisi: Optional[int]
    sorular: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[StoryResponse])
async def list_stories(
    sinif_duzeyi: Optional[int] = None,
    ders: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all stories, optionally filtered by grade level, subject and search term
    """
    query = db.query(Story)
    
    # If student, filter by their grade level (allow +-1 level flexibility if needed later)
    if current_user.rol == UserRole.STUDENT and current_user.sinif_duzeyi:
        query = query.filter(Story.sinif_duzeyi == current_user.sinif_duzeyi)
    elif sinif_duzeyi:
        query = query.filter(Story.sinif_duzeyi == sinif_duzeyi)
    
    if ders:
        query = query.filter(Story.ders == ders)
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(Story.baslik.ilike(search_term))
    
    stories = query.order_by(Story.sinif_duzeyi, Story.baslik).all()
    return stories

@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific story by ID
    """
    story = db.query(Story).filter(Story.id == story_id).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Check if student can access this story
    if current_user.rol == UserRole.STUDENT:
        # Allow accessing if assigned by teacher (future) or matching grade
        if story.sinif_duzeyi != current_user.sinif_duzeyi:
             # Basic check for now, can be relaxed later
             pass 
    
    return story

@router.post("/", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    story_data: StoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role([UserRole.ADMIN, UserRole.TEACHER]))
):
    """
    Create a new story (Admin or Teacher)
    """
    # Validate grade level 1-12
    if not (1 <= story_data.sinif_duzeyi <= 12):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grade level must be between 1 and 12"
        )
    
    # Count words
    word_count = count_words(story_data.metin)
    
    # Create story
    new_story = Story(
        sinif_duzeyi=story_data.sinif_duzeyi,
        ders=story_data.ders,
        baslik=story_data.baslik,
        konu_ozeti=story_data.konu_ozeti,
        metin=story_data.metin,
        kelime_sayisi=word_count,
        sorular=json.dumps(story_data.sorular) if story_data.sorular else None
    )
    
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    
    return new_story

@router.put("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: int,
    story_data: StoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role([UserRole.ADMIN, UserRole.TEACHER]))
):
    """
    Update a story (Admin or Teacher)
    """
    story = db.query(Story).filter(Story.id == story_id).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Update fields
    if story_data.baslik is not None:
        story.baslik = story_data.baslik

    if story_data.ders is not None:
        story.ders = story_data.ders
        
    if story_data.konu_ozeti is not None:
        story.konu_ozeti = story_data.konu_ozeti
    
    if story_data.metin is not None:
        story.metin = story_data.metin
        story.kelime_sayisi = count_words(story_data.metin)
    
    if story_data.sinif_duzeyi is not None:
        if not (1 <= story_data.sinif_duzeyi <= 12):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Grade level must be between 1 and 12"
            )
        story.sinif_duzeyi = story_data.sinif_duzeyi

    if story_data.sorular is not None:
        story.sorular = json.dumps(story_data.sorular)
    
    db.commit()
    db.refresh(story)
    
    return story

@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role([UserRole.ADMIN, UserRole.TEACHER]))
):
    """
    Delete a story (Admin or Teacher)
    """
    story = db.query(Story).filter(Story.id == story_id).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Delete associated files
    if story.kapak_gorseli:
        delete_file(story.kapak_gorseli)
    if story.ses_dosyasi:
        delete_file(story.ses_dosyasi)
    
    db.delete(story)
    db.commit()
    
    return None

@router.post("/{story_id}/upload-cover", response_model=StoryResponse)
async def upload_cover_image(
    story_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role([UserRole.ADMIN, UserRole.TEACHER]))
):
    """
    Upload cover image for a story (Admin or Teacher)
    """
    story = db.query(Story).filter(Story.id == story_id).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Delete old cover if exists
    if story.kapak_gorseli:
        delete_file(story.kapak_gorseli)
    
    # Save new cover
    file_path = await save_upload_file(file, file_type="image")
    story.kapak_gorseli = file_path
    
    db.commit()
    db.refresh(story)
    
    return story

@router.post("/{story_id}/upload-audio", response_model=StoryResponse)
async def upload_audio_file(
    story_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role([UserRole.ADMIN, UserRole.TEACHER]))
):
    """
    Upload audio file for a story (Admin or Teacher)
    """
    story = db.query(Story).filter(Story.id == story_id).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Delete old audio if exists
    if story.ses_dosyasi:
        delete_file(story.ses_dosyasi)
    
    # Save new audio
    file_path = await save_upload_file(file, file_type="audio")
    story.ses_dosyasi = file_path
    
    db.commit()
    db.refresh(story)
    
    return story

# Quiz Question Schemas
class QuizQuestionCreate(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str  # A, B, C, or D

class QuizQuestionResponse(BaseModel):
    id: int
    story_id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    
    class Config:
        from_attributes = True

@router.get("/{story_id}/quiz", response_model=List[QuizQuestionResponse])
async def get_quiz_questions(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all quiz questions for a story
    """
    from models.quiz import QuizQuestion
    
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    questions = db.query(QuizQuestion).filter(QuizQuestion.story_id == story_id).all()
    return questions

@router.post("/{story_id}/quiz", response_model=QuizQuestionResponse, status_code=status.HTTP_201_CREATED)
async def add_quiz_question(
    story_id: int,
    question_data: QuizQuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Add a quiz question to a story (Admin only)
    """
    from models.quiz import QuizQuestion
    
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Validate correct answer
    if question_data.correct_answer not in ['A', 'B', 'C', 'D']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Correct answer must be A, B, C, or D"
        )
    
    new_question = QuizQuestion(
        story_id=story_id,
        question_text=question_data.question_text,
        option_a=question_data.option_a,
        option_b=question_data.option_b,
        option_c=question_data.option_c,
        option_d=question_data.option_d,
        correct_answer=question_data.correct_answer
    )
    
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    
    return new_question

@router.delete("/{story_id}/quiz/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz_question(
    story_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Delete a quiz question (Admin only)
    """
    from models.quiz import QuizQuestion
    
    question = db.query(QuizQuestion).filter(
        QuizQuestion.id == question_id,
        QuizQuestion.story_id == story_id
    ).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    db.delete(question)
    db.commit()
    
    return None


# ===== STORY STATISTICS =====

@router.get("/{story_id}/stats")
async def get_story_statistics(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role([UserRole.ADMIN, UserRole.TEACHER]))
):
    """
    Get statistics for a story: read count, assignment count, error count
    """
    from models.reading_activity import PreReading, Practice
    from models.assignment import Assignment
    from models.evaluation import TeacherEvaluation
    
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hikaye bulunamadı"
        )
    
    # Count unique readers (pre-reading)
    read_count = db.query(PreReading.ogrenci_id).filter(
        PreReading.story_id == story_id
    ).distinct().count()
    
    # Count practice sessions
    practice_count = db.query(Practice).filter(
        Practice.story_id == story_id
    ).count()
    
    # Count assignments
    assignment_count = db.query(Assignment).filter(
        Assignment.story_id == story_id
    ).count()
    
    # Count completed assignments
    completed_assignments = db.query(Assignment).filter(
        Assignment.story_id == story_id,
        Assignment.status == 'tamamlandi'
    ).count()
    
    # Count evaluations with errors (hatali_kelime not empty)
    error_count = db.query(TeacherEvaluation).filter(
        TeacherEvaluation.story_id == story_id,
        TeacherEvaluation.hatali_kelime != None,
        TeacherEvaluation.hatali_kelime != ""
    ).count()
    
    # Average scores
    avg_fluency = db.query(func.avg(TeacherEvaluation.akicilik_puan)).filter(
        TeacherEvaluation.story_id == story_id,
        TeacherEvaluation.akicilik_puan != None
    ).scalar()
    
    avg_comprehension = db.query(func.avg(TeacherEvaluation.acik_soru_puani)).filter(
        TeacherEvaluation.story_id == story_id,
        TeacherEvaluation.acik_soru_puani != None
    ).scalar()
    
    return {
        "story_id": story_id,
        "baslik": story.baslik,
        "okunma_sayisi": read_count,
        "pratik_sayisi": practice_count,
        "atanma_sayisi": assignment_count,
        "tamamlanan_odev": completed_assignments,
        "hata_sayisi": error_count,
        "ortalama_akicilik": round(avg_fluency, 1) if avg_fluency else None,
        "ortalama_anlama": round(avg_comprehension, 1) if avg_comprehension else None
    }


@router.get("/popular/list")
async def get_popular_stories(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get most popular stories by read count
    """
    from models.reading_activity import PreReading
    from sqlalchemy import desc
    
    # Get stories with read counts
    popular = db.query(
        Story,
        func.count(PreReading.ogrenci_id.distinct()).label('read_count')
    ).outerjoin(
        PreReading, Story.id == PreReading.story_id
    ).group_by(Story.id).order_by(desc('read_count')).limit(limit).all()
    
    result = []
    for story, read_count in popular:
        result.append({
            "id": story.id,
            "baslik": story.baslik,
            "ders": story.ders,
            "sinif_duzeyi": story.sinif_duzeyi,
            "okunma_sayisi": read_count or 0,
            "kapak_gorseli": story.kapak_gorseli
        })
    
    return {"stories": result}

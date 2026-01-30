from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
from models.user import User, UserRole
from models.reading_activity import Answer, PreReading, Practice
from models.evaluation import TeacherEvaluation
from models.story import Story
from models.speech_practice import SpeechPracticeRecord
import json
from auth.dependencies import get_current_user, require_role
from utils.progress_calculator import calculate_improvement, get_student_progress_summary
from sqlalchemy import func

router = APIRouter(prefix="/api/teacher", tags=["Teacher Panel"])

# Pydantic schemas
class StudentInfo(BaseModel):
    id: int
    ad_soyad: str
    email: str
    sinif_duzeyi: Optional[int]
    
    class Config:
        from_attributes = True

class EvaluationCreate(BaseModel):
    ogrenci_id: int
    story_id: int
    hatali_kelime: Optional[str] = None
    akicilik_puan: Optional[int] = None
    acik_soru_puani: Optional[int] = None
    ogretmen_yorumu: Optional[str] = None

class AssignStudentRequest(BaseModel):
    student_email: str

class EvaluationResponse(BaseModel):
    id: int
    ogrenci_id: int
    story_id: int
    ogretmen_id: int
    hatali_kelime: Optional[str]
    akicilik_puan: Optional[int]
    acik_soru_puani: Optional[int]
    ogretmen_yorumu: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/all")
async def get_all_teachers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of all teachers (for messaging purposes)
    """
    teachers = db.query(User).filter(User.rol == UserRole.TEACHER).all()
    return [{"id": t.id, "ad_soyad": t.ad_soyad, "email": t.email} for t in teachers]

@router.get("/students", response_model=List[StudentInfo])
async def get_students(
    sinif_duzeyi: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of students, optionally filtered by grade level and search term.
    Teachers only see their own students. Admins see all.
    """
    if current_user.rol not in [UserRole.TEACHER, UserRole.ADMIN]:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    query = db.query(User).filter(User.rol == UserRole.STUDENT)
    
    # Filter by teacher if role is Teacher
    if current_user.rol == UserRole.TEACHER:
        query = query.filter(User.teacher_id == current_user.id)
    
    if sinif_duzeyi:
        query = query.filter(User.sinif_duzeyi == sinif_duzeyi)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(User.ad_soyad.ilike(search_term))
    
    students = query.order_by(User.ad_soyad).all()
    return students

@router.post("/assign-student")
async def assign_student(
    data: AssignStudentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a student to the current teacher (or Admin logic)
    """
    if current_user.rol not in [UserRole.TEACHER, UserRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    student = db.query(User).filter(User.email == data.student_email, User.rol == UserRole.STUDENT).first()
    if not student:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found with this email")
         
    # Assign to current user (if teacher)
    if current_user.rol == UserRole.TEACHER:
        student.teacher_id = current_user.id
    # If admin, logic might differ, but for now allow Admin to assign to themselves or ignore
    # Let's say Admin can assign to themselves for testing
    else:
        # TODO: Allow Admin to specify teacher_id in future
        student.teacher_id = current_user.id 

    db.commit()
    
    return {"message": "Student assigned successfully", "student": student.ad_soyad}

@router.get("/student/{student_id}/progress")
async def get_student_progress(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Get detailed progress for a specific student
    """
    # Verify student exists
    student = db.query(User).filter(
        User.id == student_id,
        User.rol == UserRole.STUDENT
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Get overall summary
    summary = get_student_progress_summary(student_id, db)
    
    # Get reading history
    from models.reading_activity import PreReading
    
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == student_id
    ).all()
    
    reading_history = []
    for pr in pre_readings:
        story = db.query(Story).filter(Story.id == pr.story_id).first()
        if story:
            # Get practice count
            practice_count = db.query(Practice).filter(
                Practice.ogrenci_id == student_id,
                Practice.story_id == story.id
            ).count()
            
            # Get quiz result
            answer = db.query(Answer).filter(
                Answer.ogrenci_id == student_id,
                Answer.story_id == story.id
            ).first()
            
            # Get evaluation
            evaluation = db.query(TeacherEvaluation).filter(
                TeacherEvaluation.ogrenci_id == student_id,
                TeacherEvaluation.story_id == story.id
            ).first()
            
            # Calculate improvement
            improvement = calculate_improvement(student_id, story.id, db)
            
            reading_history.append({
                "story_id": story.id,
                "story_title": story.baslik,
                "pre_reading_speed": pr.okuma_hizi,
                "practice_count": practice_count,
                "quiz_score": answer.dogru_sayisi if answer else None,
                "has_evaluation": evaluation is not None,
                "evaluation_pending": answer is not None and evaluation is None,
                "improvement": improvement,
                "completed_at": pr.created_at.isoformat() if pr.created_at else None
            })
    
    return {
        "student": {
            "id": student.id,
            "ad_soyad": student.ad_soyad,
            "sinif_duzeyi": student.sinif_duzeyi
        },
        "summary": summary,
        "reading_history": reading_history
    }

@router.get("/student/{student_id}/story/{story_id}/answers")
async def get_student_answers(
    student_id: int,
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Get student's answers for a specific story
    """
    # Get story
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )
    
    # Get student
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Get answers
    answer = db.query(Answer).filter(
        Answer.ogrenci_id == student_id,
        Answer.story_id == story_id
    ).first()
    
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No answers found for this story"
        )
    
    # Get quiz questions
    from models.quiz import QuizQuestion
    questions = db.query(QuizQuestion).filter(
        QuizQuestion.story_id == story_id
    ).all()
    
    # Parse student answers
    import json
    student_answers = json.loads(answer.cevaplar) if answer.cevaplar else {}
    
    # Format response
    quiz_results = []
    for q in questions:
        student_answer = student_answers.get(str(q.id))
        is_correct = student_answer == q.correct_answer if student_answer else False
        
        quiz_results.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "options": {
                "A": q.option_a,
                "B": q.option_b,
                "C": q.option_c,
                "D": q.option_d
            },
            "correct_answer": q.correct_answer,
            "student_answer": student_answer,
            "is_correct": is_correct
        })
    
    return {
        "story_title": story.baslik,
        "student_name": student.ad_soyad,
        "quiz_score": answer.dogru_sayisi,
        "open_ended_answer": answer.acik_ucu_cevap,
        "quiz_results": quiz_results,
        "submitted_at": answer.created_at.isoformat() if answer.created_at else None
    }

@router.post("/evaluate", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    evaluation_data: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Create or update teacher evaluation for a student's story
    """
    # Check if evaluation already exists
    existing = db.query(TeacherEvaluation).filter(
        TeacherEvaluation.ogrenci_id == evaluation_data.ogrenci_id,
        TeacherEvaluation.story_id == evaluation_data.story_id
    ).first()
    
    if existing:
        # Update existing evaluation
        existing.hatali_kelime = evaluation_data.hatali_kelime
        existing.akicilik_puan = evaluation_data.akicilik_puan
        existing.acik_soru_puani = evaluation_data.acik_soru_puani
        existing.ogretmen_yorumu = evaluation_data.ogretmen_yorumu
        existing.ogretmen_id = current_user.id
        
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new evaluation
        new_evaluation = TeacherEvaluation(
            ogrenci_id=evaluation_data.ogrenci_id,
            story_id=evaluation_data.story_id,
            ogretmen_id=current_user.id,
            hatali_kelime=evaluation_data.hatali_kelime,
            akicilik_puan=evaluation_data.akicilik_puan,
            acik_soru_puani=evaluation_data.acik_soru_puani,
            ogretmen_yorumu=evaluation_data.ogretmen_yorumu
        )
        
        db.add(new_evaluation)
        db.commit()
        db.refresh(new_evaluation)
        
        return new_evaluation

@router.get("/pending-reviews")
async def get_pending_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Get list of students with pending evaluations
    """
    # Get all students who have submitted answers but don't have evaluations
    from sqlalchemy import and_, not_, exists
    
    # Subquery for answers that have evaluations
    evaluated_subquery = db.query(TeacherEvaluation.ogrenci_id, TeacherEvaluation.story_id).subquery()
    
    # Get answers without evaluations
    pending = db.query(Answer, User, Story).join(
        User, Answer.ogrenci_id == User.id
    ).join(
        Story, Answer.story_id == Story.id
    ).filter(
        not_(
            and_(
                Answer.ogrenci_id == evaluated_subquery.c.ogrenci_id,
                Answer.story_id == evaluated_subquery.c.story_id
            )
        )
    ).all()
    
    pending_list = []
    for answer, student, story in pending:
        pending_list.append({
            "student_id": student.id,
            "student_name": student.ad_soyad,
            "story_id": story.id,
            "story_title": story.baslik,
            "submitted_at": answer.created_at.isoformat() if answer.created_at else None
        })
    
    return {"pending_reviews": pending_list}

@router.get("/analytics/class-summary")
async def get_class_analytics(
    sinif_duzeyi: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Get class-wide analytics for charts
    """
    # Get students (optionally filtered by grade)
    students_query = db.query(User).filter(User.rol == UserRole.STUDENT)
    if sinif_duzeyi:
        students_query = students_query.filter(User.sinif_duzeyi == sinif_duzeyi)
    students = students_query.all()
    
    # Calculate stats for each student
    student_stats = []
    for student in students:
        # Count completed stories
        completed_count = db.query(Answer).filter(Answer.ogrenci_id == student.id).count()
        
        # Average comprehension score
        avg_score = db.query(func.avg(Answer.dogru_sayisi)).filter(
            Answer.ogrenci_id == student.id
        ).scalar() or 0
        
        # Get evaluations
        evaluations = db.query(TeacherEvaluation).filter(
            TeacherEvaluation.ogrenci_id == student.id
        ).all()
        
        avg_fluency = sum(e.akicilik_puan for e in evaluations if e.akicilik_puan) / len(evaluations) if evaluations else 0
        avg_comprehension = sum(e.acik_soru_puani for e in evaluations if e.acik_soru_puani) / len(evaluations) if evaluations else 0
        
        student_stats.append({
            "id": student.id,
            "name": student.ad_soyad,
            "grade": student.sinif_duzeyi,
            "completed_stories": completed_count,
            "avg_quiz_score": round(float(avg_score) * 25, 1),  # Convert to percentage
            "avg_fluency": round(avg_fluency, 1),
            "avg_comprehension": round(avg_comprehension, 1)
        })
    
    # Overall class statistics
    total_students = len(students)
    total_completions = sum(s["completed_stories"] for s in student_stats)
    avg_class_score = sum(s["avg_quiz_score"] for s in student_stats) / total_students if total_students > 0 else 0
    
    return {
        "class_summary": {
            "total_students": total_students,
            "total_completions": total_completions,
            "average_score": round(avg_class_score, 1)
        },
        "student_stats": student_stats
    }
from utils.notification_helper import notify_parent_of_evaluation

@router.post('/evaluation', response_model=EvaluationResponse)
async def create_evaluation(
    evaluation: EvaluationCreate,
    current_user: User = Depends(require_role(UserRole.TEACHER)),
    db: Session = Depends(get_db)
):
    '''Create teacher evaluation with parent notification'''
    # Verify student and story
    student = db.query(User).filter(User.id == evaluation.ogrenci_id).first()
    if not student:
        raise HTTPException(status_code=404, detail='Student not found')
    
    story = db.query(Story).filter(Story.id == evaluation.story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail='Story not found')
    
    # Create evaluation
    new_eval = TeacherEvaluation(
        ogrenci_id=evaluation.ogrenci_id,
        story_id=evaluation.story_id,
        ogretmen_id=current_user.id,
        hatali_kelime=evaluation.hatali_kelime,
        akicilik_puan=evaluation.akicilik_puan,
        acik_soru_puani=evaluation.acik_soru_puani,
        ogretmen_yorumu=evaluation.ogretmen_yorumu
    )
    
    db.add(new_eval)
    db.commit()
    db.refresh(new_eval)
    
    # Send notification to parent
    try:
        notify_parent_of_evaluation(db, student.id, current_user.ad_soyad, story.baslik)
    except Exception as e:
        print(f'Notification error: {e}')
    
    return new_eval

@router.get("/student/{student_id}/speech-practice")
async def get_student_speech_practice(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Get speech practice history for a specific student
    """
    # Verify student exists
    student = db.query(User).filter(
        User.id == student_id,
        User.rol == UserRole.STUDENT
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Get all speech practice records for this student
    records = db.query(SpeechPracticeRecord).filter(
        SpeechPracticeRecord.ogrenci_id == student_id
    ).order_by(
        SpeechPracticeRecord.hikaye_id,
        SpeechPracticeRecord.deneme_no.desc()
    ).all()
    
    # Group by story
    stories_data = {}
    for record in records:
        story_id = record.hikaye_id
        if story_id not in stories_data:
            story = db.query(Story).filter(Story.id == story_id).first()
            stories_data[story_id] = {
                "story_id": story_id,
                "story_title": story.baslik if story else "Bilinmeyen Hikaye",
                "attempts": []
            }
        
        stories_data[story_id]["attempts"].append({
            "deneme_no": record.deneme_no,
            "dogru_kelime": record.dogru_kelime,
            "hatali_kelime": record.hatali_kelime,
            "atlanan_kelime": record.atlanan_kelime,
            "toplam_kelime": record.toplam_kelime,
            "dogruluk_orani": record.dogruluk_orani,
            "hatali_kelimeler": json.loads(record.hatali_kelimeler) if record.hatali_kelimeler else [],
            "created_at": str(record.created_at) if record.created_at else None
        })
    
    return {
        "student_id": student_id,
        "student_name": student.ad_soyad,
        "stories": list(stories_data.values())
    }


# ===== TEACHER PROFILE ENDPOINTS =====

class TeacherProfileUpdate(BaseModel):
    brans: Optional[str] = None
    mezuniyet: Optional[str] = None
    biyografi: Optional[str] = None


@router.get("/profile/me")
async def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Get current teacher's profile with statistics
    """
    # Get student count
    student_count = db.query(User).filter(
        User.teacher_id == current_user.id,
        User.rol == UserRole.STUDENT
    ).count()
    
    # Get story/article count
    story_count = db.query(Story).filter(Story.olusturan_id == current_user.id).count()
    
    return {
        "id": current_user.id,
        "ad_soyad": current_user.ad_soyad,
        "email": current_user.email,
        "brans": current_user.brans,
        "mezuniyet": current_user.mezuniyet,
        "biyografi": current_user.biyografi,
        "ogrenci_sayisi": student_count,
        "makale_sayisi": story_count,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }


@router.put("/profile/me")
async def update_my_profile(
    profile: TeacherProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Update current teacher's profile
    """
    if profile.brans is not None:
        current_user.brans = profile.brans
    if profile.mezuniyet is not None:
        current_user.mezuniyet = profile.mezuniyet
    if profile.biyografi is not None:
        current_user.biyografi = profile.biyografi
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "success": True,
        "message": "Profil güncellendi",
        "profile": {
            "brans": current_user.brans,
            "mezuniyet": current_user.mezuniyet,
            "biyografi": current_user.biyografi
        }
    }


@router.get("/profile/{teacher_id}")
async def get_teacher_profile(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a teacher's public profile (for students/parents to view)
    """
    teacher = db.query(User).filter(
        User.id == teacher_id,
        User.rol == UserRole.TEACHER
    ).first()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğretmen bulunamadı"
        )
    
    # Get statistics
    student_count = db.query(User).filter(
        User.teacher_id == teacher.id,
        User.rol == UserRole.STUDENT
    ).count()
    
    story_count = db.query(Story).filter(Story.olusturan_id == teacher.id).count()
    
    return {
        "id": teacher.id,
        "ad_soyad": teacher.ad_soyad,
        "brans": teacher.brans,
        "mezuniyet": teacher.mezuniyet,
        "biyografi": teacher.biyografi,
        "ogrenci_sayisi": student_count,
        "makale_sayisi": story_count
    }


@router.get("/list")
async def list_teachers(
    brans: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all teachers (for students to find and request)
    """
    query = db.query(User).filter(
        User.rol == UserRole.TEACHER,
        User.is_approved == True
    )
    
    if brans:
        query = query.filter(User.brans.ilike(f"%{brans}%"))
    
    if search:
        query = query.filter(User.ad_soyad.ilike(f"%{search}%"))
    
    teachers = query.all()
    
    result = []
    for t in teachers:
        student_count = db.query(User).filter(
            User.teacher_id == t.id,
            User.rol == UserRole.STUDENT
        ).count()
        
        story_count = db.query(Story).filter(Story.olusturan_id == t.id).count()
        
        result.append({
            "id": t.id,
            "ad_soyad": t.ad_soyad,
            "brans": t.brans,
            "mezuniyet": t.mezuniyet,
            "ogrenci_sayisi": student_count,
            "makale_sayisi": story_count
        })
    
    return {"teachers": result}


# ===== STUDENT-TEACHER REQUEST SYSTEM =====

from models.teacher_request import TeacherRequest, RequestStatus

class TeacherRequestCreate(BaseModel):
    teacher_id: int
    message: Optional[str] = None


class RequestResponse(BaseModel):
    accept: bool
    message: Optional[str] = None


@router.post("/request")
async def send_teacher_request(
    request: TeacherRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT))
):
    """
    Student sends a request to join a teacher
    """
    # Check if teacher exists
    teacher = db.query(User).filter(
        User.id == request.teacher_id,
        User.rol == UserRole.TEACHER
    ).first()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğretmen bulunamadı"
        )
    
    # Check if already linked
    if current_user.teacher_id == request.teacher_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zaten bu öğretmene bağlısınız"
        )
    
    # Check for existing pending request
    existing = db.query(TeacherRequest).filter(
        TeacherRequest.student_id == current_user.id,
        TeacherRequest.teacher_id == request.teacher_id,
        TeacherRequest.status == RequestStatus.PENDING
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu öğretmene zaten bir istek gönderilmiş"
        )
    
    # Create request
    new_request = TeacherRequest(
        student_id=current_user.id,
        teacher_id=request.teacher_id,
        message=request.message
    )
    db.add(new_request)
    db.commit()
    
    # Notify teacher
    from utils.notification_helper import create_notification
    create_notification(
        db=db,
        user_id=request.teacher_id,
        type="request",
        title="Yeni Öğrenci İsteği",
        message=f"{current_user.ad_soyad} sizinle çalışmak istiyor",
        link="/teacher/dashboard"
    )
    
    return {"success": True, "message": "İstek gönderildi"}


@router.get("/requests/pending")
async def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Get pending student requests for teacher
    """
    requests = db.query(TeacherRequest).filter(
        TeacherRequest.teacher_id == current_user.id,
        TeacherRequest.status == RequestStatus.PENDING
    ).order_by(TeacherRequest.created_at.desc()).all()
    
    result = []
    for req in requests:
        result.append({
            "id": req.id,
            "student_id": req.student_id,
            "student_name": req.student.ad_soyad if req.student else "Unknown",
            "student_grade": req.student.sinif_duzeyi if req.student else None,
            "message": req.message,
            "created_at": req.created_at.isoformat()
        })
    
    return {"requests": result, "count": len(result)}


@router.post("/requests/{request_id}/respond")
async def respond_to_request(
    request_id: int,
    response: RequestResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Accept or reject a student request
    """
    from datetime import datetime
    
    req = db.query(TeacherRequest).filter(
        TeacherRequest.id == request_id,
        TeacherRequest.teacher_id == current_user.id
    ).first()
    
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İstek bulunamadı"
        )
    
    if req.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu istek zaten yanıtlanmış"
        )
    
    if response.accept:
        req.status = RequestStatus.ACCEPTED
        
        # Link student to teacher
        student = db.query(User).filter(User.id == req.student_id).first()
        if student:
            student.teacher_id = current_user.id
        
        notification_title = "İstek Kabul Edildi"
        notification_msg = f"{current_user.ad_soyad} isteğinizi kabul etti"
    else:
        req.status = RequestStatus.REJECTED
        notification_title = "İstek Reddedildi"
        notification_msg = f"{current_user.ad_soyad} isteğinizi reddetti"
    
    req.responded_at = datetime.utcnow()
    req.response_message = response.message
    db.commit()
    
    # Notify student
    from utils.notification_helper import create_notification
    create_notification(
        db=db,
        user_id=req.student_id,
        type="request",
        title=notification_title,
        message=notification_msg,
        link="/student/dashboard"
    )
    
    return {"success": True, "message": "Yanıt gönderildi"}


@router.get("/my-requests")
async def get_my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT))
):
    """
    Get student's own requests
    """
    requests = db.query(TeacherRequest).filter(
        TeacherRequest.student_id == current_user.id
    ).order_by(TeacherRequest.created_at.desc()).all()
    
    result = []
    for req in requests:
        result.append({
            "id": req.id,
            "teacher_id": req.teacher_id,
            "teacher_name": req.teacher.ad_soyad if req.teacher else "Unknown",
            "status": req.status.value,
            "message": req.message,
            "response_message": req.response_message,
            "created_at": req.created_at.isoformat()
        })
    
    return {"requests": result}

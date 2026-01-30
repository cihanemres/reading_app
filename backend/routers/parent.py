from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User, UserRole
from models.evaluation import TeacherEvaluation
from auth.dependencies import get_current_user, require_role
from utils.progress_calculator import get_student_progress_summary, calculate_improvement

router = APIRouter(prefix="/api/parent", tags=["Parent Panel"])

@router.get("/children")
async def get_children(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PARENT))
):
    """
    Get list of children linked to this parent
    """
    children = db.query(User).filter(
        User.rol == UserRole.STUDENT,
        User.parent_id == current_user.id
    ).all()
    
    return {
        "children": [
            {
                "id": child.id,
                "ad_soyad": child.ad_soyad,
                "sinif_duzeyi": child.sinif_duzeyi
            }
            for child in children
        ]
    }

@router.get("/child/{child_id}/progress")
async def get_child_progress(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PARENT))
):
    """
    Get progress for a specific child
    """
    # Verify child belongs to this parent
    child = db.query(User).filter(
        User.id == child_id,
        User.rol == UserRole.STUDENT,
        User.parent_id == current_user.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found or not linked to your account"
        )
    
    # Get overall summary
    summary = get_student_progress_summary(child_id, db)
    
    # Get progress for each story
    from models.reading_activity import PreReading
    from models.story import Story
    
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == child_id
    ).all()
    
    stories_progress = []
    for pr in pre_readings:
        story = db.query(Story).filter(Story.id == pr.story_id).first()
        if story:
            improvement = calculate_improvement(child_id, story.id, db)
            stories_progress.append({
                "story_title": story.baslik,
                "improvement": improvement
            })
    
    return {
        "child": {
            "id": child.id,
            "ad_soyad": child.ad_soyad,
            "sinif_duzeyi": child.sinif_duzeyi
        },
        "summary": summary,
        "stories": stories_progress
    }

@router.get("/child/{child_id}/teacher-comments")
async def get_teacher_comments(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PARENT))
):
    """
    Get teacher comments and evaluations for a child
    """
    # Verify child belongs to this parent
    child = db.query(User).filter(
        User.id == child_id,
        User.rol == UserRole.STUDENT,
        User.parent_id == current_user.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found or not linked to your account"
        )
    
    # Get all evaluations
    evaluations = db.query(TeacherEvaluation).filter(
        TeacherEvaluation.ogrenci_id == child_id
    ).all()
    
    comments = []
    for evaluation in evaluations:
        from models.story import Story
        story = db.query(Story).filter(Story.id == evaluation.story_id).first()
        teacher = db.query(User).filter(User.id == evaluation.ogretmen_id).first()
        
        if story and teacher:
            comments.append({
                "story_title": story.baslik,
                "teacher_name": teacher.ad_soyad,
                "akicilik_puan": evaluation.akicilik_puan,
                "acik_soru_puani": evaluation.acik_soru_puani,
                "ogretmen_yorumu": evaluation.ogretmen_yorumu,
                "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None
            })
    
    return {
        "child_name": child.ad_soyad,
        "comments": comments
    }

@router.get("/child/{child_id}/recommendations")
async def get_practice_recommendations(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PARENT))
):
    """
    Get practice recommendations for a child
    """
    # Verify child belongs to this parent
    child = db.query(User).filter(
        User.id == child_id,
        User.rol == UserRole.STUDENT,
        User.parent_id == current_user.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found or not linked to your account"
        )
    
    # Get stories that need more practice (low practice count or low scores)
    from models.reading_activity import PreReading, Practice
    from models.story import Story
    
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == child_id
    ).all()
    
    recommendations = []
    for pr in pre_readings:
        story = db.query(Story).filter(Story.id == pr.story_id).first()
        if not story:
            continue
        
        # Count practice attempts
        practice_count = db.query(Practice).filter(
            Practice.ogrenci_id == child_id,
            Practice.story_id == story.id
        ).count()
        
        # Get evaluation
        evaluation = db.query(TeacherEvaluation).filter(
            TeacherEvaluation.ogrenci_id == child_id,
            TeacherEvaluation.story_id == story.id
        ).first()
        
        # Recommend if: few practices OR low scores
        should_recommend = False
        reason = []
        
        if practice_count < 3:
            should_recommend = True
            reason.append(f"Only {practice_count} practice session(s)")
        
        if evaluation:
            if evaluation.akicilik_puan and evaluation.akicilik_puan < 7:
                should_recommend = True
                reason.append(f"Fluency score: {evaluation.akicilik_puan}/10")
            if evaluation.acik_soru_puani and evaluation.acik_soru_puani < 7:
                should_recommend = True
                reason.append(f"Comprehension score: {evaluation.acik_soru_puani}/10")
        
        if should_recommend:
            recommendations.append({
                "story_id": story.id,
                "story_title": story.baslik,
                "practice_count": practice_count,
                "reasons": reason
            })
    
    return {
        "child_name": child.ad_soyad,
        "recommendations": recommendations
    }


# ===== CHILD LINKING ENDPOINTS =====

from pydantic import BaseModel
import secrets
import string

class LinkChildRequest(BaseModel):
    child_email: str

class LinkCodeResponse(BaseModel):
    link_code: str
    expires_in: str

# Simple in-memory storage for link codes (in production, use Redis or DB)
link_codes = {}  # user_id -> code

@router.post("/link-child")
async def link_child_by_email(
    request: LinkChildRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PARENT))
):
    """
    Link a child to parent account by email
    The child must exist and not be linked to another parent
    """
    # Find the child
    child = db.query(User).filter(
        User.email == request.child_email,
        User.rol == UserRole.STUDENT
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğrenci bulunamadı. E-posta adresini kontrol edin."
        )
    
    if child.parent_id and child.parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu öğrenci zaten başka bir veliye bağlı."
        )
    
    if child.parent_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu öğrenci zaten sizin hesabınıza bağlı."
        )
    
    # Link the child
    child.parent_id = current_user.id
    db.commit()
    
    # Create notification
    from utils.notification_helper import create_notification
    create_notification(
        db=db,
        user_id=child.id,
        type="account",
        title="Veli Bağlantısı",
        message=f"Hesabınız {current_user.ad_soyad} adlı veliye bağlandı.",
        link="/student/dashboard"
    )
    
    return {
        "success": True,
        "message": f"{child.ad_soyad} başarıyla hesabınıza bağlandı.",
        "child": {
            "id": child.id,
            "ad_soyad": child.ad_soyad,
            "sinif_duzeyi": child.sinif_duzeyi
        }
    }


@router.delete("/unlink-child/{child_id}")
async def unlink_child(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PARENT))
):
    """
    Unlink a child from parent account
    """
    child = db.query(User).filter(
        User.id == child_id,
        User.rol == UserRole.STUDENT,
        User.parent_id == current_user.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Çocuk bulunamadı veya hesabınıza bağlı değil."
        )
    
    child.parent_id = None
    db.commit()
    
    return {
        "success": True,
        "message": f"{child.ad_soyad} hesabınızdan ayrıldı."
    }


@router.get("/dashboard-summary")
async def get_parent_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PARENT))
):
    """
    Get dashboard summary for parent - all children stats
    """
    children = db.query(User).filter(
        User.rol == UserRole.STUDENT,
        User.parent_id == current_user.id
    ).all()
    
    if not children:
        return {
            "has_children": False,
            "message": "Henüz hiçbir öğrenci hesabınıza bağlı değil.",
            "children_summary": []
        }
    
    children_summary = []
    for child in children:
        summary = get_student_progress_summary(child.id, db)
        
        # Get pending assignments
        from models.assignment import Assignment
        pending = db.query(Assignment).filter(
            Assignment.student_id == child.id,
            Assignment.status == 'bekliyor'
        ).count()
        
        children_summary.append({
            "id": child.id,
            "ad_soyad": child.ad_soyad,
            "sinif_duzeyi": child.sinif_duzeyi,
            "total_stories": summary.get("total_stories", 0),
            "total_practice": summary.get("total_practice_sessions", 0),
            "average_speed": summary.get("average_speed_wpm", 0),
            "pending_assignments": pending
        })
    
    return {
        "has_children": True,
        "children_count": len(children),
        "children_summary": children_summary
    }


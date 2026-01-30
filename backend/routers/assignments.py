from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from database import get_db
from models.user import User, UserRole
from models.story import Story
from models.assignment import Assignment, AssignmentStatus
from auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/assignments", tags=["Assignments"])

# Pydantic Schemas
class AssignmentCreate(BaseModel):
    story_id: int
    student_ids: List[int]
    due_date: Optional[datetime] = None

class AssignmentResponse(BaseModel):
    id: int
    subject: str
    story_title: str
    story_id: int
    status: AssignmentStatus
    assigned_at: datetime
    due_date: Optional[datetime]
    student_name: Optional[str] = None # For teacher view
    
    class Config:
        from_attributes = True

# Teacher Endpoints

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_assignments(
    request: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Assign a story to multiple students (Teacher only)
    """
    # Verify story exists
    story = db.query(Story).filter(Story.id == request.story_id).first()
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hikaye bulunamadı"
        )
    
    created_count = 0
    
    for student_id in request.student_ids:
        # Verify student belongs to teacher (security check)
        student = db.query(User).filter(
            User.id == student_id,
            User.teacher_id == current_user.id
        ).first()
        
        if not student:
            continue # Skip invalid students
            
        # Check if already assigned
        existing = db.query(Assignment).filter(
            Assignment.student_id == student_id,
            Assignment.story_id == request.story_id,
            Assignment.status != AssignmentStatus.COMPLETED
        ).first()
        
        if existing:
            continue # Skip duplicates
            
        new_assignment = Assignment(
            teacher_id=current_user.id,
            student_id=student_id,
            story_id=request.story_id,
            due_date=request.due_date,
            status=AssignmentStatus.PENDING
        )
        db.add(new_assignment)
        
        # Send notification to student
        from utils.notification_helper import notify_assignment
        due_str = request.due_date.strftime("%d/%m/%Y") if request.due_date else None
        notify_assignment(db, student_id, current_user.ad_soyad, story.baslik, due_str)
        
        created_count += 1
    
    db.commit()
    
    return {
        "success": True, 
        "message": f"{created_count} öğrenciye ödev atandı."
    }

@router.get("/teacher/list", response_model=List[AssignmentResponse])
async def list_teacher_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    List assignments created by the current teacher
    """
    assignments = db.query(Assignment)\
        .filter(Assignment.teacher_id == current_user.id)\
        .order_by(Assignment.assigned_at.desc())\
        .all()
    
    # Transform response to include detail
    results = []
    for a in assignments:
        results.append({
            "id": a.id,
            "subject": a.story.ders if a.story else "Unknown",
            "story_title": a.story.baslik if a.story else "Unknown",
            "story_id": a.story_id,
            "status": a.status,
            "assigned_at": a.assigned_at,
            "due_date": a.due_date,
            "student_name": a.student.ad_soyad if a.student else "Unknown"
        })
        
    return results

# Student Endpoints

@router.get("/student/me", response_model=List[AssignmentResponse])
async def list_my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT))
):
    """
    List assignments for the current student
    """
    assignments = db.query(Assignment)\
        .filter(Assignment.student_id == current_user.id)\
        .order_by(Assignment.status, Assignment.due_date)\
        .all()
        
    results = []
    for a in assignments:
        results.append({
            "id": a.id,
            "subject": a.story.ders if a.story else "Genel",
            "story_title": a.story.baslik if a.story else "Hikaye",
            "story_id": a.story_id,
            "status": a.status,
            "assigned_at": a.assigned_at,
            "due_date": a.due_date
        })
        
    return results


@router.post("/{assignment_id}/complete")
async def complete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT))
):
    """
    Mark an assignment as completed
    """
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.student_id == current_user.id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ödev bulunamadı"
        )
    
    if assignment.status == AssignmentStatus.COMPLETED:
        return {"success": True, "message": "Bu ödev zaten tamamlanmış"}
    
    assignment.status = AssignmentStatus.COMPLETED
    assignment.completed_at = datetime.utcnow()
    db.commit()
    
    # Notify teacher
    from utils.notification_helper import create_notification
    create_notification(
        db=db,
        user_id=assignment.teacher_id,
        type="assignment",
        title="Ödev Tamamlandı",
        message=f"{current_user.ad_soyad} '{assignment.story.baslik}' ödevini tamamladı.",
        link="/teacher/dashboard"
    )
    
    return {"success": True, "message": "Ödev tamamlandı olarak işaretlendi"}


@router.get("/student/pending-count")
async def get_pending_assignment_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT))
):
    """
    Get count of pending assignments for badge display
    """
    count = db.query(Assignment).filter(
        Assignment.student_id == current_user.id,
        Assignment.status == AssignmentStatus.PENDING
    ).count()
    
    # Check for urgent (due within 24 hours)
    from datetime import timedelta
    urgent = db.query(Assignment).filter(
        Assignment.student_id == current_user.id,
        Assignment.status == AssignmentStatus.PENDING,
        Assignment.due_date != None,
        Assignment.due_date <= datetime.utcnow() + timedelta(hours=24)
    ).count()
    
    return {
        "pending": count,
        "urgent": urgent
    }


@router.get("/teacher/stats")
async def get_teacher_assignment_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Get assignment statistics for teacher dashboard
    """
    assignments = db.query(Assignment).filter(
        Assignment.teacher_id == current_user.id
    ).all()
    
    total = len(assignments)
    pending = sum(1 for a in assignments if a.status == AssignmentStatus.PENDING)
    completed = sum(1 for a in assignments if a.status == AssignmentStatus.COMPLETED)
    
    # Overdue assignments
    overdue = sum(1 for a in assignments 
                  if a.status == AssignmentStatus.PENDING 
                  and a.due_date 
                  and a.due_date < datetime.utcnow())
    
    return {
        "total": total,
        "pending": pending,
        "completed": completed,
        "overdue": overdue,
        "completion_rate": round((completed / total) * 100) if total > 0 else 0
    }


@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Delete an assignment (Teacher only)
    """
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.teacher_id == current_user.id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ödev bulunamadı"
        )
    
    db.delete(assignment)
    db.commit()
    
    return {"success": True, "message": "Ödev silindi"}


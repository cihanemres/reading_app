from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from database import get_db
from models.user import User, UserRole
from models.story import Story
from auth.dependencies import get_current_user, require_role
from auth.password import hash_password

router = APIRouter(prefix="/api/admin", tags=["Admin Panel"])

# Pydantic schemas
class UserCreate(BaseModel):
    ad_soyad: str
    email: EmailStr
    password: str
    rol: UserRole
    sinif_duzeyi: Optional[int] = None
    parent_id: Optional[int] = None

class UserUpdate(BaseModel):
    ad_soyad: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    rol: Optional[UserRole] = None
    sinif_duzeyi: Optional[int] = None
    parent_id: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    ad_soyad: str
    email: str
    rol: UserRole
    sinif_duzeyi: Optional[int]
    parent_id: Optional[int]
    is_approved: bool
    
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    success: bool
    message: str

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    rol: Optional[UserRole] = None,
    pending: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    List all users, optionally filtered by role and pending status
    """
    query = db.query(User)
    
    if rol:
        query = query.filter(User.rol == rol)
    
    if pending:
        query = query.filter(User.is_approved == False)
    
    users = query.order_by(User.rol, User.ad_soyad).all()
    return users

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Create a new user (Admin only)
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate grade level for students
    if user_data.rol == UserRole.STUDENT:
        if not user_data.sinif_duzeyi or not (1 <= user_data.sinif_duzeyi <= 12):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Students must have a valid grade level (1-12)"
            )
    
    # Hash password
    password_hash = hash_password(user_data.password)
    
    # Create user
    new_user = User(
        ad_soyad=user_data.ad_soyad,
        email=user_data.email,
        password_hash=password_hash,
        rol=user_data.rol,
        sinif_duzeyi=user_data.sinif_duzeyi,
        is_approved=True # Admin created users are approved by default
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # If creating a parent, link the student to this parent
    if user_data.rol == UserRole.PARENT and user_data.parent_id:
        student = db.query(User).filter(User.id == user_data.parent_id).first()
        if student and student.rol == UserRole.STUDENT:
            student.parent_id = new_user.id
            db.commit()
            
    return new_user

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Update a user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_data.ad_soyad is not None:
        user.ad_soyad = user_data.ad_soyad
    
    if user_data.email is not None:
        # Check if new email is already taken
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = user_data.email
    
    if user_data.password is not None:
        user.password_hash = hash_password(user_data.password)
    
    if user_data.rol is not None:
        user.rol = user_data.rol
    
    if user_data.sinif_duzeyi is not None:
        if not (1 <= user_data.sinif_duzeyi <= 12):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Grade level must be 1-12 or null"
            )
        user.sinif_duzeyi = user_data.sinif_duzeyi
    
    if user_data.parent_id is not None:
        user.parent_id = user_data.parent_id
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Delete a user (Admin only)
    """
    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return None

@router.post("/users/{user_id}/approve", response_model=MessageResponse)
async def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Approve a pending user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_approved = True
    db.commit()
    
    return {"success": True, "message": "User approved successfully"}

@router.get("/statistics")
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Get system statistics
    """
    from models.reading_activity import PreReading, Practice, Answer
    from models.evaluation import TeacherEvaluation
    
    # Count users by role
    total_students = db.query(User).filter(User.rol == UserRole.STUDENT).count()
    total_teachers = db.query(User).filter(User.rol == UserRole.TEACHER).count()
    total_parents = db.query(User).filter(User.rol == UserRole.PARENT).count()
    total_admins = db.query(User).filter(User.rol == UserRole.ADMIN).count()
    
    # Count stories by grade
    stories_grade_2 = db.query(Story).filter(Story.sinif_duzeyi == 2).count()
    stories_grade_3 = db.query(Story).filter(Story.sinif_duzeyi == 3).count()
    stories_grade_4 = db.query(Story).filter(Story.sinif_duzeyi == 4).count()
    
    # Count activities
    total_pre_readings = db.query(PreReading).count()
    total_practices = db.query(Practice).count()
    total_answers = db.query(Answer).count()
    total_evaluations = db.query(TeacherEvaluation).count()
    
    # Calculate average quiz score
    from sqlalchemy import func as sql_func
    avg_quiz = db.query(sql_func.avg(Answer.dogru_sayisi)).scalar()
    avg_quiz_score = float(avg_quiz) if avg_quiz else 0.0
    
    return {
        "users": {
            "students": total_students,
            "teachers": total_teachers,
            "parents": total_parents,
            "admins": total_admins,
            "total": total_students + total_teachers + total_parents + total_admins
        },
        "stories": {
            "grade_2": stories_grade_2,
            "grade_3": stories_grade_3,
            "grade_4": stories_grade_4,
            "total": stories_grade_2 + stories_grade_3 + stories_grade_4
        },
        "activity": {
            "total_readings": total_pre_readings,
            "practices": total_practices,
            "quiz_submissions": total_answers,
            "avg_quiz_score": avg_quiz_score,
            "teacher_evaluations": total_evaluations
        }
    }

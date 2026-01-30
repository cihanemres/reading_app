"""
Notification Router
API endpoints for managing user notifications
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models.notification import Notification
from models.user import User
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

# Pydantic schemas
class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    link: Optional[str]
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int

class UnreadCountResponse(BaseModel):
    count: int

class SuccessResponse(BaseModel):
    success: bool
    message: str

@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's notifications
    
    - **limit**: Number of notifications to return (default: 20)
    - **offset**: Pagination offset (default: 0)
    - **unread_only**: Only return unread notifications (default: false)
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    # Get total count
    total = query.count()
    
    # Get unread count
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    # Get paginated notifications
    notifications = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()
    
    return {
        "notifications": notifications,
        "total": total,
        "unread_count": unread_count
    }

@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {"count": count}

@router.post("/{notification_id}/mark-read", response_model=SuccessResponse)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a specific notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return {"success": True, "message": "Notification marked as read"}

@router.post("/mark-all-read", response_model=SuccessResponse)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all user's notifications as read"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return {"success": True, "message": "All notifications marked as read"}

@router.delete("/{notification_id}", response_model=SuccessResponse)
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"success": True, "message": "Notification deleted"}


# ==================== ANNOUNCEMENT ENDPOINT ====================

from models.user import UserRole

class AnnouncementCreate(BaseModel):
    title: str
    message: str
    target: str  # 'all', 'students', 'teachers', 'parents', 'grade_2', 'grade_3', 'grade_4'

class AnnouncementResponse(BaseModel):
    success: bool
    message: str
    sent_count: int

@router.post("/announcement", response_model=AnnouncementResponse)
async def send_announcement(
    announcement: AnnouncementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send announcement to multiple users
    Only admin and teachers can send announcements
    """
    # Check permission
    if current_user.rol not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(
            status_code=403,
            detail="Only admins and teachers can send announcements"
        )
    
    # Determine target users
    target = announcement.target.lower()
    query = db.query(User)
    
    if target == 'all':
        # All users except the sender
        query = query.filter(User.id != current_user.id)
    elif target == 'students':
        query = query.filter(User.rol == UserRole.STUDENT)
    elif target == 'teachers':
        query = query.filter(User.rol == UserRole.TEACHER)
    elif target == 'parents':
        query = query.filter(User.rol == UserRole.PARENT)
    elif target.startswith('grade_'):
        grade = int(target.split('_')[1])
        query = query.filter(
            User.rol == UserRole.STUDENT,
            User.sinif_duzeyi == grade
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid target. Use: all, students, teachers, parents, grade_2, grade_3, grade_4"
        )
    
    target_users = query.all()
    
    if not target_users:
        return {
            "success": True,
            "message": "No users found for the selected target",
            "sent_count": 0
        }
    
    # Create notifications for all target users
    notifications = []
    for user in target_users:
        notification = Notification(
            user_id=user.id,
            type="announcement",
            title=f"📢 {announcement.title}",
            message=f"{announcement.message}\n\n— {current_user.ad_soyad}",
            link=None
        )
        notifications.append(notification)
    
    db.add_all(notifications)
    db.commit()
    
    return {
        "success": True,
        "message": f"Announcement sent to {len(notifications)} users",
        "sent_count": len(notifications)
    }


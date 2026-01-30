"""
Messaging Router
API endpoints for teacher-student and teacher-teacher messaging
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from database import get_db
from models.user import User, UserRole
from models.message import Message
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/messages", tags=["Messaging"])


# Pydantic Schemas
class MessageCreate(BaseModel):
    receiver_id: int
    subject: Optional[str] = None
    content: str


class MessageResponse(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    receiver_id: int
    receiver_name: str
    subject: Optional[str]
    content: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class InboxResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
    unread: int


# Send Message
@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_message(
    request: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to another user
    Teachers can message students and other teachers
    Students can message their teachers
    """
    # Verify receiver exists
    receiver = db.query(User).filter(User.id == request.receiver_id).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alıcı bulunamadı"
        )
    
    # Permission check
    if current_user.rol == UserRole.STUDENT:
        # Students can only message their teacher
        if receiver.id != current_user.teacher_id and receiver.rol != UserRole.TEACHER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sadece öğretmeninize mesaj gönderebilirsiniz"
            )
    
    # Create message
    message = Message(
        sender_id=current_user.id,
        receiver_id=request.receiver_id,
        subject=request.subject,
        content=request.content
    )
    db.add(message)
    db.commit()
    
    # Send notification
    from utils.notification_helper import create_notification
    create_notification(
        db=db,
        user_id=request.receiver_id,
        type="message",
        title="Yeni Mesaj",
        message=f"{current_user.ad_soyad} size bir mesaj gönderdi",
        link="/messages"
    )
    
    return {"success": True, "message": "Mesaj gönderildi", "id": message.id}


# Get Inbox
@router.get("/inbox", response_model=InboxResponse)
async def get_inbox(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get received messages (inbox)
    """
    query = db.query(Message).filter(Message.receiver_id == current_user.id)
    
    total = query.count()
    unread = query.filter(Message.is_read == False).count()
    
    messages = query.order_by(desc(Message.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender.ad_soyad if msg.sender else "Unknown",
            "receiver_id": msg.receiver_id,
            "receiver_name": msg.receiver.ad_soyad if msg.receiver else "Unknown",
            "subject": msg.subject,
            "content": msg.content,
            "is_read": msg.is_read,
            "created_at": msg.created_at,
            "read_at": msg.read_at
        })
    
    return {"messages": result, "total": total, "unread": unread}


# Get Sent Messages
@router.get("/sent")
async def get_sent_messages(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get sent messages
    """
    query = db.query(Message).filter(Message.sender_id == current_user.id)
    
    total = query.count()
    messages = query.order_by(desc(Message.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender.ad_soyad if msg.sender else "Unknown",
            "receiver_id": msg.receiver_id,
            "receiver_name": msg.receiver.ad_soyad if msg.receiver else "Unknown",
            "subject": msg.subject,
            "content": msg.content,
            "is_read": msg.is_read,
            "created_at": msg.created_at,
            "read_at": msg.read_at
        })
    
    return {"messages": result, "total": total}


# Read single message
@router.get("/{message_id}")
async def get_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single message and mark as read
    """
    message = db.query(Message).filter(
        Message.id == message_id,
        or_(
            Message.sender_id == current_user.id,
            Message.receiver_id == current_user.id
        )
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesaj bulunamadı"
        )
    
    # Mark as read if receiver is viewing
    if message.receiver_id == current_user.id and not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.commit()
    
    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "sender_name": message.sender.ad_soyad if message.sender else "Unknown",
        "receiver_id": message.receiver_id,
        "receiver_name": message.receiver.ad_soyad if message.receiver else "Unknown",
        "subject": message.subject,
        "content": message.content,
        "is_read": message.is_read,
        "created_at": message.created_at,
        "read_at": message.read_at
    }


# Mark message as read
@router.post("/{message_id}/read")
async def mark_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a message as read
    """
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.receiver_id == current_user.id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesaj bulunamadı"
        )
    
    message.is_read = True
    message.read_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


# Delete message
@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a message (only sender or receiver can delete)
    """
    message = db.query(Message).filter(
        Message.id == message_id,
        or_(
            Message.sender_id == current_user.id,
            Message.receiver_id == current_user.id
        )
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesaj bulunamadı"
        )
    
    db.delete(message)
    db.commit()
    
    return {"success": True, "message": "Mesaj silindi"}


# Get unread count
@router.get("/unread/count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get unread message count for badge display
    """
    count = db.query(Message).filter(
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).count()
    
    return {"count": count}


# Get conversation with a user
@router.get("/conversation/{user_id}")
async def get_conversation(
    user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get conversation history with a specific user
    """
    messages = db.query(Message).filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
            and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at).limit(limit).all()
    
    # Mark received messages as read
    for msg in messages:
        if msg.receiver_id == current_user.id and not msg.is_read:
            msg.is_read = True
            msg.read_at = datetime.utcnow()
    db.commit()
    
    # Get other user info
    other_user = db.query(User).filter(User.id == user_id).first()
    
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "is_mine": msg.sender_id == current_user.id,
            "content": msg.content,
            "created_at": msg.created_at
        })
    
    return {
        "user": {
            "id": other_user.id if other_user else user_id,
            "name": other_user.ad_soyad if other_user else "Unknown",
            "role": other_user.rol.value if other_user else "unknown"
        },
        "messages": result
    }

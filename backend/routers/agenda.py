"""
Agenda Router
API endpoints for student agenda/calendar
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from database import get_db
from models.user import User, UserRole
from models.agenda import AgendaItem
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agenda", tags=["Agenda"])


# Pydantic Schemas
class AgendaItemCreate(BaseModel):
    item_type: str = "task"  # task, reminder, birthday, special_day, reading_goal
    title: str
    description: Optional[str] = None
    date: date
    time: Optional[str] = None
    is_recurring: bool = False
    recurrence_type: Optional[str] = None
    story_id: Optional[int] = None
    teacher_id: Optional[int] = None
    notify_before: Optional[int] = None


class AgendaItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[date] = None
    time: Optional[str] = None
    is_completed: Optional[bool] = None


class AgendaItemResponse(BaseModel):
    id: int
    item_type: str
    title: str
    description: Optional[str]
    date: date
    time: Optional[str]
    is_recurring: bool
    is_completed: bool
    story_id: Optional[int]
    teacher_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Create agenda item
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_agenda_item(
    item: AgendaItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new agenda item (task, reminder, birthday, etc.)
    """
    new_item = AgendaItem(
        user_id=current_user.id,
        item_type=item.item_type,
        title=item.title,
        description=item.description,
        date=item.date,
        time=item.time,
        is_recurring=item.is_recurring,
        recurrence_type=item.recurrence_type,
        story_id=item.story_id,
        teacher_id=item.teacher_id,
        notify_before=item.notify_before
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return {"success": True, "message": "Ajanda öğesi oluşturuldu", "id": new_item.id}


# Get agenda items for a date range
@router.get("/")
async def get_agenda_items(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    item_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get agenda items for current user, optionally filtered by date range and type
    """
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    query = db.query(AgendaItem).filter(
        AgendaItem.user_id == current_user.id,
        AgendaItem.date >= start_date,
        AgendaItem.date <= end_date
    )
    
    if item_type:
        query = query.filter(AgendaItem.item_type == item_type)
    
    items = query.order_by(AgendaItem.date, AgendaItem.time).all()
    
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "item_type": item.item_type,
            "title": item.title,
            "description": item.description,
            "date": item.date.isoformat(),
            "time": item.time,
            "is_recurring": item.is_recurring,
            "is_completed": item.is_completed,
            "story_id": item.story_id,
            "teacher_id": item.teacher_id
        })
    
    return {"items": result, "count": len(result)}


# Get today's agenda
@router.get("/today")
async def get_today_agenda(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get agenda items for today
    """
    today = date.today()
    
    items = db.query(AgendaItem).filter(
        AgendaItem.user_id == current_user.id,
        AgendaItem.date == today
    ).order_by(AgendaItem.time).all()
    
    # Also get recurring items that apply today
    recurring = db.query(AgendaItem).filter(
        AgendaItem.user_id == current_user.id,
        AgendaItem.is_recurring == True
    ).all()
    
    # Filter recurring items based on recurrence_type
    for item in recurring:
        if item.date != today:
            if item.recurrence_type == 'daily':
                items.append(item)
            elif item.recurrence_type == 'weekly' and item.date.weekday() == today.weekday():
                items.append(item)
            elif item.recurrence_type == 'monthly' and item.date.day == today.day:
                items.append(item)
            elif item.recurrence_type == 'yearly' and item.date.month == today.month and item.date.day == today.day:
                items.append(item)
    
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "item_type": item.item_type,
            "title": item.title,
            "description": item.description,
            "time": item.time,
            "is_completed": item.is_completed
        })
    
    return {"date": today.isoformat(), "items": result}


# Get upcoming items (next 7 days)
@router.get("/upcoming")
async def get_upcoming_items(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get upcoming agenda items for next N days
    """
    today = date.today()
    end_date = today + timedelta(days=days)
    
    items = db.query(AgendaItem).filter(
        AgendaItem.user_id == current_user.id,
        AgendaItem.date >= today,
        AgendaItem.date <= end_date,
        AgendaItem.is_completed == False
    ).order_by(AgendaItem.date, AgendaItem.time).all()
    
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "item_type": item.item_type,
            "title": item.title,
            "date": item.date.isoformat(),
            "time": item.time,
            "is_completed": item.is_completed
        })
    
    return {"items": result, "count": len(result)}


# Update agenda item
@router.put("/{item_id}")
async def update_agenda_item(
    item_id: int,
    update: AgendaItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an agenda item
    """
    item = db.query(AgendaItem).filter(
        AgendaItem.id == item_id,
        AgendaItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ajanda öğesi bulunamadı"
        )
    
    if update.title is not None:
        item.title = update.title
    if update.description is not None:
        item.description = update.description
    if update.date is not None:
        item.date = update.date
    if update.time is not None:
        item.time = update.time
    if update.is_completed is not None:
        item.is_completed = update.is_completed
        if update.is_completed:
            item.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {"success": True, "message": "Ajanda öğesi güncellendi"}


# Mark as complete
@router.post("/{item_id}/complete")
async def complete_agenda_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark an agenda item as completed
    """
    item = db.query(AgendaItem).filter(
        AgendaItem.id == item_id,
        AgendaItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ajanda öğesi bulunamadı"
        )
    
    item.is_completed = True
    item.completed_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Görev tamamlandı"}


# Delete agenda item
@router.delete("/{item_id}")
async def delete_agenda_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an agenda item
    """
    item = db.query(AgendaItem).filter(
        AgendaItem.id == item_id,
        AgendaItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ajanda öğesi bulunamadı"
        )
    
    db.delete(item)
    db.commit()
    
    return {"success": True, "message": "Ajanda öğesi silindi"}


# Get birthdays this month
@router.get("/birthdays")
async def get_birthdays(
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get birthday reminders for the month
    """
    if not month:
        month = date.today().month
    
    birthdays = db.query(AgendaItem).filter(
        AgendaItem.user_id == current_user.id,
        AgendaItem.item_type == 'birthday'
    ).all()
    
    # Filter by month
    result = []
    for item in birthdays:
        if item.date.month == month:
            result.append({
                "id": item.id,
                "title": item.title,
                "day": item.date.day,
                "description": item.description
            })
    
    return {"month": month, "birthdays": result}

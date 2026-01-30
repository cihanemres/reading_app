"""
Chart Data Endpoints
Provides data formatted for Chart.js visualizations
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional

from database import get_db
from models.user import User
from models.reading_activity import PreReading, Practice
from models.story import Story
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/charts", tags=["Charts"])


@router.get("/reading-speed/me")
async def get_my_reading_speed_chart(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get reading speed data for charts (current user)
    Returns data points for the last N days
    """
    return await _get_reading_speed_data(current_user.id, days, db)


@router.get("/reading-speed/{student_id}")
async def get_student_reading_speed_chart(
    student_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get reading speed data for charts (specific student - for teachers)
    """
    # Verify access (teacher or admin)
    if current_user.rol not in ['ogretmen', 'yonetici']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await _get_reading_speed_data(student_id, days, db)


async def _get_reading_speed_data(student_id: int, days: int, db: Session):
    """Helper function to get reading speed time series data"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get pre-readings
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == student_id,
        PreReading.created_at >= start_date
    ).order_by(PreReading.created_at).all()
    
    # Get practices
    practices = db.query(Practice).filter(
        Practice.ogrenci_id == student_id,
        Practice.created_at >= start_date
    ).order_by(Practice.created_at).all()
    
    # Combine and sort by date
    data_points = []
    
    for pr in pre_readings:
        if pr.okuma_hizi:
            story = db.query(Story).filter(Story.id == pr.story_id).first()
            data_points.append({
                "date": pr.created_at.isoformat() if pr.created_at else None,
                "speed": pr.okuma_hizi,
                "type": "ilk_okuma",
                "story": story.baslik if story else "Bilinmeyen"
            })
    
    for p in practices:
        if p.okuma_hizi:
            story = db.query(Story).filter(Story.id == p.story_id).first()
            data_points.append({
                "date": p.created_at.isoformat() if p.created_at else None,
                "speed": p.okuma_hizi,
                "type": "pratik",
                "story": story.baslik if story else "Bilinmeyen"
            })
    
    # Sort by date
    data_points.sort(key=lambda x: x["date"] if x["date"] else "")
    
    # Calculate statistics
    speeds = [d["speed"] for d in data_points if d["speed"]]
    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    max_speed = max(speeds) if speeds else 0
    min_speed = min(speeds) if speeds else 0
    
    # Calculate trend (last 7 vs previous 7)
    if len(data_points) >= 2:
        mid = len(data_points) // 2
        first_half_avg = sum(d["speed"] for d in data_points[:mid] if d["speed"]) / mid if mid > 0 else 0
        second_half_avg = sum(d["speed"] for d in data_points[mid:] if d["speed"]) / (len(data_points) - mid) if (len(data_points) - mid) > 0 else 0
        trend = "up" if second_half_avg > first_half_avg else ("down" if second_half_avg < first_half_avg else "stable")
    else:
        trend = "stable"
    
    return {
        "data": data_points,
        "summary": {
            "total_readings": len(data_points),
            "average_speed": round(avg_speed, 1),
            "max_speed": round(max_speed, 1),
            "min_speed": round(min_speed, 1),
            "trend": trend
        },
        "chart_config": {
            "labels": [d["date"][:10] if d["date"] else "" for d in data_points],
            "datasets": [{
                "label": "Okuma Hızı (kelime/dk)",
                "data": [d["speed"] for d in data_points],
                "borderColor": "#8B5CF6",
                "backgroundColor": "rgba(139, 92, 246, 0.1)",
                "fill": True,
                "tension": 0.4
            }]
        }
    }


@router.get("/story-progress/me")
async def get_my_story_progress_chart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get story completion progress for charts
    """
    return await _get_story_progress_data(current_user.id, db)


@router.get("/story-progress/{student_id}")
async def get_student_story_progress_chart(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get story progress for specific student (for teachers)
    """
    if current_user.rol not in ['ogretmen', 'yonetici']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await _get_story_progress_data(student_id, db)


async def _get_story_progress_data(student_id: int, db: Session):
    """Get per-story improvement data"""
    from utils.progress_calculator import calculate_improvement
    
    # Get all unique stories for student
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == student_id
    ).all()
    
    story_data = []
    for pr in pre_readings:
        story = db.query(Story).filter(Story.id == pr.story_id).first()
        if story:
            improvement = calculate_improvement(student_id, story.id, db)
            if improvement.get("has_data"):
                story_data.append({
                    "story_id": story.id,
                    "story_title": story.baslik,
                    "subject": story.ders,
                    "first_speed": improvement["first_reading"]["speed_wpm"],
                    "last_speed": improvement["last_reading"]["speed_wpm"],
                    "improvement_percent": improvement["improvement"]["speed_increase_percent"],
                    "practice_count": improvement["practice_count"]
                })
    
    # Sort by improvement
    story_data.sort(key=lambda x: x["improvement_percent"], reverse=True)
    
    return {
        "stories": story_data,
        "chart_config": {
            "labels": [s["story_title"][:20] + "..." if len(s["story_title"]) > 20 else s["story_title"] for s in story_data],
            "datasets": [
                {
                    "label": "İlk Okuma (k/dk)",
                    "data": [s["first_speed"] for s in story_data],
                    "backgroundColor": "#EF4444"
                },
                {
                    "label": "Son Okuma (k/dk)",
                    "data": [s["last_speed"] for s in story_data],
                    "backgroundColor": "#10B981"
                }
            ]
        }
    }


@router.get("/weekly-activity/me")
async def get_my_weekly_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get weekly reading activity for heatmap/bar chart
    """
    return await _get_weekly_activity_data(current_user.id, db)


async def _get_weekly_activity_data(student_id: int, db: Session):
    """Get activity per day of week"""
    # Get all readings in last 4 weeks
    start_date = datetime.utcnow() - timedelta(days=28)
    
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == student_id,
        PreReading.created_at >= start_date
    ).all()
    
    practices = db.query(Practice).filter(
        Practice.ogrenci_id == student_id,
        Practice.created_at >= start_date
    ).all()
    
    # Count by day of week (0=Monday, 6=Sunday)
    day_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    day_counts = [0] * 7
    
    for pr in pre_readings:
        if pr.created_at:
            day_counts[pr.created_at.weekday()] += 1
    
    for p in practices:
        if p.created_at:
            day_counts[p.created_at.weekday()] += 1
    
    return {
        "data": [{"day": day_names[i], "count": day_counts[i]} for i in range(7)],
        "chart_config": {
            "labels": day_names,
            "datasets": [{
                "label": "Okuma Sayısı",
                "data": day_counts,
                "backgroundColor": [
                    "#8B5CF6", "#A78BFA", "#C4B5FD", "#DDD6FE",
                    "#EDE9FE", "#F5F3FF", "#7C3AED"
                ]
            }]
        }
    }

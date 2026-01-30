"""
Gamification Router
Handles achievement badges and leaderboard
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from models.user import User, UserRole
from models.achievement import Achievement
from models.reading_activity import PreReading, Practice
from auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/gamification", tags=["gamification"])

# Badge definitions
BADGE_CRITERIA = {
    "first_step": {
        "name": "İlk Adım",
        "description": "İlk hikayeni okudun!",
        "icon": "🌟",
        "color": "gold",
        "check": lambda user_id, db: get_story_count(user_id, db) >= 1
    },
    "speed_reader": {
        "name": "Hızlı Okuyucu",
        "description": "5 hikaye okudun",
        "icon": "⚡",
        "color": "blue",
        "check": lambda user_id, db: get_story_count(user_id, db) >= 5
    },
    "bookworm": {
        "name": "Kitap Kurdu",
        "description": "10 hikaye okudun",
        "icon": "📚",
        "color": "purple",
        "check": lambda user_id, db: get_story_count(user_id, db) >= 10
    },
    "super_reader": {
        "name": "Süper Okuyucu",
        "description": "25 hikaye okudun",
        "icon": "🦸",
        "color": "red",
        "check": lambda user_id, db: get_story_count(user_id, db) >= 25
    },
    "master": {
        "name": "Ustalaşma",
        "description": "50 hikaye okudun",
        "icon": "👑",
        "color": "gold",
        "check": lambda user_id, db: get_story_count(user_id, db) >= 50
    },
    "practice_master": {
        "name": "Pratik Ustası",
        "description": "10 pratik tamamladın",
        "icon": "🎯",
        "color": "green",
        "check": lambda user_id, db: get_practice_count(user_id, db) >= 10
    },
    "speed_champion": {
        "name": "Hız Şampiyonu",
        "description": "150+ kelime/dakika hıza ulaştın",
        "icon": "🏃",
        "color": "orange",
        "check": lambda user_id, db: get_avg_speed(user_id, db) >= 150
    },
    "perfect_comprehension": {
        "name": "Mükemmel Anlama",
        "description": "Anlama puanında 9+ aldın",
        "icon": "🧠",
        "color": "pink",
        "check": lambda user_id, db: get_avg_comprehension(user_id, db) >= 9
    }
}

def get_story_count(user_id: int, db: Session) -> int:
    """Get unique story count for user"""
    count = db.query(func.count(func.distinct(PreReading.story_id))).filter(
        PreReading.ogrenci_id == user_id
    ).scalar()
    return count or 0

def get_practice_count(user_id: int, db: Session) -> int:
    """Get total practice sessions for user"""
    count = db.query(func.count(Practice.id)).filter(
        Practice.ogrenci_id == user_id
    ).scalar()
    return count or 0

def get_avg_speed(user_id: int, db: Session) -> float:
    """Get average reading speed for user"""
    avg = db.query(func.avg(PreReading.okuma_hizi)).filter(
        PreReading.ogrenci_id == user_id,
        PreReading.okuma_hizi.isnot(None)
    ).scalar()
    return float(avg) if avg else 0.0

def get_avg_comprehension(user_id: int, db: Session) -> float:
    """Get average comprehension score for user"""
    # TODO: Implement when evaluation system is ready
    return 0.0

def has_badge(user_id: int, badge_type: str, db: Session) -> bool:
    """Check if user already has badge"""
    exists = db.query(Achievement).filter(
        Achievement.user_id == user_id,
        Achievement.badge_type == badge_type
    ).first()
    return exists is not None

def award_badge(user_id: int, badge_type: str, db: Session):
    """Award badge to user"""
    if not has_badge(user_id, badge_type, db):
        achievement = Achievement(
            user_id=user_id,
            badge_type=badge_type
        )
        db.add(achievement)
        db.commit()
        return True
    return False

@router.get("/badges/me")
async def get_my_badges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all badges earned by current user"""
    achievements = db.query(Achievement).filter(
        Achievement.user_id == current_user.id
    ).order_by(Achievement.earned_at.desc()).all()
    
    badges = []
    for achievement in achievements:
        badge_info = BADGE_CRITERIA.get(achievement.badge_type, {})
        badges.append({
            "type": achievement.badge_type,
            "name": badge_info.get("name", achievement.badge_type),
            "description": badge_info.get("description", ""),
            "icon": badge_info.get("icon", "🏅"),
            "color": badge_info.get("color", "gray"),
            "earned_at": achievement.earned_at.isoformat()
        })
    
    return {"badges": badges, "total": len(badges)}

@router.post("/check-achievements")
async def check_achievements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user earned new achievements"""
    new_badges = []
    
    for badge_type, criteria in BADGE_CRITERIA.items():
        # Skip if already has badge
        if has_badge(current_user.id, badge_type, db):
            continue
        
        # Check if criteria met
        if criteria["check"](current_user.id, db):
            if award_badge(current_user.id, badge_type, db):
                new_badges.append({
                    "type": badge_type,
                    "name": criteria["name"],
                    "description": criteria["description"],
                    "icon": criteria["icon"],
                    "color": criteria["color"]
                })
    
    return {"new_badges": new_badges}

@router.get("/leaderboard")
async def get_leaderboard(
    period: str = "weekly",
    grade_level: Optional[int] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get leaderboard rankings"""
    # Calculate date range
    now = datetime.utcnow()
    if period == "weekly":
        start_date = now - timedelta(days=7)
    elif period == "monthly":
        start_date = now - timedelta(days=30)
    else:  # all_time
        start_date = datetime(2000, 1, 1)
    
    # Base query
    query = db.query(
        User.id,
        User.ad_soyad,
        User.sinif_duzeyi,
        func.count(func.distinct(PreReading.story_id)).label('story_count'),
        func.avg(PreReading.okuma_hizi).label('avg_speed'),
        func.coalesce(func.avg(0), 0).label('avg_comprehension')  # Placeholder
    ).join(
        PreReading, User.id == PreReading.ogrenci_id
    ).filter(
        User.rol == 'ogrenci',
        PreReading.created_at >= start_date
    )
    
    # Filter by grade if specified
    if grade_level:
        query = query.filter(User.sinif_duzeyi == grade_level)
    
    # Group and order
    leaderboard = query.group_by(
        User.id, User.ad_soyad, User.sinif_duzeyi
    ).order_by(
        desc('story_count'),
        desc('avg_speed')
    ).limit(limit).all()
    
    # Format results
    results = []
    for rank, entry in enumerate(leaderboard, 1):
        results.append({
            "rank": rank,
            "user_id": entry.id,
            "name": entry.ad_soyad,
            "grade_level": entry.sinif_duzeyi,
            "story_count": entry.story_count,
            "avg_speed": round(entry.avg_speed, 1) if entry.avg_speed else 0,
            "avg_comprehension": round(entry.avg_comprehension, 1) if entry.avg_comprehension else 0
        })
    
    return {"leaderboard": results, "period": period}

@router.get("/progress/me")
async def get_my_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get progress towards next milestone"""
    story_count = get_story_count(current_user.id, db)
    
    # Define milestones
    milestones = [1, 5, 10, 25, 50, 100]
    
    # Find next milestone
    next_milestone = None
    for milestone in milestones:
        if story_count < milestone:
            next_milestone = milestone
            break
    
    if next_milestone is None:
        next_milestone = milestones[-1]
    
    progress_percentage = (story_count / next_milestone) * 100 if next_milestone > 0 else 100
    
    return {
        "current_stories": story_count,
        "next_milestone": next_milestone,
        "remaining": max(0, next_milestone - story_count),
        "progress_percentage": min(100, progress_percentage)
    }


# ===== STREAK & XP SYSTEM =====
from models.user_streak import UserStreak, XP_VALUES, get_level_for_xp, get_xp_for_next_level
from datetime import date

def get_or_create_streak(user_id: int, db: Session) -> UserStreak:
    """Get or create user streak record"""
    streak = db.query(UserStreak).filter(UserStreak.user_id == user_id).first()
    if not streak:
        streak = UserStreak(user_id=user_id)
        db.add(streak)
        db.commit()
        db.refresh(streak)
    return streak

def update_streak(user_id: int, db: Session) -> dict:
    """Update user's streak based on activity"""
    streak = get_or_create_streak(user_id, db)
    today = date.today()
    
    if streak.last_activity_date is None:
        # First activity
        streak.current_streak = 1
        streak.longest_streak = 1
        streak.last_activity_date = today
    elif streak.last_activity_date == today:
        # Already logged today
        pass
    elif streak.last_activity_date == today - timedelta(days=1):
        # Consecutive day
        streak.current_streak += 1
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        streak.last_activity_date = today
        
        # Streak bonus XP
        if streak.current_streak == 3:
            add_xp(user_id, "streak_bonus_3", db)
        elif streak.current_streak == 7:
            add_xp(user_id, "streak_bonus_7", db)
        elif streak.current_streak == 30:
            add_xp(user_id, "streak_bonus_30", db)
    else:
        # Streak broken
        streak.current_streak = 1
        streak.last_activity_date = today
    
    db.commit()
    return {
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak
    }

def add_xp(user_id: int, action: str, db: Session) -> int:
    """Add XP for an action"""
    streak = get_or_create_streak(user_id, db)
    xp_amount = XP_VALUES.get(action, 0)
    
    streak.total_xp += xp_amount
    streak.level = get_level_for_xp(streak.total_xp)
    
    db.commit()
    return xp_amount


@router.get("/streak/me")
async def get_my_streak(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's streak info"""
    streak = get_or_create_streak(current_user.id, db)
    
    return {
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
        "last_activity": streak.last_activity_date.isoformat() if streak.last_activity_date else None,
        "streak_status": "active" if streak.last_activity_date == date.today() else "inactive"
    }


@router.get("/xp/me")
async def get_my_xp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's XP and level info"""
    streak = get_or_create_streak(current_user.id, db)
    level_progress = get_xp_for_next_level(streak.total_xp, streak.level)
    
    return {
        "total_xp": streak.total_xp,
        "level": streak.level,
        "level_name": get_level_name(streak.level),
        "progress_to_next": level_progress,
        "xp_values": XP_VALUES
    }


@router.post("/xp/add")
async def add_user_xp(
    action: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add XP for an action"""
    if action not in XP_VALUES:
        raise HTTPException(status_code=400, detail="Invalid action type")
    
    # Update streak on any activity
    streak_info = update_streak(current_user.id, db)
    
    # Add XP
    xp_added = add_xp(current_user.id, action, db)
    
    streak = get_or_create_streak(current_user.id, db)
    
    return {
        "xp_added": xp_added,
        "total_xp": streak.total_xp,
        "level": streak.level,
        "streak": streak_info
    }


@router.get("/stats/me")
async def get_my_gamification_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all gamification stats for current user"""
    streak = get_or_create_streak(current_user.id, db)
    level_progress = get_xp_for_next_level(streak.total_xp, streak.level)
    
    # Get badges
    achievements = db.query(Achievement).filter(
        Achievement.user_id == current_user.id
    ).all()
    
    badges = []
    for achievement in achievements:
        badge_info = BADGE_CRITERIA.get(achievement.badge_type, {})
        badges.append({
            "type": achievement.badge_type,
            "name": badge_info.get("name", achievement.badge_type),
            "icon": badge_info.get("icon", "🏅")
        })
    
    return {
        "xp": {
            "total": streak.total_xp,
            "level": streak.level,
            "level_name": get_level_name(streak.level),
            "progress": level_progress
        },
        "streak": {
            "current": streak.current_streak,
            "longest": streak.longest_streak,
            "active_today": streak.last_activity_date == date.today()
        },
        "badges": {
            "earned": badges,
            "total": len(badges),
            "available": len(BADGE_CRITERIA)
        },
        "reading": {
            "stories": get_story_count(current_user.id, db),
            "practices": get_practice_count(current_user.id, db),
            "avg_speed": round(get_avg_speed(current_user.id, db), 1)
        }
    }


def get_level_name(level: int) -> str:
    """Get level name based on level number"""
    level_names = {
        1: "Çırak",
        2: "Okur",
        3: "Hikayeci",
        4: "Kitap Kurdu",
        5: "Usta Okur",
        6: "Bilge",
        7: "Efsane",
        8: "Şampiyon",
        9: "Kahraman",
        10: "Efsanevi Okur"
    }
    return level_names.get(level, f"Seviye {level}")


# ===== COMMENDATION/TAKDİR SYSTEM =====

from models.commendation import Commendation
from pydantic import BaseModel
from typing import Optional

class CommendationCreate(BaseModel):
    student_id: int
    commendation_type: str = "takdir"  # takdir, tesekkur, birincilik, ozel_basari
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    rank: Optional[int] = None
    xp_reward: int = 50


@router.post("/commendation")
async def give_commendation(
    data: CommendationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    """
    Teacher gives a commendation to a student
    """
    # Verify student exists and belongs to teacher
    student = db.query(User).filter(
        User.id == data.student_id,
        User.teacher_id == current_user.id
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğrenci bulunamadı veya size ait değil"
        )
    
    # Create commendation
    commendation = Commendation(
        student_id=data.student_id,
        teacher_id=current_user.id,
        commendation_type=data.commendation_type,
        title=data.title,
        description=data.description,
        category=data.category,
        rank=data.rank,
        xp_reward=data.xp_reward
    )
    db.add(commendation)
    
    # Add XP if reward specified
    if data.xp_reward > 0:
        add_xp(db, data.student_id, data.xp_reward, "commendation")
    
    db.commit()
    
    # Notify student
    from utils.notification_helper import create_notification
    type_names = {
        "takdir": "Takdir",
        "tesekkur": "Teşekkür",
        "birincilik": "Birincilik",
        "ozel_basari": "Özel Başarı"
    }
    create_notification(
        db=db,
        user_id=data.student_id,
        type="achievement",
        title=f"🏆 {type_names.get(data.commendation_type, 'Takdir')} Aldınız!",
        message=f"{current_user.ad_soyad}: {data.title}",
        link="/student/achievements"
    )
    
    return {"success": True, "message": "Takdir verildi", "id": commendation.id}


@router.get("/commendations/me")
async def get_my_commendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT))
):
    """
    Get student's commendations
    """
    commendations = db.query(Commendation).filter(
        Commendation.student_id == current_user.id
    ).order_by(Commendation.created_at.desc()).all()
    
    result = []
    for c in commendations:
        result.append({
            "id": c.id,
            "type": c.commendation_type,
            "title": c.title,
            "description": c.description,
            "category": c.category,
            "rank": c.rank,
            "xp_reward": c.xp_reward,
            "teacher_name": c.teacher.ad_soyad if c.teacher else "Unknown",
            "created_at": c.created_at.isoformat()
        })
    
    # Group by type
    grouped = {
        "takdir": [c for c in result if c["type"] == "takdir"],
        "tesekkur": [c for c in result if c["type"] == "tesekkur"],
        "birincilik": [c for c in result if c["type"] == "birincilik"],
        "ozel_basari": [c for c in result if c["type"] == "ozel_basari"]
    }
    
    return {
        "commendations": result,
        "grouped": grouped,
        "total": len(result)
    }


@router.get("/rankings/weekly")
async def get_weekly_rankings(
    category: str = "xp",  # xp, stories, speed
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get weekly rankings for different categories
    """
    from datetime import datetime, timedelta
    from sqlalchemy import desc
    
    week_start = datetime.utcnow() - timedelta(days=7)
    
    if category == "xp":
        # Rank by XP gained this week
        rankings = db.query(
            User.id,
            User.ad_soyad,
            User.sinif_duzeyi,
            UserStreak.total_xp
        ).join(
            UserStreak, User.id == UserStreak.user_id
        ).filter(
            User.rol == UserRole.STUDENT
        ).order_by(desc(UserStreak.total_xp)).limit(10).all()
        
        result = []
        for rank, r in enumerate(rankings, 1):
            result.append({
                "rank": rank,
                "user_id": r.id,
                "name": r.ad_soyad,
                "grade": r.sinif_duzeyi,
                "score": r.total_xp or 0,
                "is_me": r.id == current_user.id
            })
    
    elif category == "stories":
        # Rank by stories read this week
        from models.reading_activity import PreReading
        
        rankings = db.query(
            User.id,
            User.ad_soyad,
            User.sinif_duzeyi,
            func.count(PreReading.id).label('story_count')
        ).join(
            PreReading, User.id == PreReading.ogrenci_id
        ).filter(
            User.rol == UserRole.STUDENT,
            PreReading.tarih >= week_start
        ).group_by(User.id).order_by(desc('story_count')).limit(10).all()
        
        result = []
        for rank, r in enumerate(rankings, 1):
            result.append({
                "rank": rank,
                "user_id": r.id,
                "name": r.ad_soyad,
                "grade": r.sinif_duzeyi,
                "score": r.story_count,
                "is_me": r.id == current_user.id
            })
    
    else:
        result = []
    
    return {"category": category, "rankings": result}

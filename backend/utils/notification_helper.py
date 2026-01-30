"""
Notification Helper Functions
Utility functions for creating and managing notifications
"""
from sqlalchemy.orm import Session
from models.notification import Notification
from models.user import User

def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    message: str,
    link: str = None
) -> Notification:
    """
    Create a new notification
    
    Args:
        db: Database session
        user_id: ID of user to notify
        type: Notification type (evaluation, progress, achievement, general)
        title: Notification title
        message: Notification message
        link: Optional link to related content
        
    Returns:
        Created notification object
    """
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        link=link
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification

def notify_parent_of_evaluation(
    db: Session,
    student_id: int,
    teacher_name: str,
    story_title: str = None
):
    """
    Notify parent when teacher evaluates their child
    
    Args:
        db: Database session
        student_id: ID of the student
        teacher_name: Name of the teacher who evaluated
        story_title: Optional story title
    """
    # Get student
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        return
    
    # Get parent
    parent = db.query(User).filter(User.id == student.parent_id).first()
    if not parent:
        return
    
    # Create notification
    title = "Yeni Öğretmen Değerlendirmesi"
    message = f"{teacher_name}, {student.ad_soyad} için yeni bir değerlendirme yaptı"
    if story_title:
        message += f" ({story_title})"
    
    create_notification(
        db=db,
        user_id=parent.id,
        type="evaluation",
        title=title,
        message=message,
        link="/parent/dashboard"
    )

def notify_student_of_achievement(
    db: Session,
    student_id: int,
    badge_name: str,
    badge_description: str
):
    """
    Notify student when they earn a new achievement
    
    Args:
        db: Database session
        student_id: ID of the student
        badge_name: Name of the badge earned
        badge_description: Description of the achievement
    """
    create_notification(
        db=db,
        user_id=student_id,
        type="achievement",
        title=f"🎉 Yeni Rozet: {badge_name}",
        message=badge_description,
        link="/student/dashboard"
    )

def notify_progress_milestone(
    db: Session,
    student_id: int,
    milestone_type: str,
    milestone_value: int
):
    """
    Notify student and parent of progress milestone
    
    Args:
        db: Database session
        student_id: ID of the student
        milestone_type: Type of milestone (stories, practice, speed)
        milestone_value: Value achieved
    """
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        return
    
    # Create message based on milestone type
    if milestone_type == "stories":
        title = "📚 İlerleme Kaydedildi"
        message = f"{milestone_value}. hikayeni tamamladın! Harika gidiyorsun!"
    elif milestone_type == "practice":
        title = "🔄 Pratik Başarısı"
        message = f"{milestone_value}. pratik seansını tamamladın!"
    elif milestone_type == "speed":
        title = "⚡ Hız Artışı"
        message = f"Okuma hızın {milestone_value} kelime/dakikaya ulaştı!"
    else:
        return
    
    # Notify student
    create_notification(
        db=db,
        user_id=student_id,
        type="progress",
        title=title,
        message=message,
        link="/student/dashboard"
    )
    
    # Notify parent if exists
    if student.parent_id:
        parent = db.query(User).filter(User.id == student.parent_id).first()
        if parent:
            create_notification(
                db=db,
                user_id=parent.id,
                type="progress",
                title=f"📊 {student.ad_soyad} - {title}",
                message=message,
                link="/parent/dashboard"
            )


def notify_level_up(
    db: Session,
    student_id: int,
    new_level: int,
    level_name: str
):
    """
    Notify student when they level up
    
    Args:
        db: Database session
        student_id: ID of the student
        new_level: New level number
        level_name: Name of the new level
    """
    create_notification(
        db=db,
        user_id=student_id,
        type="level_up",
        title=f"🎊 Seviye Atladın: {level_name}!",
        message=f"Tebrikler! Artık Seviye {new_level} - {level_name} oldun! Okumaya devam et!",
        link="/student/dashboard"
    )


def notify_streak_bonus(
    db: Session,
    student_id: int,
    streak_days: int,
    xp_bonus: int
):
    """
    Notify student when they earn a streak bonus
    
    Args:
        db: Database session
        student_id: ID of the student
        streak_days: Number of consecutive days
        xp_bonus: XP bonus earned
    """
    create_notification(
        db=db,
        user_id=student_id,
        type="streak",
        title=f"🔥 {streak_days} Gün Seri!",
        message=f"Harika! {streak_days} gün üst üste okudun ve +{xp_bonus} XP bonus kazandın!",
        link="/student/dashboard"
    )


def notify_streak_lost(
    db: Session,
    student_id: int,
    lost_streak: int
):
    """
    Notify student when they lose their streak
    """
    if lost_streak >= 3:  # Only notify if they had a decent streak
        create_notification(
            db=db,
            user_id=student_id,
            type="streak",
            title="😢 Seri Kırıldı",
            message=f"{lost_streak} günlük seri sona erdi. Yeniden başla!",
            link="/student/dashboard"
        )


def notify_assignment(
    db: Session,
    student_id: int,
    teacher_name: str,
    story_title: str,
    due_date: str = None
):
    """
    Notify student of new assignment
    """
    message = f"{teacher_name} sana yeni bir ödev verdi: {story_title}"
    if due_date:
        message += f". Son tarih: {due_date}"
    
    create_notification(
        db=db,
        user_id=student_id,
        type="assignment",
        title="📝 Yeni Ödev",
        message=message,
        link="/student/dashboard"
    )


def notify_assignment_due_reminder(
    db: Session,
    student_id: int,
    story_title: str,
    hours_remaining: int
):
    """
    Remind student of upcoming assignment deadline
    """
    if hours_remaining <= 24:
        title = "⚠️ Ödev Son Gün!"
        message = f"'{story_title}' ödevi bugün bitiyor. Hemen tamamla!"
    else:
        title = "📅 Ödev Hatırlatması"
        message = f"'{story_title}' ödevinin bitmesine {hours_remaining // 24} gün kaldı."
    
    create_notification(
        db=db,
        user_id=student_id,
        type="reminder",
        title=title,
        message=message,
        link="/student/dashboard"
    )


def notify_xp_earned(
    db: Session,
    student_id: int,
    action: str,
    xp_amount: int
):
    """
    Notify student of XP earned (optional, for significant amounts)
    """
    if xp_amount >= 15:  # Only notify for significant XP
        action_names = {
            "story_read": "Hikaye okuma",
            "quiz_passed": "Quiz başarısı",
            "perfect_score": "Mükemmel skor",
            "speed_improvement": "Hız artışı"
        }
        
        action_name = action_names.get(action, action)
        
        create_notification(
            db=db,
            user_id=student_id,
            type="xp",
            title=f"⭐ +{xp_amount} XP Kazandın!",
            message=f"{action_name} için {xp_amount} XP kazandın!",
            link="/student/dashboard"
        )


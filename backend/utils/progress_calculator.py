from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models.reading_activity import PreReading, Practice

def calculate_improvement(
    student_id: int,
    story_id: int,
    db: Session
) -> Dict:
    """
    Calculate reading improvement from first to last attempt
    
    Args:
        student_id: Student's user ID
        story_id: Story ID
        db: Database session
        
    Returns:
        Dictionary with improvement metrics
    """
    # Get pre-reading (first attempt)
    pre_reading = db.query(PreReading).filter(
        PreReading.ogrenci_id == student_id,
        PreReading.story_id == story_id
    ).first()
    
    # Get all practice attempts
    practices = db.query(Practice).filter(
        Practice.ogrenci_id == student_id,
        Practice.story_id == story_id
    ).order_by(Practice.tekrar_no).all()
    
    if not pre_reading:
        return {
            "has_data": False,
            "message": "No reading data found"
        }
    
    first_speed = pre_reading.okuma_hizi or 0
    first_time = pre_reading.okuma_suresi
    
    # Get last practice attempt
    last_speed = first_speed
    last_time = first_time
    total_attempts = 1
    
    if practices:
        last_practice = practices[-1]
        last_speed = last_practice.okuma_hizi or 0
        last_time = last_practice.okuma_suresi
        total_attempts = len(practices) + 1
    
    # Calculate improvements
    speed_improvement = last_speed - first_speed
    speed_improvement_percent = (speed_improvement / first_speed * 100) if first_speed > 0 else 0
    
    time_reduction = first_time - last_time
    time_reduction_percent = (time_reduction / first_time * 100) if first_time > 0 else 0
    
    return {
        "has_data": True,
        "first_reading": {
            "speed_wpm": first_speed,
            "time_seconds": first_time
        },
        "last_reading": {
            "speed_wpm": last_speed,
            "time_seconds": last_time
        },
        "improvement": {
            "speed_increase_wpm": round(speed_improvement, 2),
            "speed_increase_percent": round(speed_improvement_percent, 2),
            "time_reduction_seconds": round(time_reduction, 2),
            "time_reduction_percent": round(time_reduction_percent, 2)
        },
        "total_attempts": total_attempts,
        "practice_count": len(practices)
    }

def get_student_progress_summary(
    student_id: int,
    db: Session
) -> Dict:
    """
    Get overall progress summary for a student across all stories
    
    Args:
        student_id: Student's user ID
        db: Database session
        
    Returns:
        Dictionary with overall progress metrics
    """
    # Get all pre-readings
    pre_readings = db.query(PreReading).filter(
        PreReading.ogrenci_id == student_id
    ).all()
    
    # Get all practices
    practices = db.query(Practice).filter(
        Practice.ogrenci_id == student_id
    ).all()
    
    total_stories = len(pre_readings)
    total_practice_sessions = len(practices)
    
    if total_stories == 0:
        return {
            "total_stories": 0,
            "total_practice_sessions": 0,
            "average_speed_wpm": 0,
            "message": "No reading data found"
        }
    
    # Calculate average reading speed
    all_speeds = [pr.okuma_hizi for pr in pre_readings if pr.okuma_hizi]
    all_speeds.extend([p.okuma_hizi for p in practices if p.okuma_hizi])
    
    average_speed = sum(all_speeds) / len(all_speeds) if all_speeds else 0
    
    return {
        "total_stories": total_stories,
        "total_practice_sessions": total_practice_sessions,
        "average_speed_wpm": round(average_speed, 2),
        "total_reading_sessions": total_stories + total_practice_sessions
    }

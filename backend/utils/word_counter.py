import re

def count_words(text: str) -> int:
    """
    Count the number of words in a text
    
    Args:
        text: The text to count words in
        
    Returns:
        Number of words
    """
    if not text:
        return 0
    
    # Remove extra whitespace and split by whitespace
    words = text.strip().split()
    
    # Filter out empty strings
    words = [w for w in words if w]
    
    return len(words)

def calculate_reading_speed(word_count: int, time_seconds: float) -> float:
    """
    Calculate reading speed in words per minute
    
    Args:
        word_count: Number of words read
        time_seconds: Time taken in seconds
        
    Returns:
        Reading speed in words per minute (WPM)
    """
    if time_seconds <= 0:
        return 0.0
    
    # Convert seconds to minutes and calculate WPM
    time_minutes = time_seconds / 60
    wpm = word_count / time_minutes
    
    return round(wpm, 2)

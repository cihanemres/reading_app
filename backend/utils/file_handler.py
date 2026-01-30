import os
import shutil
from typing import Optional
from fastapi import UploadFile, HTTPException
import uuid

UPLOAD_DIR = "static/uploads"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def ensure_upload_directory():
    """Create upload directories if they don't exist"""
    os.makedirs(f"{UPLOAD_DIR}/images", exist_ok=True)
    os.makedirs(f"{UPLOAD_DIR}/audio", exist_ok=True)

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return os.path.splitext(filename)[1].lower()

def validate_file_size(file: UploadFile) -> bool:
    """Validate file size"""
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    return file_size <= MAX_FILE_SIZE

async def save_upload_file(file: UploadFile, file_type: str = "image") -> str:
    """
    Save an uploaded file to the appropriate directory
    
    Args:
        file: FastAPI UploadFile object
        file_type: Type of file ("image" or "audio")
        
    Returns:
        Relative path to saved file
        
    Raises:
        HTTPException: If file validation fails
    """
    ensure_upload_directory()
    
    # Validate file size
    if not validate_file_size(file):
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Get and validate extension
    extension = get_file_extension(file.filename)
    
    if file_type == "image":
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )
        subdirectory = "images"
    elif file_type == "audio":
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audio format. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
            )
        subdirectory = "audio"
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = f"{UPLOAD_DIR}/{subdirectory}/{unique_filename}"
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
    finally:
        file.file.close()
    
    # Return relative path
    return f"/{file_path}"

def delete_file(file_path: str) -> bool:
    """
    Delete a file from the filesystem
    
    Args:
        file_path: Path to file (relative or absolute)
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        # Remove leading slash if present
        if file_path.startswith("/"):
            file_path = file_path[1:]
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False

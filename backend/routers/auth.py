from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import re
from database import get_db
from models.user import User, UserRole
from auth.password import hash_password, verify_password
from auth.jwt_handler import create_access_token
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ==================== PASSWORD VALIDATION ====================

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength:
    - Minimum 6 characters
    - At least one uppercase letter
    - At least one number
    """
    if len(password) < 6:
        return False, "Şifre en az 6 karakter olmalıdır"
    if not re.search(r'[A-Z]', password):
        return False, "Şifre en az bir büyük harf içermelidir"
    if not re.search(r'[0-9]', password):
        return False, "Şifre en az bir rakam içermelidir"
    return True, ""

# ==================== PYDANTIC SCHEMAS ====================

class RegisterRequest(BaseModel):
    ad_soyad: str
    email: EmailStr
    password: str
    rol: UserRole
    sinif_duzeyi: Optional[int] = None
    parent_id: Optional[int] = None
    
    @validator('password')
    def password_strength(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: int
    ad_soyad: str
    email: str
    rol: UserRole
    sinif_duzeyi: Optional[int]
    
    class Config:
        from_attributes = True

class UpdateProfileRequest(BaseModel):
    ad_soyad: Optional[str] = None
    email: Optional[EmailStr] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def password_strength(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v

class PasswordResetRequest(BaseModel):
    email: EmailStr

class MessageResponse(BaseModel):
    success: bool
    message: str

# ==================== AUTHENTICATION ENDPOINTS ====================

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with password strength validation
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate grade level for students
    if request.rol == UserRole.STUDENT:
        if not request.sinif_duzeyi or not (1 <= request.sinif_duzeyi <= 12):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Students must have a valid grade level (1-12)"
            )
    
    # Hash password
    password_hash = hash_password(request.password)
    
    # Create new user
    new_user = User(
        ad_soyad=request.ad_soyad,
        email=request.email,
        password_hash=password_hash,
        rol=request.rol,
        sinif_duzeyi=request.sinif_duzeyi,
        parent_id=request.parent_id,
        is_approved=False # Explicitly set to False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "success": True, 
        "message": "Kayıt başarılı. Yönetici onayı bekleniyor."
    }

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login user and return JWT token
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check approval
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız henüz onaylanmadı. Lütfen yönetici onayını bekleyin."
        )
    
    # Create access token
    token_data = {
        "user_id": user.id,
        "email": user.email,
        "rol": user.rol.value
    }
    access_token = create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "ad_soyad": user.ad_soyad,
            "email": user.email,
            "rol": user.rol.value,
            "sinif_duzeyi": user.sinif_duzeyi
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    """
    return current_user

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's profile (name and email only)
    """
    # Update name if provided
    if request.ad_soyad:
        current_user.ad_soyad = request.ad_soyad
    
    # Update email if provided and not already taken
    if request.email and request.email != current_user.email:
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = request.email
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

# ==================== PASSWORD MANAGEMENT ====================

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change current user's password with verification
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mevcut şifre yanlış"
        )
    
    # Check if new password is same as current
    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yeni şifre mevcut şifreden farklı olmalıdır"
        )
    
    # Update password
    current_user.password_hash = hash_password(request.new_password)
    db.commit()
    
    return {"success": True, "message": "Şifre başarıyla değiştirildi"}

@router.post("/verify-token", response_model=MessageResponse)
async def verify_token(current_user: User = Depends(get_current_user)):
    """
    Verify if current token is still valid (for session management)
    """
    return {"success": True, "message": "Token is valid"}


"""
Seed script to create test users
Run: python create_test_users.py
"""
import sys
sys.path.insert(0, '.')

from database import SessionLocal, engine, Base
from models.user import User, UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_test_users():
    db = SessionLocal()
    
    test_users = [
        {
            "email": "admin@test.com",
            "ad_soyad": "Admin Kullanıcı",
            "rol": UserRole.ADMIN,
            "sinif_duzeyi": None,
            "parent_id": None
        },
        {
            "email": "teacher@test.com",
            "ad_soyad": "Öğretmen Kullanıcı",
            "rol": UserRole.TEACHER,
            "sinif_duzeyi": None,
            "parent_id": None
        },
        {
            "email": "student@test.com",
            "ad_soyad": "Öğrenci Kullanıcı",
            "rol": UserRole.STUDENT,
            "sinif_duzeyi": 3,
            "parent_id": None  # Will update after parent created
        },
        {
            "email": "parent@test.com",
            "ad_soyad": "Veli Kullanıcı",
            "rol": UserRole.PARENT,
            "sinif_duzeyi": None,
            "parent_id": None
        }
    ]
    
    password_hash = hash_password("123456")
    created_users = {}
    
    for user_data in test_users:
        # Check if user exists
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            print(f"⚠️  User {user_data['email']} already exists, skipping...")
            created_users[user_data["rol"]] = existing
            continue
        
        # Create user
        user = User(
            email=user_data["email"],
            ad_soyad=user_data["ad_soyad"],
            password_hash=password_hash,
            rol=user_data["rol"],
            sinif_duzeyi=user_data["sinif_duzeyi"],
            parent_id=user_data["parent_id"]
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        created_users[user_data["rol"]] = user
        print(f"✅ Created: {user_data['email']} ({user_data['rol'].value})")
    
    # Link student to parent
    if UserRole.STUDENT in created_users and UserRole.PARENT in created_users:
        student = created_users[UserRole.STUDENT]
        parent = created_users[UserRole.PARENT]
        if student.parent_id != parent.id:
            student.parent_id = parent.id
            db.commit()
            print(f"🔗 Linked student to parent")
    
    db.close()
    print("\n✨ Test users ready!")
    print("Login with any of these emails using password: 123456")

if __name__ == "__main__":
    create_test_users()

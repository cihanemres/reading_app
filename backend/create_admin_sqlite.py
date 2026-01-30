"""
Create admin user for SQLite database
"""
import sys
sys.path.insert(0, '.')

# Import database first to initialize Base
from database import SessionLocal, Base, engine

# Then import models (they register with Base)
from models.user import User, UserRole
import bcrypt

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Check if admin exists
existing = db.query(User).filter(User.email == 'admin@test.com').first()
if not existing:
    password = '123456'
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin = User(
        ad_soyad='Admin User',
        email='admin@test.com',
        password_hash=hashed,
        rol=UserRole.ADMIN,
        is_approved=True
    )
    db.add(admin)
    db.commit()
    print('Admin user created: admin@test.com / 123456')
else:
    # Update to ensure is_approved
    existing.is_approved = True
    db.commit()
    print('Admin already exists and is approved')

db.close()
print('Done!')

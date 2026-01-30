import sys
sys.path.insert(0, '.')
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Check if admin user exists
    result = db.execute(text("SELECT id, email, is_approved FROM users WHERE email = 'admin@test.com'"))
    admin = result.fetchone()
    
    if admin:
        print(f"Found admin user: {admin[1]}")
        # Ensure is_approved is true
        db.execute(text("UPDATE users SET is_approved = true WHERE email = 'admin@test.com'"))
        db.commit()
        print("Admin user approved and activated.")
    else:
        print("Admin user admin@test.com not found. Please check create_test_users.py and check_users.py.")
finally:
    db.close()

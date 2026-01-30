import sys
sys.path.insert(0, '.')
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    result = db.execute(text("SELECT id, ad_soyad, email, rol, is_approved FROM users"))
    users = result.fetchall()
    print(f"{'ID':<4} | {'Name':<20} | {'Email':<25} | {'Role':<10} | {'Approved':<5}")
    print("-" * 75)
    for u in users:
        print(f"{u[0]:<4} | {u[1]:<20} | {u[2]:<25} | {u[3]:<10} | {u[4]}")
finally:
    db.close()
